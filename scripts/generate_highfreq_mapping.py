import requests
import json
import time

# 1. 词表及高频界限配置
DICT_PATHS = [
    (r"d:\promptui\dict\Chinese\dict.txt", 100),  # dict.txt 高频界限
    (r"d:\promptui\dict\Chinese\IT.txt", 10000),  # IT.txt 高频界限
    (r"d:\promptui\dict\Chinese\idiom.txt", 10),  # idiom.txt 高频界限
]
MODEL = "llama3:8b-instruct-q4_K_M"
PORT = 11434
BATCH_SIZE = 50
SLEEP = 2
OUTPUT_PATH = r"d:\promptui\static\mappings_llama3_q4_highfreq.json"

# 2. 读取高频词
all_words = set()


def load_highfreq_words(path, freq_limit):
    words = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            word, freq = parts[0], parts[1]
            try:
                freq = int(freq)
            except Exception:
                continue
            if freq >= freq_limit and all("\u4e00" <= ch <= "\u9fff" for ch in word):
                words.add(word)
    return words


for path, limit in DICT_PATHS:
    ws = load_highfreq_words(path, limit)
    print(f"{path} 高频词 {len(ws)} 个 (界限: {limit})")
    all_words.update(ws)

all_words = sorted(all_words)
print(f"总高频词数: {len(all_words)}")


def batch(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def ollama_translate(words, model=MODEL, port=PORT, sleep=SLEEP):
    url = f"http://localhost:{port}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    prompt = (
        "请将以下中文词汇翻译为适合插画/摄影/现实场景的英文视觉标签，逗号分隔，"
        "每个词一行，格式为‘原词: 英文标签’。\n"
        "词汇：" + "、".join(words)
    )
    data = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    resp = requests.post(url, headers=headers, json=data, timeout=120)
    time.sleep(sleep)
    return resp.json()["choices"][0]["message"]["content"]


def parse_response(text):
    mapping = {}
    for line in text.splitlines():
        if ":" in line:
            zh, en = line.split(":", 1)
            mapping[zh.strip()] = en.strip()
    return mapping


if __name__ == "__main__":
    all_mapping = {}
    for idx, group in enumerate(batch(all_words, BATCH_SIZE), 1):
        print(f"处理第{idx}批...")
        try:
            result = ollama_translate(group)
            mapping = parse_response(result)
            all_mapping.update(mapping)
        except Exception as e:
            print(f"第{idx}批处理失败: {e}")
        time.sleep(1)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"mappings": all_mapping}, f, ensure_ascii=False, indent=4)
    print(f"已生成 {OUTPUT_PATH}")
