"""将前端静态文件与服务端整合"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import os

router = APIRouter()

# 获取前端HTML路径
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


@router.get("/app", response_class=HTMLResponse)
async def serve_app():
    """服务前端应用"""
    html_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>前端文件未找到</h1>"
