#ifndef TRIE_H
#define TRIE_H

#include <stddef.h>

// Trie 节点结构 (对外部隐藏具体实现，如果需要也可以公开)
typedef struct TrieNode TrieNode;

// 创建/销毁
TrieNode* trie_create(void);
void trie_free(TrieNode* root);

// 插入词语 (word: UTF-8字符串, freq: 词频)
void trie_insert(TrieNode* root, const char* word, int freq);

// 正向最大匹配查找
// text: 当前文本指针
// matched_len: 输出匹配到的字节长度（如果没有匹配则为0）
// matched_freq: 输出匹配到的词的词频
// 返回: 是否匹配成功 (1=是, 0=否)
int trie_search_longest(TrieNode* root, const char* text, int* matched_len, int* matched_freq);

#endif