import csv
import json
from collections import defaultdict

# 输入文件路径
csv_path = r'c:\Users\think\Downloads\danbooru-10w-zh_cn.csv'
output_path = r'd:\promptui\static\mappings_new.json'

# 1. 构建英文→中文、中文→英文映射
en2zh = defaultdict(list)
zh2en = defaultdict(set)

with open(csv_path, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or ',' not in line:
            continue
        en, zh_str = line.split(',', 1)
        zh_list = [z.strip() for z in zh_str.split() if z.strip()]
        for zh in zh_list:
            en2zh[en].append(zh)
            zh2en[zh].add(en)

# 2. 可选：筛选高频中文（如出现英文标签数≥2）
min_en_count = 1  # 可调整
zh2en_final = {}
for zh, en_set in zh2en.items():
    if len(en_set) >= min_en_count:
        zh2en_final[zh] = ', '.join(sorted(en_set))

# 3. 可选：只保留部分优质英文标签（如只保留人物、场景等）
# 可扩展：根据英文标签前缀、类别等筛选

# 4. 输出为 mappings.json
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump({'mappings': zh2en_final}, f, ensure_ascii=False, indent=4)

print(f"已生成 {output_path}，共 {len(zh2en_final)} 个中文关键词。")