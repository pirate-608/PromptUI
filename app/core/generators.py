import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from .visual_mapper import VisualMapper

# 加载环境变量
load_dotenv()


class PromptGenerator:
    def __init__(self, analyzer=None):
        self.analyzer = analyzer
        self.mapper = VisualMapper()
        # 加载默认配置 (从环境变量)
        self.default_config = {
            "api_base": os.getenv("LLM_API_BASE", "http://localhost:11434/v1"),
            "api_key": os.getenv("LLM_API_KEY", "ollama"),
            "model": os.getenv("LLM_MODEL", "llama3"),
            "timeout": int(os.getenv("LLM_TIMEOUT", "30")),
        }

    def generate(
        self,
        text: str,
        analysis: Dict[str, Any],
        mode: str = "auto",
        panels: int = 2,
        style: str = "清新简洁",
        sensitive_filter: bool = True,
        llm_config: Optional[Dict[str, str]] = None,
        language: Optional[str] = None,
    ) -> str:
        """
        :param llm_config: 前端传来的临时配置 {api_base, api_key, model}
        """
        # 合并配置：前端传来的 > 环境变量默认的
        current_config = self.default_config.copy()
        if llm_config:
            # 过滤掉空值，只更新有值的字段
            clean_config = {k: v for k, v in llm_config.items() if v}
            current_config.update(clean_config)

        # 语言集成：在 prompt 前加 Target language: ...
        lang_prefix = f"Target language: {language}\n" if language else ""
        if mode == "llm":
            return lang_prefix + self._generate_by_llm(
                text, style, panels, current_config
            )
        elif mode == "hybrid":
            return lang_prefix + self._generate_hybrid(
                text, analysis, style, panels, current_config
            )
        else:
            return lang_prefix + self._generate_by_algorithm(
                text, analysis, style, panels, sensitive_filter
            )

    def _generate_by_algorithm(
        self,
        text: str,
        analysis: Dict[str, Any],
        style: str,
        panels: int,
        sensitive_filter: bool,
    ) -> str:
        """算法模式：基于统计和关键词映射 (离线、快速、稳定)"""
        prompt_parts = []

        # A. 画风 & 布局
        prompt_parts.append(self.mapper.get_style_tags(style))
        prompt_parts.append(self._get_panel_tags(panels))

        # B. 内容映射 (取前15个高频词)
        top_words_data = analysis.get("top_words", [])
        keywords = [item.get("word", "") for item in top_words_data[:15]]
        visual_tags = self.mapper.map_keywords(keywords)

        if visual_tags:
            prompt_parts.extend(visual_tags)
        else:
            prompt_parts.append("daily life, storytelling")

        # C. 质量修饰
        prompt_parts.append("highres, best quality, 8k")

        # D. 敏感词处理
        if sensitive_filter and analysis.get("sensitive_words"):
            prompt_parts.append("safe for work")

        # 组装
        final_prompt = ", ".join(filter(None, prompt_parts))
        if panels > 1:
            final_prompt += " --ar 2:3"

        return final_prompt

    def _generate_by_llm(self, text: str, style: str, panels: int, config: Dict) -> str:
        """LLM 模式：完全由大模型理解并生成"""

        # 构造 System Prompt：教 AI 做 Stable Diffusion 的 Prompt Engineer
        system_prompt = (
            "You are an expert AI Art Prompt Generator. "
            "Your task is to convert the user's narrative text into a specific format for Stable Diffusion/Anime models.\n"
            "Rules:\n"
            "1. Output ONLY the English tags, separated by commas.\n"
            "2. No explanations, no markdown, no intro/outro.\n"
            "3. Structure: Style, Camera/Layout, Subject, Action, Environment, Quality.\n"
            "4. Include visual details (lighting, colors, expression).\n"
        )

        # 构造 User Prompt
        style_tags = self.mapper.get_style_tags(style)
        panel_tags = self._get_panel_tags(panels)

        user_prompt = (
            f'Input Text: "{text}"\n\n'
            f"Requirements:\n"
            f"- Art Style: {style} (Tags: {style_tags})\n"
            f"- Layout: {panels} Panels Comic (Tags: {panel_tags})\n"
            f"- Task: Extract characters, emotions, objects, and scenes from text and convert to tags.\n"
            f"\nOutput Tags:"
        )

        try:
            raw = self._call_llm_api(system_prompt, user_prompt, config)
            return self._extract_prompt(raw)
        except Exception as e:
            # 降级处理
            return (
                f"LLM Error: {str(e)} (Switched to Algorithm)\n"
                + self._generate_by_algorithm(text, {}, style, panels, True)
            )

    def _generate_hybrid(
        self, text: str, analysis: Dict[str, Any], style: str, panels: int, config: Dict
    ) -> str:
        """混合模式：算法提取关键词 + LLM 润色组织"""

        # 1. 先用算法提取关键词，作为“硬约束”喂给 LLM
        # 这样可以避免 LLM 遗漏文本中的关键实体
        top_words = [w["word"] for w in analysis.get("top_words", [])[:10]]
        keywords_str = ", ".join(top_words)

        style_tags = self.mapper.get_style_tags(style)
        panel_tags = self._get_panel_tags(panels)

        system_prompt = "You are a helper optimizing AI art prompts. Keep the key entities provided."

        user_prompt = (
            f'Source Text: "{text}"\n'
            f"Key Entities Detected: [{keywords_str}]\n"
            f"Target Style: {style_tags}\n"
            f"Layout: {panel_tags}\n\n"
            f"Task: Create a high-quality, comma-separated prompt string. "
            f"Ensure all Key Entities are represented visually. Add lighting and atmosphere details."
        )

        try:
            raw = self._call_llm_api(system_prompt, user_prompt, config)
            return self._extract_prompt(raw)
        except Exception as e:
            return f"Hybrid Error: {str(e)} (Fallback)\n" + self._generate_by_algorithm(
                text, analysis, style, panels, True
            )

    def _extract_prompt(self, raw: str) -> str:
        """
        提取 LLM 返回内容中的纯 prompt 字符串：
        - 优先提取英文引号内内容
        - 若无引号，提取第一段英文逗号串
        """
        import re

        # 提取英文引号内内容
        m = re.search(r'"([^"]{10,})"', raw)
        if m:
            return m.group(1).strip()
        # 提取第一段英文逗号串
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        for l in lines:
            if "," in l and len(l) > 20:
                return l
        # 否则返回原始内容
        return raw.strip()

    def _call_llm_api(
        self, system_content: str, user_content: str, config: Dict
    ) -> str:
        """使用传入的 config 发送请求"""
        url = f"{config['api_base'].rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}",
        }

        payload = {
            "model": config["model"],
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.7,
            "stream": False,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=config["timeout"]) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")

                body = response.read().decode("utf-8")
                result = json.loads(body)

                # 解析 OpenAI 格式响应
                content = result["choices"][0]["message"]["content"]
                return content.strip()

        except urllib.error.URLError as e:
            raise Exception(f"Connection failed: {e}")
        except KeyError:
            raise Exception("Invalid API response format")

    def _get_panel_tags(self, panels: int) -> str:
        """布局映射"""
        mapping = {
            1: "solo, single view, movie still",
            2: "2koma, 2 panels, split view, top and bottom",
            3: "3koma, 3 panels, comic page",
            4: "4koma, 4 panels, comic strip",
        }
        return mapping.get(panels, "comic page, multiple views")
