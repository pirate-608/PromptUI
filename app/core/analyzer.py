# 文本分析器封装
import ctypes
import json
import os
import platform
import sys
from typing import Dict, Any

class TextAnalyzer:
    def __init__(self):
        self.lib = None
        self._load_library()

    def _load_library(self):
        system = platform.system()
        # 兼容 MinGW (libanalyzer.dll) 和 MSVC (analyzer.dll)
        lib_names = ["libanalyzer.dll", "analyzer.dll"] if system == "Windows" else ["libanalyzer.so"]
        
        # 获取路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        
        # 定义可能的搜索目录
        search_dirs = [
            # 1. VS Code 构建目录 (你当前的构建位置)
            os.path.join(project_root, "build"),
            # 2. C 模块内部构建目录
            os.path.join(project_root, "c_modules", "build"),
            # 3. 打包后的目录
            os.path.join(getattr(sys, '_MEIPASS', ''), "c_modules")
        ]

        self.lib = None
        for dir_path in search_dirs:
            for name in lib_names:
                full_path = os.path.join(dir_path, name)
                if os.path.exists(full_path):
                    try:
                        # 找到文件，尝试加载
                        self.lib = ctypes.CDLL(full_path)
                        print(f"[Analyzer] ✅ Successfully loaded C library: {full_path}")
                        break
                    except OSError as e:
                        print(f"[Analyzer] ⚠️ Found {full_path} but failed to load: {e}")
            if self.lib:
                break
        
        if self.lib:
            self.lib.analyze_text.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
            self.lib.analyze_text.restype = ctypes.c_int
        else:
            print(f"[Analyzer] ❌ Error: Could not find any of {lib_names} in search paths.")
            print(f"Searched: {search_dirs}")

    def is_loaded(self) -> bool:
        return self.lib is not None

    def analyze(self, text: str) -> Dict[str, Any]:
        """调用 C 核心进行分析"""
        if not self.lib:
            # 降级模式（如果C库没加载成功，返回一个模拟数据，防止崩坏）
            return {
                "total_chars": len(text),
                "richness": 0.5,
                "top_words": [{"word": x, "freq": 1} for x in text[:10]],
                "error": "C library not loaded"
            }

        # 准备缓冲区
        buf_size = 1024 * 1024  # 1MB buffer
        result_buffer = ctypes.create_string_buffer(buf_size)
        
        # 编码文本
        text_bytes = text.encode('utf-8')
        
        # 调用 C 函数
        ret = self.lib.analyze_text(text_bytes, result_buffer, buf_size)
        
        if ret == 0:
            try:
                json_str = result_buffer.value.decode('utf-8')
                return json.loads(json_str)
            except json.JSONDecodeError:
                return {"error": "JSON decode failed"}
        else:
            return {"error": "Analysis failed in C module"}