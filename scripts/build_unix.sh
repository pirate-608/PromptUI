#!/bin/bash

# ==========================================
# 初始化路径
# ==========================================
cd "$(dirname "$0")/.." || exit
PROJECT_ROOT=$(pwd)

echo "[INFO] Project Root: $PROJECT_ROOT"
echo ""

# ==========================================
# 1. 开发环境检查
# ==========================================
echo "[1/5] Checking Development Environment..."

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found."
    exit 1
fi
if ! command -v cmake &> /dev/null; then
    echo "[ERROR] CMake not found."
    exit 1
fi
if ! command -v gcc &> /dev/null; then
    echo "[ERROR] GCC not found."
    exit 1
fi
echo "[PASS] Environment checks passed."
echo ""

# ==========================================
# 2. 环境变量文件 (.env) 自动生成
# ==========================================
echo "[2/5] Checking configuration (.env)..."

if [ ! -f ".env" ]; then
    echo "[WARN] .env not found. Starting interactive setup..."
    echo ""
    
    # --- 修改开始：询问是否配置云端模型 ---
    read -p "Do you want to configure a default cloud LLM provider? (y/n, default: n): " CONFIGURE_LLM
    
    if [[ "$CONFIGURE_LLM" == "y" || "$CONFIGURE_LLM" == "Y" ]]; then
        read -p "Enter LLM_API_BASE (Default: https://api.deepseek.com/v1): " API_BASE
        API_BASE=${API_BASE:-https://api.deepseek.com/v1}
        
        read -p "Enter LLM_API_KEY: " API_KEY
        
        read -p "Enter LLM_MODEL (Default: deepseek-chat): " MODEL
        MODEL=${MODEL:-deepseek-chat}
    fi
    # --- 修改结束 ---
    
    # 开始写入文件
    echo "# System" > .env
    echo "HOST=127.0.0.1" >> .env
    echo "PORT=8000" >> .env
    echo "LLM_TIMEOUT=60" >> .env
    echo "" >> .env
    
    if [[ "$CONFIGURE_LLM" == "y" || "$CONFIGURE_LLM" == "Y" ]]; then
        echo "# LLM Configuration" >> .env
        echo "LLM_API_BASE=$API_BASE" >> .env
        echo "LLM_API_KEY=$API_KEY" >> .env
        echo "LLM_MODEL=$MODEL" >> .env
    else
        echo "# LLM Configuration (Default: Ollama - Settings commented out)" >> .env
        echo "# LLM_API_BASE=http://localhost:11434/v1" >> .env
        echo "# LLM_API_KEY=ollama" >> .env
        echo "# LLM_MODEL=llama3" >> .env
    fi
    
    echo "[PASS] .env created successfully."
else
    echo "[PASS] .env exists. Skipping generation."
fi
echo ""

# ==========================================
# 3. 编译 C 语言模块
# ==========================================
echo "[3/5] Building C Modules..."

cd c_modules || exit
mkdir -p build
cd build || exit

echo "Configuring CMake..."
cmake ..

echo "Compiling..."
cmake --build . --config Release

cd "$PROJECT_ROOT" || exit
echo "[PASS] C Modules built successfully."
echo ""

# ==========================================
# 4. 安装 Python 依赖
# ==========================================
echo "[4/5] Installing Python Dependencies..."
python3 -m pip install -r requirements.txt
echo "[PASS] Dependencies installed."
echo ""

# ==========================================
# 5. PyInstaller 打包
# ==========================================
echo "[5/5] Packaging with PyInstaller..."

rm -rf dist build

pyinstaller build.spec --clean --noconfirm

echo "Copying .env to dist directory..."
cp .env dist/PromptUI/.env

echo ""
echo "=========================================="
echo "[SUCCESS] Build Complete!"
echo "Executable: $PROJECT_ROOT/dist/PromptUI/PromptUI"
echo "=========================================="