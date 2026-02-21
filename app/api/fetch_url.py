from fastapi import APIRouter, Request
from pydantic import BaseModel, HttpUrl
from fastapi.responses import JSONResponse
import requests
from readability import Document
from bs4 import BeautifulSoup

router = APIRouter()


class FetchUrlRequest(BaseModel):
    url: HttpUrl


@router.post("/api/fetch_url")
def fetch_url(req: FetchUrlRequest):
    url = str(req.url)
    # 只允许 http/https
    if not (url.startswith("http://") or url.startswith("https://")):
        return {"success": False, "error": "仅支持 http/https 协议"}
    try:
        resp = requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (compatible; PromptUI/1.0)"},
        )
        if resp.status_code != 200:
            return {"success": False, "error": f"请求失败，状态码: {resp.status_code}"}

        # 自动检测并修正编码，优先支持中文网站
        html_bytes = resp.content
        # 1. 优先用 meta 标签检测编码
        meta_enc = None
        try:
            import re

            meta = re.search(rb'<meta[^>]+charset=["\']?([\w-]+)', html_bytes, re.I)
            if meta:
                meta_enc = meta.group(1).decode(errors="ignore").lower()
        except Exception:
            pass
        enc = meta_enc or resp.apparent_encoding or resp.encoding or "utf-8"
        if enc:
            enc_lc = enc.lower()
            if any(x in enc_lc for x in ["gbk", "gb2312", "gb18030"]):
                html = html_bytes.decode(enc, errors="ignore")
            else:
                try:
                    html = html_bytes.decode(enc, errors="ignore")
                except Exception:
                    html = html_bytes.decode("utf-8", errors="ignore")
        else:
            html = html_bytes.decode("utf-8", errors="ignore")
        # 限制最大长度，防止大页面拖垮
        if len(html) > 500_000:
            html = html[:500_000]
        # 优先用readability抽取正文
        try:
            doc = Document(html)
            title = doc.short_title() or ""
            content_html = doc.summary(html_partial=True)
            soup = BeautifulSoup(content_html, "html.parser")
            paragraphs = [
                p.get_text(strip=True)
                for p in soup.find_all(["p", "li"])
                if p.get_text(strip=True)
            ]
            text = title + "\n" + "\n".join(paragraphs)
            if not text.strip():
                raise ValueError("正文抽取为空")
        except Exception:
            # 降级为针对性提取：优先尝试常见论坛正文区
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "form"]):
                tag.decompose()
            # 针对 cc98 论坛等，优先提取主内容区
            candidates = [
                # cc98新版正文区
                {"name": "div", "attrs": {"class": "topic-content"}},
                {"name": "div", "attrs": {"class": "content"}},
                {"name": "div", "attrs": {"id": "main-content"}},
                {"name": "article"},
            ]
            text = ""
            for cand in candidates:
                found = soup.find(cand.get("name"), cand.get("attrs", {}))
                if found:
                    text = found.get_text(separator="\n", strip=True)
                    if text and len(text) > 20:
                        break
            if not text or len(text) < 10:
                # 兜底：全页面去标签纯文本
                text = soup.get_text(separator="\n", strip=True)
            text = text[:20000]  # 限制最大输出
        return {"success": True, "text": text}
    except Exception as e:
        return {"success": False, "error": str(e)}
