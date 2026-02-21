
# PowerShell 构建脚本（可选：去除 lib 前缀）
# 自动将 libanalyzer.dll 重命名为 analyzer.dll 以兼容主程序

param()

# 先获取脚本目录，避免变量为 null
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$envPath = Join-Path $ScriptDir '..' | Join-Path '.env'
# 自动读取 .env 并将 GCC_PATH 加入 PATH
if (Test-Path $envPath) {
    $lines = Get-Content $envPath | Where-Object { $_ -match '^GCC_PATH=' }
    foreach ($line in $lines) {
        $gccPath = $line -replace '^GCC_PATH=', ''
        if ($gccPath -and ($env:PATH -notlike "*$gccPath*")) {
            $env:PATH = "$gccPath;" + $env:PATH
            Write-Host "[INFO] GCC_PATH added to PATH: $gccPath" -ForegroundColor Cyan
        }
    }
}
$ErrorActionPreference = 'Stop'

# 获取项目根目录
$PROJECT_ROOT = Resolve-Path (Join-Path $ScriptDir '..')
Write-Host "[INFO] Project Root: $PROJECT_ROOT" -ForegroundColor Cyan

# ==========================================
# 1. 检查环境
# ==========================================
Write-Host "`n[1/5] Checking Environment..." -ForegroundColor Yellow
$missing = @()
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { $missing += 'Python' }
if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) { $missing += 'CMake' }
if ($missing.Count -gt 0) {
    Write-Host "[ERROR] Missing: $($missing -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "[PASS] Environment OK."

# ==========================================
# 2. .env 检查
# ==========================================
Write-Host "`n[2/5] Checking .env..." -ForegroundColor Yellow
$envPath = Join-Path $PROJECT_ROOT '.env'
if (-not (Test-Path $envPath)) {
    # 简单的默认 .env 生成逻辑
    $defaultEnv = @"
# System
HOST=127.0.0.1
PORT=8000
LLM_TIMEOUT=60
# LLM Configuration (Default: Ollama)
# LLM_API_BASE=http://localhost:11434/v1
# LLM_API_KEY=ollama
# LLM_MODEL=llama3
"@
    $defaultEnv | Set-Content -Path $envPath -Encoding UTF8
    Write-Host "[INFO] Generated default .env"
}
else {
    Write-Host "[PASS] .env exists."
}

# ==========================================
# 3. 构建 C 模块
# ==========================================
Write-Host "`n[3/5] Building C Modules..." -ForegroundColor Yellow

# VS Code 默认构建目录 promptui/build
$cmakeBuildDir = Join-Path $PROJECT_ROOT 'build'

if (-not (Test-Path $cmakeBuildDir)) {
    New-Item -ItemType Directory -Path $cmakeBuildDir | Out-Null
}

Push-Location $cmakeBuildDir

# 清理缓存，防止路径问题
if (Test-Path "CMakeCache.txt") { Remove-Item "CMakeCache.txt" -Force }


Write-Host "Configuring CMake (source: ../c_modules)..."
# 直接用 PowerShell 调用 cmake，避免 $LASTEXITCODE 异常
& cmake ../c_modules -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] CMake configure failed." -ForegroundColor Red; exit 1 }

Write-Host "Compiling..."
cmd /c "cmake --build . --config Release"
if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] Build failed." -ForegroundColor Red; exit 1 }

# ==========================================
# 检查并修正 DLL 文件命名（兼容性）
# ==========================================
$dllTarget = Join-Path $cmakeBuildDir 'analyzer.dll'
$dllSourceLib = Join-Path $cmakeBuildDir 'libanalyzer.dll'

if (Test-Path $dllTarget) {
    Write-Host "[PASS] Found $dllTarget" -ForegroundColor Green
}
elseif (Test-Path $dllSourceLib) {
    Write-Host "[INFO] Found libanalyzer.dll, renaming to analyzer.dll..." -ForegroundColor Cyan
    Copy-Item $dllSourceLib $dllTarget -Force
    if (Test-Path $dllTarget) {
        Write-Host "[PASS] Renamed successfully." -ForegroundColor Green
    }
    else {
        Write-Host "[ERROR] Rename failed." -ForegroundColor Red; exit 1
    }
}
else {
    Write-Host "[ERROR] 未找到 analyzer.dll 或 libanalyzer.dll，请检查 CMake 构建输出。" -ForegroundColor Red
    exit 1
}

Pop-Location # 返回原目录

# ==========================================
# 4. 安装依赖
# ==========================================
Write-Host "`n[4/5] Installing Dependencies..." -ForegroundColor Yellow
$venvPath = Join-Path $PROJECT_ROOT '.venv'
if (-not (Test-Path $venvPath)) {
    Write-Host "[INFO] Creating venv..."
    python -m venv $venvPath
}
$venvPython = Join-Path $venvPath 'Scripts\python.exe'
& $venvPython -m pip install -r (Join-Path $PROJECT_ROOT 'requirements.txt') | Out-Null

# ==========================================
# 5. PyInstaller 打包
# ==========================================
Write-Host "`n[5/5] Packaging..." -ForegroundColor Yellow
$distPath = Join-Path $PROJECT_ROOT 'dist'
# 使用独立目录作为 PyInstaller 的工作目录，防止误删 build 目录
$pyWorkDir = Join-Path $PROJECT_ROOT 'build_py_temp'

if (Test-Path $distPath) { Remove-Item -Recurse -Force $distPath -ErrorAction SilentlyContinue }
if (Test-Path $pyWorkDir) { Remove-Item -Recurse -Force $pyWorkDir -ErrorAction SilentlyContinue }

# 确认 build.spec 存在
if (-not (Test-Path "build.spec")) {
    Write-Host "[ERROR] build.spec not found in project root!" -ForegroundColor Red
    exit 1
}

Write-Host "Running PyInstaller..."
# 指定 --workpath 使用独立目录
& $venvPython -m PyInstaller build.spec --clean --noconfirm --workpath $pyWorkDir --distpath $distPath
if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] Packaging failed." -ForegroundColor Red; exit 1 }



# 拷贝 static 目录到 dist/PromptUI，确保 FastAPI 静态资源可用
$staticSrc = Join-Path $PROJECT_ROOT 'static'
$staticDst = Join-Path $distPath 'PromptUI\static'
if (Test-Path $staticSrc) {
    Copy-Item $staticSrc $staticDst -Recurse -Force
    Write-Host "[INFO] Copied static directory to dist/PromptUI/static" -ForegroundColor Cyan
}
else {
    Write-Host "[WARN] static directory not found, skipping copy." -ForegroundColor Yellow
}

# 拷贝 dict 目录到 dist/PromptUI，确保词典文件可用
$dictSrc = Join-Path $PROJECT_ROOT 'dict'
$dictDst = Join-Path $distPath 'PromptUI\dict'
if (Test-Path $dictSrc) {
    Copy-Item $dictSrc $dictDst -Recurse -Force
    Write-Host "[INFO] Copied dict directory to dist/PromptUI/dict" -ForegroundColor Cyan
}
else {
    Write-Host "[WARN] dict directory not found, skipping copy." -ForegroundColor Yellow
}

# 拷贝 .env
Copy-Item $envPath (Join-Path $distPath 'PromptUI\.env') -Force

# 构建成功
$exe = Join-Path $distPath 'PromptUI\PromptUI.exe'
Write-Host "`n[SUCCESS] Build Complete!" -ForegroundColor Green
Write-Host "Location: $exe"
Read-Host "Press Enter to exit..."