#include "dict.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <dirent.h>
#include <sys/types.h>
#include "analyzer_common.h"

// 自动遍历目录并批量加载所有txt词典
int load_all_cn_dicts(const char* dir_path) {
    DIR* dir = opendir(dir_path);
    if (!dir) {
        printf("[Error] Cannot open dict dir: %s\n", dir_path);
        return 0;
    }
    struct dirent* entry;
    int total = 0;
    char path[512];
    while ((entry = readdir(dir)) != NULL) {
        // 跳过 . 和 ..
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0)
            continue;
        const char* ext = strrchr(entry->d_name, '.');
        if (ext && strcmp(ext, ".txt") == 0) {
            snprintf(path, sizeof(path), "%s/%s", dir_path, entry->d_name);
            FILE* fp = fopen(path, "r");
            if (fp) {
                fclose(fp);
                total += Analyzer_LoadCNDict(NULL, path);
                printf("[Info] Loaded dict: %s\n", path);
            }
        }
    }
    closedir(dir);
    return total;
}

// 词典遍历器实现
dict_iter_t dict_iter(Dict* d) {
    dict_iter_t it;
    it.dict = d;
    it.bucket_idx = -1;
    it.node = NULL;
    it.key = NULL;
    it.value = 0;
    return it;
}

int dict_next(dict_iter_t* it) {
    if (!it || !it->dict) return 0;
    if (it->node && it->node->next) {
        it->node = it->node->next;
        it->key = it->node->word;
        it->value = it->node->count;
        return 1;
    }
    for (int i = it->bucket_idx + 1; i < HASH_TABLE_SIZE; i++) {
        if (it->dict->buckets[i]) {
            it->bucket_idx = i;
            it->node = it->dict->buckets[i];
            it->key = it->node->word;
            it->value = it->node->count;
            return 1;
        }
    }
    return 0;
}
// DJB2 Hash function
unsigned long hash(const char *str) {
    unsigned long hash = 5381;
    int c;
    while ((c = *str++)) hash = ((hash << 5) + hash) + c;
    return hash % HASH_TABLE_SIZE;
}

Dict* dict_create() {
    Dict* d = (Dict*)calloc(1, sizeof(Dict));
    return d;
}

void dict_free(Dict* d) {
    if (!d) return;
    for (int i = 0; i < HASH_TABLE_SIZE; i++) {
        Node* curr = d->buckets[i];
        while (curr) {
            Node* temp = curr;
            curr = curr->next;
            free(temp);
        }
    }
    free(d);
}

int dict_add(Dict* d, const char* word) {
    unsigned long h = hash(word);
    Node* curr = d->buckets[h];
    
    while (curr) {
        if (strncmp(curr->word, word, MAX_WORD_LEN) == 0) {
            d->total_count++;
            return ++(curr->count);
        }
        curr = curr->next;
    }
    
    // New node
    Node* new_node = (Node*)malloc(sizeof(Node));
    strncpy(new_node->word, word, MAX_WORD_LEN - 1);
    new_node->word[MAX_WORD_LEN - 1] = '\0';
    new_node->count = 1;
    new_node->next = d->buckets[h];
    d->buckets[h] = new_node;
    
    d->unique_count++;
    d->total_count++;
    return 1;
}

int dict_get(Dict* d, const char* word) {
    unsigned long h = hash(word);
    Node* curr = d->buckets[h];
    while (curr) {
        if (strncmp(curr->word, word, MAX_WORD_LEN) == 0) return curr->count;
        curr = curr->next;
    }
    return 0;
}

// 简单的冒泡排序取出前N（因为N很小，通常为10，效率足够）
void dict_get_top(Dict* d, WordFreq* out_arr, int n) {
    // 1. Collect all nodes (temporary inefficient but safe)
    int count = 0;
    // Assume worst case for stack alloc or use heap if unique_count is large
    // For safety with large text, we just scan and insert into fixed size sorted array
    
    for (int i = 0; i < n; i++) {
        out_arr[i].count = -1;
        out_arr[i].word[0] = '\0';
    }

    for (int i = 0; i < HASH_TABLE_SIZE; i++) {
        Node* curr = d->buckets[i];
        while (curr) {
            // Insert into top N
            int val = curr->count;
            char* key = curr->word;
            
            for (int k = 0; k < n; k++) {
                if (val > out_arr[k].count) {
                    // Shift
                    for (int j = n - 1; j > k; j--) {
                        out_arr[j] = out_arr[j-1];
                    }
                    out_arr[k].count = val;
                    strcpy(out_arr[k].word, key);
                    break;
                }
            }
            curr = curr->next;
        }
    }
}