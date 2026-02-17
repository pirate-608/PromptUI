#ifndef ANALYZER_COMMON_H
#define ANALYZER_COMMON_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "dict.h"
#include "trie.h"

// 宏定义
#define MAX_WORD_LEN 64       // 单个词最大长度
#define MAX_SECTIONS 100      // 最大章节数
#define HASH_TABLE_SIZE 8192  // 哈希桶大小，适合万字级别文本

// 导出宏
#ifdef _WIN32
  #ifdef ANALYZER_EXPORTS
    #define EXPORT __declspec(dllexport)
  #else
    #define EXPORT __declspec(dllimport)
  #endif
#else
  #define EXPORT __attribute__((visibility("default")))
#endif

// 多语言敏感词/停用词表声明 (全局变量)
// 注意：如果从动态库外部(main.c)直接访问这些变量，在Windows下需要特殊处理
// 本项目中 main.c 通过函数调用间接使用，因此只需 extern
extern char** SENSITIVE_WORDS_CN;
extern int SENSITIVE_WORDS_CN_COUNT;
extern char** SENSITIVE_WORDS_EN;
extern int SENSITIVE_WORDS_EN_COUNT;
extern char** STOP_WORDS_CN;
extern int STOP_WORDS_CN_COUNT;
extern char** STOP_WORDS_EN;
extern int STOP_WORDS_EN_COUNT;

// 类型定义
typedef struct SectionInfo {
    int section_id;
    char title[128];
    int level;
    int length;
    double ratio;
    int word_count;
} SectionInfo;

typedef struct Stats {
    int total_chars;
    int en_words;
    int cn_chars;
    int sensitive_count;
    int redundancy_count;
    int punct_count;
    int section_count;
    double richness;
} Stats;

typedef struct AnalyzerContext {
    Dict* dict_freq;          // 有效词频
    Dict* dict_sensitive_hit; // 命中的敏感词
    Dict* set_stop;
    Dict* set_sensitive;
    Dict* set_redundant;
    TrieNode* cn_dict;        // 指向全局Trie，不负责释放
    SectionInfo sections[MAX_SECTIONS];
    int section_idx;
    int current_section_char_count;
    Stats stats;
} AnalyzerContext;


// --- 接口声明 ---

// 词表/词典加载与热更新接口（list.c实现）
EXPORT int load_all_sensitive_and_stop_words(void);
EXPORT int load_all_dicts(const char** paths, int count);

// Analyzer主流程相关声明
EXPORT AnalyzerContext* Analyzer_Create(void);
EXPORT void Analyzer_Free(AnalyzerContext* ctx);
EXPORT void Analyzer_AddStopWord(AnalyzerContext* ctx, const char* word);
EXPORT void Analyzer_AddSensitiveWord(AnalyzerContext* ctx, const char* word);
EXPORT void Analyzer_AddRedundantWord(AnalyzerContext* ctx, const char* word);
EXPORT void Analyzer_Process(AnalyzerContext* ctx, const char* text);
EXPORT Stats Analyzer_GetStats(AnalyzerContext* ctx);
EXPORT void Analyzer_GetTopWords(AnalyzerContext* ctx, WordFreq* out_arr, int n);
EXPORT void Analyzer_GetSensitiveWords(AnalyzerContext* ctx, WordFreq* out_arr, int n);
EXPORT void Analyzer_GetSections(AnalyzerContext* ctx, SectionInfo* out_arr, int n);

// 核心分析接口：输入内容，输出JSON
EXPORT int analyze_text(const char* content, char* result_json, int buf_size);

// 分词词典加载/热更新接口
EXPORT int Analyzer_LoadCNDict(AnalyzerContext* ctx, const char* dict_path);
EXPORT int Analyzer_RefreshCNDict(const char* dict_path);

// 枚举类型
typedef enum {
    LANG_UNKNOWN = 0,
    LANG_EN,
    LANG_CN
} Language;

#ifdef __cplusplus
}
#endif

#endif // ANALYZER_COMMON_H
