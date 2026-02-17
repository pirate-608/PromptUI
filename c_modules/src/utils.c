#include "utils.h"
#include <ctype.h>

int utf8_len(unsigned char c) {
    if ((c & 0x80) == 0) return 1;
    if ((c & 0xE0) == 0xC0) return 2;
    if ((c & 0xF0) == 0xE0) return 3; 
    if ((c & 0xF8) == 0xF0) return 4;
    return 1; // 默认为1，防止死循环
}

bool is_chinese(const unsigned char* str) {
    // 粗略判断：3字节且在常见汉字范围内
    // 范围覆盖：E4~E9 开头的大部分常用汉字
    int len = utf8_len(*str);
    if (len == 3) {
        if (*str >= 0xE4 && *str <= 0xE9) return true;
    }
    return false;
}

void str_normalize_lower(char* dest, const char* src) {
    while (*src) {
        if (!(*src & 0x80)) { // ASCII
            *dest = tolower(*src);
        } else {
            *dest = *src;
        }
        dest++;
        src++;
    }
    *dest = '\0';
}