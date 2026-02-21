# 视觉映射
import json
import os
import sys
from typing import List, Dict, Set


class VisualMapper:
    def __init__(
        self, mappings_filename: str = "mappings.json", styles_filename: str = None
    ):
        """
        初始化视觉映射器
        :param mappings_filename: 主标签映射文件名，默认 static/mappings.json
        :param styles_filename: 风格映射文件名，默认None（可选）
        """
        self.mappings: Dict[str, str] = {}
        self.styles: Dict[str, str] = {}

        # 1. 设置默认内置配置 (兜底策略)
        self._set_defaults()

        # 2. 加载主映射文件
        self._load_mappings_file(mappings_filename)

        # 3. 加载风格映射文件（可选）
        if styles_filename:
            self._load_styles_file(styles_filename)

    def _set_defaults(self):
        """内置默认映射，防止配置文件丢失导致功能不可用"""
        self.mappings = {
            # --- 情绪 ---
            "悲伤": "crying, tears, sad expression, gloomy atmosphere, rainy background",
            "开心": "smile, happy, laughing, bright eyes, sparkles",
            "愤怒": "angry, veins pop, shouting, aggressive pose, fire background",
            "惊讶": "surprised, open mouth, wide eyes, shock lines",
            "绝望": "despair, empty eyes, dark background, shadow over face",
            # --- 场景 ---
            "学校": "classroom, school desk, chalkboard, school uniform, sunlight through window",
            "医院": "hospital room, medical equipment, white bed, clinical atmosphere",
            "家": "living room, cozy, indoor, furniture, sofa",
            "街道": "city street, outdoors, buildings, crowd, traffic",
            "办公室": "office, desk, computer, documents, business suit",
            # --- 人物/特定概念 (针对你的示例) ---
            "巨婴": "immature adult, childish behavior, holding toys, messy, tantrum",
            "离婚": "broken ring, divorce papers, separate, arguing, back to back",
            "钱": "holding money, cash, rich, currency, bank notes",
            "补偿": "stack of money, transaction, handshake, business deal",
            "家务": "cleaning, apron, vacuum cleaner, washing dishes",
            "孩子": "child, baby, playing, toys, cute",
        }

        self.styles = {
            "清新简洁": "masterpiece, best quality, flat color, anime style, simple background, bright",
            "赛博朋克": "cyberpunk, neon lights, sci-fi, futuristic, dark atmosphere, glowing",
            "黑白线稿": "monochrome, lineart, manga style, ink, sketch, screentones",
            "鲜艳活泼": "vibrant colors, energetic, dynamic angle, highly detailed, saturation high",
            "水墨古风": "chinese traditional ink painting, watercolor, calligraphy brush, mountain landscape",
            "日系动漫": "anime key visual, cel shaded, vibrant colors, manga style, japanese animation aesthetic, detailed lineart"
        }

    def _load_mappings_file(self, filename: str):
        """加载主标签映射文件（只取mappings字段）"""
        try:
            config_path = self._get_resource_path(os.path.join("static", filename))
            if not os.path.exists(config_path):
                print(
                    f"[VisualMapper] Warning: Mappings file not found at {config_path}, using defaults."
                )
                return
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "mappings" in data:
                    self.mappings.update(data["mappings"])
            print(f"[VisualMapper] Loaded mappings from {config_path}")
        except Exception as e:
            print(f"[VisualMapper] Error loading mappings: {e}, using defaults.")
    
    def load_acgn_mappings(self, acgn_filename: str = "mappings/mappings_acgn.json"):
            """按需加载ACGN（日系动漫）专用映射"""
            try:
                config_path = self._get_resource_path(os.path.join("static", acgn_filename))
                if not os.path.exists(config_path):
                    print(f"[VisualMapper] Warning: ACGN mappings file not found at {config_path}.")
                    return
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "mappings" in data:
                        self.mappings.update(data["mappings"])
                print(f"[VisualMapper] Loaded ACGN mappings from {config_path}")
            except Exception as e:
                print(f"[VisualMapper] Error loading ACGN mappings: {e}")

    def _load_styles_file(self, filename: str):
        """加载风格映射文件（只取styles字段）"""
        try:
            config_path = self._get_resource_path(os.path.join("static", filename))
            if not os.path.exists(config_path):
                print(
                    f"[VisualMapper] Warning: Styles file not found at {config_path}, using defaults."
                )
                return
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "styles" in data:
                    self.styles.update(data["styles"])
            print(f"[VisualMapper] Loaded styles from {config_path}")
        except Exception as e:
            print(f"[VisualMapper] Error loading styles: {e}, using defaults.")

    def _get_resource_path(self, relative_path: str) -> str:
        """获取资源绝对路径，兼容 PyInstaller"""
        if getattr(sys, "frozen", False):
            # PyInstaller 打包后的临时目录
            base_path = sys._MEIPASS
        else:
            # 开发环境：定位到项目根目录 (假设当前在 app/core/，根目录在 ../../)
            current_file = os.path.abspath(__file__)
            app_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            base_path = app_dir

        return os.path.join(base_path, relative_path)

    def map_keywords(self, keywords: List[str]) -> List[str]:
        """
        将中文关键词列表映射为英文提示词标签
        """
        visual_tags: List[str] = []
        seen_tags: Set[str] = set()  # 用于去重

        for kw in keywords:
            if not kw:
                continue

            mapped_tag = None

            # 1. 精确匹配
            if kw in self.mappings:
                mapped_tag = self.mappings[kw]

            # 2. 模糊匹配 (如果精确匹配失败)
            if not mapped_tag:
                for key, val in self.mappings.items():
                    if key in kw:  # 例如 "做家务" 匹配 "家务"
                        mapped_tag = val
                        break

            # 3. 添加到结果
            if mapped_tag:
                # 处理逗号分隔的多个tag
                tags = [t.strip() for t in mapped_tag.split(",")]
                for tag in tags:
                    if tag not in seen_tags:
                        visual_tags.append(tag)
                        seen_tags.add(tag)

        return visual_tags

    def get_style_tags(self, style_name: str) -> str:
        """获取风格提示词，并在需要时动态加载ACGN映射"""
        # 特殊处理“日系动漫”风格，动态加载acgn映射
        if style_name == "日系动漫":
            self.load_acgn_mappings()
        # 如果找不到指定风格，默认返回第一个风格或空字符串
        return self.styles.get(style_name, self.styles.get("清新简洁", ""))


# 单例测试
if __name__ == "__main__":
    mapper = VisualMapper()
    test_keywords = ["男方", "巨婴", "不做", "家务", "补偿金"]
    print("Test Mappings:", mapper.map_keywords(test_keywords))
    print("Test Style:", mapper.get_style_tags("黑白线稿"))
