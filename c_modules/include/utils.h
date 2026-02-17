#ifndef UTILS_H
#define UTILS_H

#include <stdbool.h>
#include <stddef.h>

// 获取UTF-8字符的字节长度 (1-4)
int utf8_len(unsigned char c);

// 判断当前UTF-8字符是否为中文字符
bool is_chinese(const unsigned char* str);

// 辅助：安全的字符串小写转换 (仅处理ASCII部分，中文不变)
// dest 必须有足够的空间
void str_normalize_lower(char* dest, const char* src);

#endif