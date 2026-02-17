#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include "analyzer_common.h"

// 全局变量定义（DLL中）
char** SENSITIVE_WORDS_CN = NULL;
int SENSITIVE_WORDS_CN_COUNT = 0;
char** SENSITIVE_WORDS_EN = NULL;
int SENSITIVE_WORDS_EN_COUNT = 0;
char** STOP_WORDS_CN = NULL;
int STOP_WORDS_CN_COUNT = 0;
char** STOP_WORDS_EN = NULL;
int STOP_WORDS_EN_COUNT = 0;

static pthread_mutex_t sensitive_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t stop_mutex = PTHREAD_MUTEX_INITIALIZER;

static void free_str_array(char** arr, int count) {
    if (!arr) return;
    for (int i = 0; i < count; i++) free(arr[i]);
    free(arr);
}

static int load_word_file(const char* path, char*** out_arr) {
    FILE* fp = fopen(path, "r");
    if (!fp) {
        // printf("Skipping missing file: %s\n", path);
        return 0;
    }
    char** arr = NULL;
    int cap = 128, cnt = 0;
    arr = (char**)malloc(sizeof(char*) * cap);
    char line[256];
    while (fgets(line, sizeof(line), fp)) {
        char* p = line;
        while (*p == ' ' || *p == '\t') p++;
        size_t len = strlen(p);
        while (len > 0 && (p[len-1] == '\r' || p[len-1] == '\n')) {
            p[len-1] = 0;
            len--;
        }
        if (*p == 0) continue;
        
        if (cnt >= cap) {
            cap *= 2;
            char** temp = (char**)realloc(arr, sizeof(char*) * cap);
            if (!temp) break; // 内存不足
            arr = temp;
        }
        arr[cnt++] = strdup(p);
    }
    fclose(fp);
    *out_arr = arr;
    return cnt;
}

EXPORT int load_all_sensitive_and_stop_words() {
    int total = 0;
    char** arr = NULL;
    int cnt;

    // 假设运行目录在 build/bin 或类似位置，词典在 ../text_analyzer/dict/
    // 请根据实际部署调整路径
    

    cnt = load_word_file("./dict/Chinese/sensitive_words_cn.txt", &arr);
    pthread_mutex_lock(&sensitive_mutex);
    if(SENSITIVE_WORDS_CN) free_str_array(SENSITIVE_WORDS_CN, SENSITIVE_WORDS_CN_COUNT);
    SENSITIVE_WORDS_CN = arr; SENSITIVE_WORDS_CN_COUNT = cnt;
    pthread_mutex_unlock(&sensitive_mutex);
    total += cnt;

    arr = NULL;
    cnt = load_word_file("./dict/English/sensitive_words_en.txt", &arr);
    pthread_mutex_lock(&sensitive_mutex);
    if(SENSITIVE_WORDS_EN) free_str_array(SENSITIVE_WORDS_EN, SENSITIVE_WORDS_EN_COUNT);
    SENSITIVE_WORDS_EN = arr; SENSITIVE_WORDS_EN_COUNT = cnt;
    pthread_mutex_unlock(&sensitive_mutex);
    total += cnt;

    arr = NULL;
    cnt = load_word_file("./dict/Chinese/stop_words_cn.txt", &arr);
    pthread_mutex_lock(&stop_mutex);
    if(STOP_WORDS_CN) free_str_array(STOP_WORDS_CN, STOP_WORDS_CN_COUNT);
    STOP_WORDS_CN = arr; STOP_WORDS_CN_COUNT = cnt;
    pthread_mutex_unlock(&stop_mutex);
    total += cnt;

    arr = NULL;
    cnt = load_word_file("./dict/English/stop_words_en.txt", &arr);
    pthread_mutex_lock(&stop_mutex);
    if(STOP_WORDS_EN) free_str_array(STOP_WORDS_EN, STOP_WORDS_EN_COUNT);
    STOP_WORDS_EN = arr; STOP_WORDS_EN_COUNT = cnt;
    pthread_mutex_unlock(&stop_mutex);
    total += cnt;

    return total;
}

EXPORT int load_all_dicts(const char** paths, int count) {
    return count; // 实际逻辑在 Analyzer_LoadCNDict 循环调用中完成
}