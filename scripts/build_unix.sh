#!/bin/bash
set -e

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 1. 检查环境
if ! command -v python3 &>/dev/null; then echo "[ERROR] Python3 未安装"; exit 1; fi
if ! command -v cmake &>/dev/null; then echo "[ERROR] CMake 未安装"; exit 1; fi

# 2. 检查 .env
ENV_PATH="$PROJECT_ROOT/.env"
if [ ! -f "$ENV_PATH" ]; then
cat > "$ENV_PATH" <<EOF
# System
HOST=127.0.0.1
PORT=8000
LLM_TIMEOUT=60
# LLM Configuration (Default: Ollama)
# LLM_API_BASE=http://localhost:11434/v1
# LLM_API_KEY=ollama
# LLM_MODEL=llama3
EOF
    echo "[INFO] Generated default .env"
else
    echo "[PASS] .env exists."
fi

# 3. 构建 C 模块
CMAKE_BUILD_DIR="$PROJECT_ROOT/build"
mkdir -p "$CMAKE_BUILD_DIR"
cd "$CMAKE_BUILD_DIR"
if [ -f "CMakeCache.txt" ]; then rm -f CMakeCache.txt; fi
cmake ../c_modules -DCMAKE_BUILD_TYPE=Release
make

DLL_TARGET="$CMAKE_BUILD_DIR/analyzer.so"
DLL_SOURCE_LIB="$CMAKE_BUILD_DIR/libanalyzer.so"
DLL_SOURCE_DYLIB="$CMAKE_BUILD_DIR/libanalyzer.dylib"
if [ -f "$DLL_TARGET" ]; then
    echo "[PASS] Found $DLL_TARGET"
elif [ -f "$DLL_SOURCE_LIB" ]; then
    echo "[PASS] Found $DLL_SOURCE_LIB"
elif [ -f "$DLL_SOURCE_DYLIB" ]; then
    echo "[PASS] Found $DLL_SOURCE_DYLIB"
else
    echo "[ERROR] 未找到 analyzer.so、libanalyzer.so 或 libanalyzer.dylib，请检查 CMake 构建输出。"; exit 1
fi
cd "$PROJECT_ROOT"

# 4. 安装依赖
VENV_PATH="$PROJECT_ROOT/.venv"
if [ ! -d "$VENV_PATH" ]; then
    echo "[INFO] Creating venv..."
    python3 -m venv "$VENV_PATH"
fi
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_ROOT/requirements.txt"

# 5. PyInstaller 打包
DIST_PATH="$PROJECT_ROOT/dist"
PY_WORK_DIR="$PROJECT_ROOT/build_py_temp"
rm -rf "$DIST_PATH" "$PY_WORK_DIR"
if [ ! -f "$PROJECT_ROOT/build.spec" ]; then echo "[ERROR] build.spec not found!"; exit 1; fi
pyinstaller "$PROJECT_ROOT/build.spec" --clean --noconfirm --workpath "$PY_WORK_DIR" --distpath "$DIST_PATH"

# 拷贝 static
STATIC_SRC="$PROJECT_ROOT/static"
STATIC_DST="$DIST_PATH/PromptUI/static"
if [ -d "$STATIC_SRC" ]; then
    cp -r "$STATIC_SRC" "$STATIC_DST"
    echo "[INFO] Copied static directory to dist/PromptUI/static"
else
    echo "[WARN] static directory not found, skipping copy."
fi

# 拷贝 dict
DICT_SRC="$PROJECT_ROOT/dict"
DICT_DST="$DIST_PATH/PromptUI/dict"
if [ -d "$DICT_SRC" ]; then
    cp -r "$DICT_SRC" "$DICT_DST"
    echo "[INFO] Copied dict directory to dist/PromptUI/dict"
else
    echo "[WARN] dict directory not found, skipping copy."
fi

# 拷贝 .env
cp "$ENV_PATH" "$DIST_PATH/PromptUI/.env"

# 完成
EXE="$DIST_PATH/PromptUI/PromptUI"
echo "[SUCCESS] Build Complete!"
echo "Location: $EXE"
