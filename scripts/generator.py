import requests
import json
import time

# 1. 读取中文词表（合并多个文件，去重）
def load_chinese_words(*files):
    words = set()
    for file in files:
        with open(file, encoding='utf-8') as f:
            for line in f:
                word = line.strip().split()[0]  # 只取词条
                if word and all('\u4e00' <= ch <= '\u9fff' for ch in word):  # 只保留全中文
                    words.add(word)
    return sorted(words)

# 2. 批量分组
def batch(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

# 3. 调用 Ollama 本地模型
def ollama_translate(words, model='llama3:8b-instruct-q4_K_M', port=11434, sleep=2):
    url = f'http://localhost:{port}/v1/chat/completions'
    headers = {'Content-Type': 'application/json'}
    prompt = (
        "请将以下中文词汇翻译为适合插画/摄影/现实场景的英文视觉标签，逗号分隔，"
        "每个词一行，格式为“原词: 英文标签”。\n"
        "词汇：" + "、".join(words)
    )
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }
    resp = requests.post(url, headers=headers, json=data, timeout=120)
    time.sleep(sleep)  # 防止接口压力过大
    return resp.json()['choices'][0]['message']['content']

# 4. 解析 Ollama 返回
def parse_response(text):
    mapping = {}
    for line in text.splitlines():
        if ':' in line:
            zh, en = line.split(':', 1)
            mapping[zh.strip()] = en.strip()
    return mapping

# 5. 主流程
if __name__ == '__main__':
    # 文件路径
    files = [
        r'd:\promptui\dict\Chinese\dict.txt',
        r'd:\promptui\dict\Chinese\IT.txt',
        r'd:\promptui\dict\Chinese\idiom.txt'
    ]
    all_words = load_chinese_words(*files)
    print(f'共{len(all_words)}个中文词')

    all_mapping = {}
    batch_size = 50  # 每批处理50个词
    for idx, group in enumerate(batch(all_words, batch_size), 1):
        print(f'处理第{idx}批...')
        try:
            result = ollama_translate(group)
            mapping = parse_response(result)
            all_mapping.update(mapping)
        except Exception as e:
            print(f'第{idx}批处理失败: {e}')
        time.sleep(1)  # 可适当调整

    # 输出为 mappings.json
    with open(r'd:\promptui\static\mappings_ollama.json', 'w', encoding='utf-8') as f:
        json.dump({'mappings': all_mapping}, f, ensure_ascii=False, indent=4)
    print('已生成 d:\\promptui\\static\\mappings_ollama.json')