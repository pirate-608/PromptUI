import os
import sys
import subprocess
import shutil
import threading
import time
import webbrowser

from dotenv import load_dotenv


# --- 提前定义 pull_ollama_model ---
def pull_ollama_model():
    """
    自动拉取 Ollama 模型，模型名从 OLLAMA_MODEL 环境变量读取（无则默认 llama3）
    """
    model = os.getenv("OLLAMA_MODEL") or os.getenv("LLM_MODEL") or "llama3"
    if not shutil.which("ollama"):
        print("[Ollama] 跳过模型拉取，未检测到 ollama 可执行文件。")
        return
    print(f"[Ollama] 检查模型：{model}")
    # 检查模型是否已存在
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, check=True
        )
        if model in result.stdout:
            print(f"[Ollama] 已存在模型：{model}")
            return
    except Exception as e:
        print(f"[Ollama] 检查模型失败：{e}")
        # 继续尝试拉取
    print(f"[Ollama] 拉取模型：{model} ...")
    try:
        subprocess.run(["ollama", "pull", model], check=True)
        print(f"[Ollama] ✅ 模型拉取完成：{model}")
    except Exception as e:
        print(f"[Ollama] ❌ 模型拉取失败：{e}")


# --- 打包环境下自动切换工作目录到 _internal ---
if getattr(sys, "frozen", False):
    # sys._MEIPASS 是 PyInstaller 的临时解包目录
    base_dir = getattr(sys, "_MEIPASS", None)
    if base_dir:
        internal_dir = os.path.join(base_dir, "_internal")
        if os.path.isdir(internal_dir):
            os.chdir(internal_dir)
            print(f"[PromptUI] 切换工作目录到: {internal_dir}")

# 加载环境变量
load_dotenv()


def check_and_install_ollama():
    """
    检测 Ollama 是否安装，未安装则尝试自动安装 (仅限 Windows)
    """
    print("🔍 Checking system dependencies...")

    # 优先读取 .env 中 OLLAMA_PATH 并加入 PATH
    ollama_path = os.getenv("OLLAMA_PATH")
    if ollama_path:
        # 兼容多路径（分号分隔）
        paths = ollama_path.split(";")
        for p in paths:
            p = p.strip()
            if p and p not in os.environ.get("PATH", ""):
                os.environ["PATH"] = p + ";" + os.environ["PATH"]
        print(f"🔧 OLLAMA_PATH added to PATH: {ollama_path}")

    if shutil.which("ollama"):
        print("✅ Ollama detected.")
        return

    print("⚠️ Ollama not found in PATH.")
    print("Ollama is recommended for local AI inference.")

    # 仅在非静默模式下询问（可根据需求调整交互逻辑）
    choice = (
        input("👉 Do you want to download and install Ollama automatically? (y/n): ")
        .strip()
        .lower()
    )

    if choice == "y":
        platform = sys.platform
        if platform.startswith("win"):
            print("🚀 Downloading and installing Ollama (via PowerShell)...")
            print("   (Please allow Administrator privileges if requested)")
            ps_command = "irm https://ollama.com/install.ps1 | iex"
            try:
                subprocess.run(["powershell", "-Command", ps_command], check=True)
                print(
                    "✅ Ollama installed successfully! You may need to restart the app."
                )
            except subprocess.CalledProcessError as e:
                print(f"❌ Installation failed: {e}")
                print("Please install manually from: https://ollama.com")
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
        elif (
            platform == "darwin"
            or platform.startswith("linux")
            or platform.startswith("cygwin")
        ):
            print("🚀 Downloading and installing Ollama (via curl)...")
            curl_cmd = "curl -fsSL https://ollama.com/install.sh | sh"
            try:
                subprocess.run(curl_cmd, shell=True, check=True, executable="/bin/bash")
                print(
                    "✅ Ollama installed successfully! You may need to restart the app."
                )
            except subprocess.CalledProcessError as e:
                print(f"❌ Installation failed: {e}")
                print("Please install manually from: https://ollama.com")
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
        else:
            print(
                f"❌ Unsupported platform: {platform}. Please install Ollama manually from https://ollama.com"
            )
    else:
        print("⏩ Skipping Ollama installation.")


def open_browser(url):
    """延迟打开浏览器"""
    time.sleep(2)
    webbrowser.open(url)


def run_app():
    # 1. 启动前检查
    check_and_install_ollama()
    pull_ollama_model()

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    url = f"http://{host}:{port}"

    # 2. 区分运行模式
    if getattr(sys, "frozen", False):
        # --- 打包后的 EXE 模式 ---
        import uvicorn

        # 显式导入 app.main，防止 PyInstaller 找不到模块
        import app.main

        print(f"🚀 Starting PromptUI (Production Mode) at {url}")

        # 启动浏览器线程
        threading.Thread(target=open_browser, args=(url,), daemon=True).start()

        # 直接传递 app 对象而不是字符串，避免打包后的导入路径问题
        # log_level="error" 保持界面清爽
        uvicorn.run(app.main.app, host=host, port=port, log_level="info")

    else:
        # --- 开发模式 ---
        print(f"🛠️ Starting PromptUI (Dev Mode) at {url}")

        # 开发模式使用字符串导入，以支持 --reload 热重载
        # 注意：这里假设你已经在 promptui/ 根目录下运行
        # 启动浏览器（可选，开发时可能不想每次都弹窗，这里加上防止为了保持一致）
        threading.Thread(target=open_browser, args=(url,), daemon=True).start()

        # 使用 os.system 或 subprocess 调用 uvicorn CLI 以支持 reload
        # 必须确保当前目录是 promptui/
        os.system(f"uvicorn app.main:app --host {host} --port {port} --reload")


if __name__ == "__main__":
    try:
        run_app()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
