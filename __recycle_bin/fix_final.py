import json
import time
import requests

# 配置
MAPPING_PATH = r"d:\promptui\static\mappings_llama3_q4_highfreq.json"
DICT_PATHS = [
    (r"d:\promptui\dict\Chinese\dict.txt", 100),
    (r"d:\promptui\dict\Chinese\IT.txt", 10000),
    (r"d:\promptui\dict\Chinese\idiom.txt", 10),
]
MODEL = "llama3:8b-instruct-q4_K_M"
PORT = 11434
BATCH_SIZE = 50
SLEEP = 2
RETRY = 3

# 读取高频词
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
    all_words.update(ws)

# 读取已完成映射
try:
    with open(MAPPING_PATH, encoding="utf-8") as f:
        mappings = json.load(f).get("mappings", {})
except Exception:
    mappings = {}

# 找出缺失词
missing_words = sorted(
    [w for w in all_words if w not in mappings or not mappings[w].strip()]
)
print(f"缺失映射词数: {len(missing_words)}")


def batch(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def ollama_translate(words, model=MODEL, port=PORT, sleep=SLEEP, retry=RETRY):
    url = f"http://localhost:{port}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    prompt = (
        "请将以下中文词汇翻译为适合插画/摄影/现实场景的英文视觉标签，逗号分隔，"
        "每个词一行，格式为‘原词: 英文标签’。\n"
        "词汇：" + "、".join(words)
    )
    data = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    for attempt in range(1, retry + 1):
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=120)
            time.sleep(sleep)
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"请求失败，重试{attempt}/{retry}: {e}")
            time.sleep(3)
    return ""


def parse_response(text):
    mapping = {}
    for line in text.splitlines():
        if ":" in line:
            zh, en = line.split(":", 1)
            mapping[zh.strip()] = en.strip()
    return mapping


if __name__ == "__main__":
    updated = False
    for idx, group in enumerate(batch(missing_words, BATCH_SIZE), 1):
        print(f"补全第{idx}批...")
        try:
            result = ollama_translate(group)
            mapping = parse_response(result)
            for k, v in mapping.items():
                if k in group and v:
                    mappings[k] = v
            updated = True
        except Exception as e:
            print(f"第{idx}批补全失败: {e}")
        time.sleep(1)
    if updated:
        with open(MAPPING_PATH, "w", encoding="utf-8") as f:
            json.dump({"mappings": mappings}, f, ensure_ascii=False, indent=4)
        print(f"已补全并保存到 {MAPPING_PATH}")
    else:
        print("无新增补全，无需保存。")

    # -------- 冗余key清理并输出新文件 --------
    def is_valid_zh_key(k):
        # 只保留全中文key（可根据需要调整规则）
        return all("\u4e00" <= ch <= "\u9fff" for ch in k) and 1 <= len(k) <= 8

    cleaned = {k: v for k, v in mappings.items() if is_valid_zh_key(k)}
    cleaned_path = MAPPING_PATH.replace(".json", "_cleaned.json")
    with open(cleaned_path, "w", encoding="utf-8") as f:
        json.dump({"mappings": cleaned}, f, ensure_ascii=False, indent=4)
    print(f"已清理冗余key，输出到 {cleaned_path}")
