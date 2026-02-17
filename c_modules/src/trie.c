#include "trie.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

struct TrieNode {
    unsigned char key;      // 当前节点的字节值
    int freq;               // > 0 表示以此节点结尾是一个词，存储词频
    struct TrieNode* child; // 第一个子节点
    struct TrieNode* sibling;// 下一个兄弟节点
};

TrieNode* trie_create(void) {
    TrieNode* node = (TrieNode*)calloc(1, sizeof(TrieNode));
    return node;
}

static void trie_free_node(TrieNode* node) {
    if (!node) return;
    trie_free_node(node->child);
    trie_free_node(node->sibling);
    free(node);
}

void trie_free(TrieNode* root) {
    trie_free_node(root);
}

void trie_insert(TrieNode* root, const char* word, int freq) {
    if (!root || !word) return;
    
    TrieNode* current = root;
    const unsigned char* p = (const unsigned char*)word;
    
    while (*p) {
        unsigned char key = *p;
        TrieNode* found = NULL;
        
        // 在子节点链表中查找当前字节
        TrieNode* child = current->child;
        while (child) {
            if (child->key == key) {
                found = child;
                break;
            }
            child = child->sibling;
        }
        
        if (!found) {
            // 没找到，创建新节点并插入头部（头插法效率高）
            TrieNode* new_node = (TrieNode*)calloc(1, sizeof(TrieNode));
            new_node->key = key;
            new_node->sibling = current->child;
            current->child = new_node;
            current = new_node;
        } else {
            current = found;
        }
        p++;
    }
    // 标记词尾
    current->freq = freq;
}

int trie_search_longest(TrieNode* root, const char* text, int* matched_len, int* matched_freq) {
    if (!root || !text) return 0;
    
    TrieNode* current = root;
    const unsigned char* p = (const unsigned char*)text;
    int len = 0;
    int max_len = 0;
    int max_freq = 0;
    
    // 遍历 Trie
    while (*p) {
        unsigned char key = *p;
        TrieNode* found = NULL;
        
        TrieNode* child = current->child;
        while (child) {
            if (child->key == key) {
                found = child;
                break;
            }
            child = child->sibling;
        }
        
        if (!found) break; // 路径断了
        
        current = found;
        len++;
        p++;
        
        // 如果当前节点是词尾，记录下来（贪婪匹配：继续往下找更长的）
        if (current->freq > 0) {
            max_len = len;
            max_freq = current->freq;
        }
    }
    
    if (max_len > 0) {
        if (matched_len) *matched_len = max_len;
        if (matched_freq) *matched_freq = max_freq;
        return 1;
    }
    
    return 0;
}