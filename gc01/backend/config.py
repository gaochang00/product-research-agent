"""应用配置"""
import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI / AI API 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

# Amazon API 配置 (Rainforest API)
RAINFOREST_API_KEY = os.getenv("RAINFOREST_API_KEY", "")
RAINFOREST_API_URL = "https://api.rainforestapi.com/request"

# 服务器配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
