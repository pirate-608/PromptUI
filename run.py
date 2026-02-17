import os
import sys
import subprocess
import shutil
import threading
import time
import webbrowser
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_and_install_ollama():
    """
    检测 Ollama 是否安装，未安装则尝试自动安装 (仅限 Windows)
    """
    print("🔍 Checking system dependencies...")
    
    if shutil.which("ollama"):
        print("✅ Ollama detected.")
        return

    print("⚠️ Ollama not found in PATH.")
    print("Ollama is recommended for local AI inference.")
    
    # 仅在非静默模式下询问（可根据需求调整交互逻辑）
    choice = input("👉 Do you want to download and install Ollama automatically? (y/n): ").strip().lower()
    
    if choice == 'y':
        print("🚀 Downloading and installing Ollama (via PowerShell)...")
        print("   (Please allow Administrator privileges if requested)")
        
        # 使用 Windows 官方推荐的 PowerShell 安装命令
        ps_command = "irm https://ollama.com/install.ps1 | iex"
        
        try:
            # shell=True 允许执行 PowerShell 命令
            subprocess.run(["powershell", "-Command", ps_command], check=True)
            print("✅ Ollama installed successfully! You may need to restart the app.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Installation failed: {e}")
            print("Please install manually from: https://ollama.com")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    else:
        print("⏩ Skipping Ollama installation.")

def open_browser(url):
    """延迟打开浏览器"""
    time.sleep(2)
    webbrowser.open(url)

def run_app():
    # 1. 启动前检查
    check_and_install_ollama()

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    url = f"http://{host}:{port}"

    # 2. 区分运行模式
    if getattr(sys, 'frozen', False):
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