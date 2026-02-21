# FastAPI主应用
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import uvicorn
import webbrowser
from threading import Thread
import time

from app.core.analyzer import TextAnalyzer
from app.core.generators import PromptGenerator
from app.api import styles as api_styles
from app.api import fetch_url as api_fetch_url


app = FastAPI(title="漫画提示词生成器")
app.include_router(api_styles.router)
app.include_router(api_fetch_url.router)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 初始化核心组件
analyzer = TextAnalyzer()
generator = PromptGenerator(analyzer)


# 请求/响应模型
class GenerateRequest(BaseModel):
    text: str
    mode: str = "auto"
    panels: int = 2
    style: str = "清新简洁"
    sensitive_filter: bool = True
    # 新增字段
    llm_api_base: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    language: Optional[str] = None  # 新增语言字段


class GenerateResponse(BaseModel):
    success: bool
    prompt: Optional[str] = None
    analysis: Optional[dict] = None
    error: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def root():
    """返回主页面"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_prompt(request: GenerateRequest):
    try:
        # 1. 文本分析
        analysis = analyzer.analyze(request.text)

        # 2. 构造配置对象
        llm_config = {
            "api_base": request.llm_api_base,
            "api_key": request.llm_api_key,
            "model": request.llm_model,
        }

        # 3. 生成提示词 (传入 llm_config)
        prompt = generator.generate(
            text=request.text,
            analysis=analysis,
            mode=request.mode,
            panels=request.panels,
            style=request.style,
            sensitive_filter=request.sensitive_filter,
            llm_config=llm_config,
            language=request.language,
        )

        return GenerateResponse(success=True, prompt=prompt, analysis=analysis)
    except Exception as e:
        return GenerateResponse(success=False, error=str(e))


@app.post("/api/analyze")
async def analyze_text(text: str = Form(...)):
    """仅分析文本API"""
    try:
        result = analyzer.analyze(text)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传文件API"""
    try:
        content = await file.read()
        text = content.decode("utf-8")
        return {"filename": file.filename, "content": text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件读取失败: {e}")


@app.get("/api/stats")
async def get_stats():
    """获取系统状态"""
    return {
        "analyzer_loaded": analyzer.is_loaded(),
        "modes": ["auto", "algorithm", "llm", "hybrid"],
        "version": "1.0.0",
    }


# 启动浏览器函数
def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")


if __name__ == "__main__":
    # 开发环境运行
    Thread(target=open_browser).start()
    uvicorn.run(app, host="127.0.0.1", port=8000)
