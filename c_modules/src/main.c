#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "analyzer_common.h"

#ifdef _WIN32
#include <windows.h>
#endif

#define TXT_BUF_SIZE (2 * 1024 * 1024) // 2MB

size_t read_txt_file(const char* path, char* buf, size_t maxlen) {
    FILE* fp = fopen(path, "r");
    if (!fp) {
        printf("[Error] Cannot open file: %s\n", path);
        return 0;
    }
    size_t len = fread(buf, 1, maxlen - 1, fp);
    buf[len] = '\0';
    fclose(fp);
    return len;
}

void print_top_words_from_json(const char* json) {
    // 简易解析，仅用于演示
    const char* key = "\"top_words\":[";
    char* p = strstr(json, key);
    if (!p) return;
    p += strlen(key);
    
    printf("\nTop Words:\n");
    int i = 1;
    while (*p && *p != ']') {
        char w[64] = {0};
        int f = 0;
        char* w_start = strstr(p, "\"word\":\"");
        char* f_start = strstr(p, "\"freq\":");
        if(!w_start || !f_start) break;
        
        w_start += 8;
        int k=0;
        while(w_start[k] && w_start[k] != '"' && k<63) { w[k] = w_start[k]; k++; }
        
        sscanf(f_start, "\"freq\":%d", &f);
        
        printf("  %2d. %-15s (%d)\n", i++, w, f);
        
        p = strchr(f_start, '}');
        if(!p) break;
        p++;
    }
}

int main(int argc, char** argv) {
    #ifdef _WIN32
    SetConsoleOutputCP(65001);
    #endif

    printf("==== Text Analyzer CLI ====\n");

    // 1. 初始化
    printf("Loading dictionaries...\n");
    int w_count = load_all_sensitive_and_stop_words();
    printf("- Loaded %d sensitive/stop words.\n", w_count);

    printf("Loaded Sensitive Words (CN):\n");
    for (int i = 0; i < SENSITIVE_WORDS_CN_COUNT; ++i) {
        if (SENSITIVE_WORDS_CN[i]) printf("  [%d] %s\n", i, SENSITIVE_WORDS_CN[i]);
    }
    printf("Loaded Sensitive Words (EN):\n");
    for (int i = 0; i < SENSITIVE_WORDS_EN_COUNT; ++i) {
        if (SENSITIVE_WORDS_EN[i]) printf("  [%d] %s\n", i, SENSITIVE_WORDS_EN[i]);
    }

    // 分词词典由analyze_text自动全局加载，无需手动加载

    char path[512];
    if (argc > 1) {
        strcpy(path, argv[1]);
    } else {
        printf("Enter file path: ");
        if (!fgets(path, sizeof(path), stdin)) return 0;
        path[strcspn(path, "\r\n")] = 0;
    }

    if (strlen(path) == 0) return 0;

    char* buf = (char*)malloc(TXT_BUF_SIZE);
    if (!buf) return -1;
    
    size_t len = read_txt_file(path, buf, TXT_BUF_SIZE);
    if (len > 0) {
        printf("Analyzing %zu bytes...\n", len);
        
        // 方式1：直接使用JSON接口
        char* json_out = (char*)malloc(TXT_BUF_SIZE); // 结果可能很大
        if (json_out) {
            if (analyze_text(buf, json_out, TXT_BUF_SIZE) == 0) {
                print_top_words_from_json(json_out);
                // printf("\nRaw JSON:\n%s\n", json_out); 
            } else {
                printf("Analysis failed (buffer too small?)\n");
            }
            free(json_out);
        }
    }

    free(buf);
    return 0;
}