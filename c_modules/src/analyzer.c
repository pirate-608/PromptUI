#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdio.h>
#include <math.h>
#include <stddef.h>
#include <pthread.h>

#include "analyzer_common.h"
#include "dict.h"
#include "utils.h"
#include "trie.h"

// 全局静态Trie树指针及互斥锁
static TrieNode* g_cn_dict = NULL;
static int g_cn_dict_loaded = 0;
static pthread_mutex_t g_cn_dict_mutex = PTHREAD_MUTEX_INITIALIZER;
// 全局只加载一次敏感词/停用词
static pthread_once_t g_words_once = PTHREAD_ONCE_INIT;
static void ensure_sensitive_and_stop_words_loaded_once() {
    load_all_sensitive_and_stop_words();
}

static void load_main_dicts_once() {
    int dict_cnt = Analyzer_LoadCNDict(NULL, "./dict/Chinese/dict.txt");
    int it_cnt = Analyzer_LoadCNDict(NULL, "./dict/Chinese/IT.txt");
    int idiom_cnt = Analyzer_LoadCNDict(NULL, "./dict/Chinese/idiom.txt");
    int sensitive_cnt = Analyzer_LoadCNDict(NULL, "./dict/Chinese/sensitive_words_cn.txt");
    int stop_cnt = Analyzer_LoadCNDict(NULL, "./dict/Chinese/stop_words_cn.txt");
    if (dict_cnt == 0 || it_cnt == 0 || idiom_cnt == 0) {
        fprintf(stderr, "[FATAL] Dictionary load failed: dict.txt=%d, IT.txt=%d, idiom.txt=%d\n", dict_cnt, it_cnt, idiom_cnt);
        exit(1);
    }
}

// 支持多文件合并加载分词词典
static int load_dict_file_to_trie(TrieNode* trie, const char* dict_path) {
    FILE* fp = fopen(dict_path, "r");
    if (!fp) {
        printf("[Warning] Cannot open dictionary: %s (Check path relative to executable)\n", dict_path);
        return 0;
    }
    char line[512];
    char word[256];
    int freq;
    int count = 0;
    while (fgets(line, sizeof(line), fp)) {
        char* p = line;
        while (*p == ' ' || *p == '\t') p++;
        if (*p == 0 || *p == '\n' || *p == '\r') continue;
        
        // 尝试 "词 频" 格式
        if (sscanf(p, "%255s %d", word, &freq) >= 2) {
            trie_insert(trie, word, freq);
            count++;
            continue;
        }
        // 尝试 "词\t频" 或仅 "词"
        if (sscanf(p, "%255s", word) == 1) {
            // 如果后面有数字则读取，否则默认为1
            // 这里简单处理，若无频次默认1
            trie_insert(trie, word, 1); 
            count++;
        }
    }
    fclose(fp);
    return count;
}

EXPORT int Analyzer_LoadCNDict(AnalyzerContext* ctx, const char* dict_path) {
    pthread_mutex_lock(&g_cn_dict_mutex);
    // 首次加载或全局加载时创建/复用 Trie
    if (!g_cn_dict) {
        g_cn_dict = trie_create();
    }
    
    int total = 0;
    if (dict_path) {
        // 加载指定文件
        total += load_dict_file_to_trie(g_cn_dict, dict_path);
    } 
    
    g_cn_dict_loaded = 1;
    if (ctx) ctx->cn_dict = g_cn_dict;
    
    pthread_mutex_unlock(&g_cn_dict_mutex);
    return total;
}

EXPORT int Analyzer_RefreshCNDict(const char* dict_path) {
    pthread_mutex_lock(&g_cn_dict_mutex);
    FILE* fp = fopen(dict_path, "r");
    if (!fp) {
        pthread_mutex_unlock(&g_cn_dict_mutex);
        return -1;
    }
    // 创建新树
    TrieNode* new_trie = trie_create();
    load_dict_file_to_trie(new_trie, dict_path); // 复用加载逻辑
    fclose(fp);
    
    // 切换
    if (g_cn_dict) trie_free(g_cn_dict);
    g_cn_dict = new_trie;
    g_cn_dict_loaded = 1;
    
    pthread_mutex_unlock(&g_cn_dict_mutex);
    return 0;
}

// 简单JSON转义
static void json_escape(const char* src, char* dst, size_t dst_size) {
    size_t j = 0;
    for (size_t i = 0; src[i] && j + 2 < dst_size; ++i) {
        unsigned char c = (unsigned char)src[i];
        if (c == '\\') { dst[j++] = '\\'; dst[j++] = '\\'; }
        else if (c == '"') { dst[j++] = '\\'; dst[j++] = '"'; }
        else if (c == '\n') { dst[j++] = '\\'; dst[j++] = 'n'; }
        else if (c == '\r') { dst[j++] = '\\'; dst[j++] = 'r'; }
        else if (c == '\t') { dst[j++] = '\\'; dst[j++] = 't'; }
        else if (c < 0x20) { /* 忽略其他控制字符或转义 */ }
        else { dst[j++] = c; }
    }
    dst[j] = '\0';
}

EXPORT int analyze_text(const char* content, char* result_json, int buf_size) {
    // ...existing code...
    pthread_once(&g_words_once, ensure_sensitive_and_stop_words_loaded_once);
    // 自动加载分词主词典（只加载一次），必须在AnalyzerContext创建前
    static pthread_once_t g_dict_once = PTHREAD_ONCE_INIT;
    pthread_once(&g_dict_once, load_main_dicts_once);
    if (!content || !result_json || buf_size < 256) return -1;
    AnalyzerContext* ctx = Analyzer_Create();
    if (!ctx) return -1;
    // ...existing code...
    
    Analyzer_Process(ctx, content);
    Stats stats = Analyzer_GetStats(ctx);

    // 1. Sections JSON
    char* sections_json = (char*)malloc(buf_size / 2); // 临时分配以防栈溢出
    if(!sections_json) { Analyzer_Free(ctx); return -1; }
    
    int offset = 0;
    offset += snprintf(sections_json + offset, buf_size/2 - offset, "[");
    for (int i = 0; i < stats.section_count && offset < buf_size/2 - 100; ++i) {
        char esc_title[256];
        json_escape(ctx->sections[i].title, esc_title, sizeof(esc_title));
        int n = snprintf(sections_json + offset, buf_size/2 - offset,
            "%s{\"section_id\":%d,\"title\":\"%s\",\"level\":%d,\"length\":%d,\"ratio\":%.4f}",
            (i > 0) ? "," : "", i, esc_title, ctx->sections[i].level, ctx->sections[i].length, ctx->sections[i].ratio);
        if (n < 0 || n >= (int)(buf_size/2 - offset)) break;
        offset += n;
    }
    strcat(sections_json, "]");

    // 2. Top Words JSON
    WordFreq top_words[10];
    Analyzer_GetTopWords(ctx, top_words, 10);
    char top_words_json[1024];
    int tw_off = snprintf(top_words_json, sizeof(top_words_json), "[");
    for (int i = 0; i < 10; ++i) {
        if (!top_words[i].word || !*top_words[i].word) break;
        tw_off += snprintf(top_words_json + tw_off, sizeof(top_words_json) - tw_off,
            "%s{\"word\":\"%s\",\"freq\":%d}",
            (i > 0) ? "," : "", top_words[i].word, top_words[i].count);
    }
    strcat(top_words_json, "]");

    // 3. Sensitive Words JSON
    char sensitive_json[1024];
    int s_off = snprintf(sensitive_json, sizeof(sensitive_json), "[");
    dict_iter_t it = dict_iter(ctx->dict_sensitive_hit);
    int sens_cnt = 0;
    while (dict_next(&it) && s_off < sizeof(sensitive_json) - 50) {
        if (sens_cnt > 0) s_off += snprintf(sensitive_json + s_off, sizeof(sensitive_json) - s_off, ",");
        s_off += snprintf(sensitive_json + s_off, sizeof(sensitive_json) - s_off, "\"%s\"", it.key);
        sens_cnt++;
    }
    strcat(sensitive_json, "]");

    // Final Assemble
    int n = snprintf(result_json, buf_size,
        "{\"total_chars\":%d,\"en_words\":%d,\"cn_chars\":%d,\"words\":%d,\"sensitive_count\":%d,\"redundancy_count\":%d,\"punct_count\":%d,\"section_count\":%d,\"richness\":%.2f,\"sections\":%s,\"top_words\":%s,\"sensitive_words\":%s}",
        stats.total_chars, stats.en_words, stats.cn_chars, stats.en_words + stats.cn_chars, 
        stats.sensitive_count, stats.redundancy_count, stats.punct_count, stats.section_count, 
        stats.richness, sections_json, top_words_json, sensitive_json);

    free(sections_json);
    Analyzer_Free(ctx);
    return (n > 0 && n < buf_size) ? 0 : -1;
}

EXPORT AnalyzerContext* Analyzer_Create() {
    AnalyzerContext* ctx = (AnalyzerContext*)calloc(1, sizeof(AnalyzerContext));
    if(!ctx) return NULL;
    
    ctx->dict_freq = dict_create();
    ctx->dict_sensitive_hit = dict_create();
    ctx->set_stop = dict_create();
    ctx->set_sensitive = dict_create();
    ctx->set_redundant = dict_create();
    
    // 默认章节
    strcpy(ctx->sections[0].title, "Introduction");
    ctx->sections[0].level = 0;
    
    // 关联全局Trie
    pthread_mutex_lock(&g_cn_dict_mutex);
    if (g_cn_dict) ctx->cn_dict = g_cn_dict;
    pthread_mutex_unlock(&g_cn_dict_mutex);

    // 注入停用词/敏感词
    for (int i = 0; i < STOP_WORDS_CN_COUNT; i++) if (STOP_WORDS_CN[i]) Analyzer_AddStopWord(ctx, STOP_WORDS_CN[i]);
    for (int i = 0; i < SENSITIVE_WORDS_CN_COUNT; i++) if (SENSITIVE_WORDS_CN[i]) Analyzer_AddSensitiveWord(ctx, SENSITIVE_WORDS_CN[i]);
    
    for (int i = 0; i < STOP_WORDS_EN_COUNT; i++) {
        if (STOP_WORDS_EN[i]) {
            char lower[256];
            str_normalize_lower(lower, STOP_WORDS_EN[i]); // 使用 utils 中的 helper
            Analyzer_AddStopWord(ctx, lower);
        }
    }
    for (int i = 0; i < SENSITIVE_WORDS_EN_COUNT; i++) if (SENSITIVE_WORDS_EN[i]) Analyzer_AddSensitiveWord(ctx, SENSITIVE_WORDS_EN[i]);

    return ctx;
}

EXPORT void Analyzer_Free(AnalyzerContext* ctx) {
    if (!ctx) return;
    dict_free(ctx->dict_freq);
    dict_free(ctx->dict_sensitive_hit);
    dict_free(ctx->set_stop);
    dict_free(ctx->set_sensitive);
    dict_free(ctx->set_redundant);
    // ctx->cn_dict is shared, do not free
    free(ctx);
}

EXPORT void Analyzer_AddStopWord(AnalyzerContext* ctx, const char* word) { dict_add(ctx->set_stop, word); }
EXPORT void Analyzer_AddSensitiveWord(AnalyzerContext* ctx, const char* word) { dict_add(ctx->set_sensitive, word); }
EXPORT void Analyzer_AddRedundantWord(AnalyzerContext* ctx, const char* word) { dict_add(ctx->set_redundant, word); }

EXPORT void Analyzer_Process(AnalyzerContext* ctx, const char* text) {
    if (!ctx || !text) return;
    const unsigned char* p = (const unsigned char*)text;
    char buffer[MAX_WORD_LEN];  
    int buf_idx = 0;
    bool is_line_start = true;

    while (*p) {
        int len = utf8_len(*p);

        if (buf_idx == 0 && ctx->cn_dict && len > 1) {
            // ...existing code...
        }

        // --- 1. Markdown Header Check ---
        if (is_line_start && *p == '#') {
            int level = 0;
            const unsigned char* temp = p;
            while (*temp == '#' && level < 6) { level++; temp++; }
            if (*temp == ' ') { 
                // 结算上一章
                ctx->sections[ctx->section_idx].length = ctx->current_section_char_count;
                // 新章
                if (ctx->section_idx < MAX_SECTIONS - 1) ctx->section_idx++;
                ctx->sections[ctx->section_idx].level = level;
                ctx->current_section_char_count = 0;
                
                temp++; // Skip space
                int t_idx = 0;
                while (*temp && *temp != '\n' && *temp != '\r' && t_idx < 127) {
                    ctx->sections[ctx->section_idx].title[t_idx++] = *temp++;
                }
                ctx->sections[ctx->section_idx].title[t_idx] = '\0';
                
                p = temp; 
                while(*p == '\r' || *p == '\n') p++; // Skip newline
                is_line_start = true;
                continue; 
            }
        }

        ctx->stats.total_chars++;
        ctx->current_section_char_count++;

        // --- 2. Chinese FMM (Trie) ---
        if (buf_idx == 0 && ctx->cn_dict && len > 1) { // 仅尝试多字节字符开头
            int matched_len = 0;
            int matched_freq = 0;
            if (trie_search_longest(ctx->cn_dict, (const char*)p, &matched_len, &matched_freq)) {
                // ...existing code...
                // 提取
                char matched_word[MAX_WORD_LEN];
                int copy_len = (matched_len < MAX_WORD_LEN) ? matched_len : (MAX_WORD_LEN - 1);
                strncpy(matched_word, (const char*)p, copy_len);
                matched_word[copy_len] = '\0';

                // 统计字数
                for (int i = 0; i < matched_len; ) {
                    const unsigned char* sub_p = p + i;
                    int sub_len = utf8_len(*sub_p);
                    if (is_chinese(sub_p)) ctx->stats.cn_chars++;
                    i += sub_len;
                }

                if (dict_get(ctx->set_sensitive, matched_word)) {
                    // ...existing code...
                    ctx->stats.sensitive_count++;
                    dict_add(ctx->dict_sensitive_hit, matched_word);
                } else if (dict_get(ctx->set_redundant, matched_word)) {
                    // ...existing code...
                    ctx->stats.redundancy_count++;
                } else if (!dict_get(ctx->set_stop, matched_word)) {
                    // ...existing code...
                    dict_add(ctx->dict_freq, matched_word);
                }

                p += matched_len;
                is_line_start = false;
                continue;
            }
        }

        // --- 3. Default Processing ---
        if (len == 1) {
            // ASCII
            if (isalpha(*p)) {
                // ...existing code...
                if (buf_idx < MAX_WORD_LEN - 1) buffer[buf_idx++] = tolower(*p);
            } else {
                // Not alpha (number, punct, space) -> Flush Buffer
                if (buf_idx > 0) {
                    // ...existing code...
                     buffer[buf_idx] = '\0';
                     ctx->stats.en_words++;
                     if (dict_get(ctx->set_sensitive, buffer)) {
                         // ...existing code...
                         ctx->stats.sensitive_count++;
                         dict_add(ctx->dict_sensitive_hit, buffer);
                     } else if (!dict_get(ctx->set_stop, buffer)) {
                         // ...existing code...
                         dict_add(ctx->dict_freq, buffer);
                     }
                     buf_idx = 0;
                }
                if (ispunct(*p)) ctx->stats.punct_count++;
            }
            if (*p == '\n') is_line_start = true; else is_line_start = false;
            p++;
        } else {
            // Multibyte fallback
            if (buf_idx > 0) { // Flush pending EN word
                // ...existing code...
                 buffer[buf_idx] = '\0';
                 ctx->stats.en_words++;
                 if (!dict_get(ctx->set_stop, buffer)) dict_add(ctx->dict_freq, buffer);
                 buf_idx = 0;
            }

            char mb_char[5] = {0};
            for(int i=0; i<len; i++) mb_char[i] = p[i];
            
            if (is_chinese(p)) {
                // ...existing code...
                ctx->stats.cn_chars++;
                if (dict_get(ctx->set_sensitive, mb_char)) {
                    // ...existing code...
                    ctx->stats.sensitive_count++;
                    dict_add(ctx->dict_sensitive_hit, mb_char);
                } else if (!dict_get(ctx->set_stop, mb_char)) {
                    // ...existing code...
                    dict_add(ctx->dict_freq, mb_char);
                }
            } else {
                ctx->stats.punct_count++;
            }
            p += len;
            is_line_start = false;
        }
    }
    
    // Flush final buffer
    if (buf_idx > 0) {
        buffer[buf_idx] = '\0';
        ctx->stats.en_words++;
        if (!dict_get(ctx->set_stop, buffer)) dict_add(ctx->dict_freq, buffer);
    }
    
    // Finish stats
    ctx->sections[ctx->section_idx].length = ctx->current_section_char_count;
    ctx->stats.section_count = ctx->section_idx + 1;
    
    int valid_len_total = 0;
    for (int i=0; i <= ctx->section_idx; i++) valid_len_total += ctx->sections[i].length;
    if (valid_len_total > 0) {
        for (int i=0; i <= ctx->section_idx; i++) ctx->sections[i].ratio = (double)ctx->sections[i].length / valid_len_total;
    }

    if (ctx->dict_freq->total_count > 0)
        ctx->stats.richness = (double)ctx->dict_freq->unique_count / sqrt(2.0 * ctx->dict_freq->total_count);
}

EXPORT Stats Analyzer_GetStats(AnalyzerContext* ctx) { return ctx->stats; }
EXPORT void Analyzer_GetTopWords(AnalyzerContext* ctx, WordFreq* out_arr, int n) { dict_get_top(ctx->dict_freq, out_arr, n); }
EXPORT void Analyzer_GetSensitiveWords(AnalyzerContext* ctx, WordFreq* out_arr, int n) { dict_get_top(ctx->dict_sensitive_hit, out_arr, n); }
EXPORT void Analyzer_GetSections(AnalyzerContext* ctx, SectionInfo* out_arr, int n) {
    int count = (ctx->section_idx + 1 > n) ? n : ctx->section_idx + 1;
    for (int i=0; i<count; i++) out_arr[i] = ctx->sections[i];
}