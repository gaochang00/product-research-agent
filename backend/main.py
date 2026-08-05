"""产品调研智能体 - 后端入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import config
from routers.analysis import router as analysis_router

app = FastAPI(
    title="产品调研智能体 (Product Research Agent)",
    description="亚马逊竞品多维度分析工具 — 输入关键词，获取设计输入报告",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(analysis_router)


@app.get("/api/status")
async def api_status():
    return {
        "service": "产品调研智能体",
        "version": "1.0.0",
        "status": "running"
    }


# 托管前端静态文件（必须在API路由之后）
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True
    )
