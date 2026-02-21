# -*- mode: python ; coding: utf-8 -*-

import sys
import os

# 动态收集实际存在的 analyzer 动态库
binaries = []
for lib in ['analyzer.dll', 'analyzer.so', 'libanalyzer.so', 'libanalyzer.dylib']:
    path = os.path.join('build', lib)
    if os.path.exists(path):
        binaries.append((path, 'c_modules'))

block_cipher = None

# --- 路径配置 ---
# 确保 PyInstaller 能找到你的源代码
PROJECT_DIR = os.getcwd()

PROJECT_DIR = os.getcwd()

a = Analysis(
    ['run.py'],  # 入口文件
    pathex=[PROJECT_DIR],
    binaries=binaries,
    datas=[
        # --- 静态资源映射 ---
        # 格式: (源路径, 目标文件夹)
        ('static', 'static'),       # 前端代码
        ('static/mappings', 'static/mappings'),  # 新增，递归包含所有mappings相关json
        ('app', 'app'),             # Python 后端代码 (防止 import 丢失)
        # --- C 模块配套词典 ---
        (os.path.join('c_modules', 'dict'), 'dict'),
        # --- 默认配置文件 ---
        # 如果你有 .env.example 或默认配置，可以在这里添加
    ],
    hiddenimports=[
        # --- 隐式导入 ---
        # Uvicorn 和 FastAPI 的依赖在静态分析时容易被忽略
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'engineio.async_drivers.asgi', # 某些 socket 库需要
        'python-dotenv',
        'app.main',                    # 强制包含我们的主应用
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PromptUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 设为 True 可以看到启动日志(特别是Ollama检查), 发布时可改为 False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/favicon/favicon.ico' if os.path.exists('static/favicon/favicon.ico') else None
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PromptUI',
)