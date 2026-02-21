import json
import re

# 读取原文件
with open('d:/promptui/static/mappings_new.json', encoding='utf-8') as f:
    data = json.load(f)

mappings = data.get('mappings', {})

new_mappings = dict(mappings)  # 保留原字段

for key, value in mappings.items():
    # 检查 key 是否包含括号
    m = re.match(r'^(.*?)[（(](.*?)[）)]$', key)
    if m:
        # 拆分：去除括号，生成副本
        key_no_bracket = m.group(1).strip()
        if key_no_bracket and key_no_bracket not in new_mappings:
            new_mappings[key_no_bracket] = value

# 保存新文件
with open('d:/promptui/static/mappings_new_cleaned.json', 'w', encoding='utf-8') as f:
    json.dump({'mappings': new_mappings}, f, ensure_ascii=False, indent=4)

print("处理完成，已生成 mappings_new_cleaned.json。")