"""品类数据层 — 混合模式数据源
=====================================
支持任意品类分析的统一数据入口：

1. 预置演示数据：此前真实爬取自 Amazon.com 的品类数据（无 API Key 也可用）
2. Rainforest API：配置 API Key 后，可实时分析任意亚马逊品类

优先级：预置品类命中 > Rainforest API 实时抓取 > 返回引导提示
"""
import re
from typing import Dict, List, Optional

import config
from services.imported_data import IMPORTED_PRODUCTS_LIST as SEX_TOY_PRODUCTS


# ============================================================
# 预置品类注册表
# 新增预置品类：用 amazon_scraper.py 爬取后，把数据导入
# services/imported_data.py，再在此注册即可。
# ============================================================
_CATEGORY_REGISTRY: List[Dict] = [
    {
        "key": "sex_toys",
        "name": "女性情趣用品（Clitoral Vibrators）",
        "aliases": [
            "vibrator", "sex toy", "sex toys", "clitoral", "satisfyer",
            "womanizer", "adult toy", "adult toys", "情趣", "振动棒", "按摩器",
        ],
        "products": SEX_TOY_PRODUCTS,
        "engine": "tuned",  # 该品类使用深度调优的分析引擎
    },
]


# ============================================================
# 最近一次分析的产品缓存
# 用于 /api/review-analysis/{asin} 支持任意品类（含 API 实时抓取的产品）
# ============================================================
_PRODUCT_CACHE: Dict[str, Dict] = {}


def cache_products(products: List[Dict]) -> None:
    """缓存产品，供评论分析接口按 ASIN 检索"""
    for p in products:
        if p.get("asin"):
            _PRODUCT_CACHE[p["asin"]] = p


def get_product_from_cache(asin: str) -> Optional[Dict]:
    return _PRODUCT_CACHE.get(asin)


def _normalize(keyword: str) -> str:
    """统一小写并去除非字母数字（保留中文）"""
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", (keyword or "").lower()).strip()


def match_demo_category(keyword: str) -> Optional[Dict]:
    """在预置品类注册表中模糊匹配关键词"""
    nk = _normalize(keyword)
    if not nk:
        return None
    for cat in _CATEGORY_REGISTRY:
        for alias in cat["aliases"]:
            a = _normalize(alias)
            if not a:
                continue
            # 包含匹配
            if a in nk or nk in a:
                return cat
            # 前缀匹配（至少3个字符，避免误匹配）
            if len(a) >= 3 and len(nk) >= 3 and a[:3] == nk[:3]:
                return cat
    return None


def _fetch_via_http(keyword: str, max_products: int) -> Dict:
    """通过 Amazon 搜索页 HTTP 直抓任意品类（免费，主要数据源）

    抓取搜索列表后，对头部产品补充详情卖点（bullet points）与用户评论，
    用于支撑「用户评价深度分析」与更深入的用户需求挖掘。
    """
    from services.amazon_http_scraper import scrape_amazon_enriched
    products = scrape_amazon_enriched(
        keyword,
        max_pages=3,
        max_products=min(max_products or 28, 28),
        detail_limit=12,
        review_limit=10,
    )
    if not products:
        return {"error": f"Amazon 实时抓取「{keyword}」未返回有效产品，请稍后重试或更换关键词"}
    cache_products(products)
    return {
        "status": "ok",
        "source": "http",
        "category": keyword,
        "category_en": keyword,
        "engine": "generic",
        "products": products,
        "note": "Amazon.com 实时抓取数据（含详情卖点与用户评论）",
    }


def _fetch_via_rainforest(keyword: str, max_products: int, max_reviews: int) -> Dict:
    """通过 Rainforest API 实时抓取任意品类（搜索 + 详情 + 评论）"""
    from services.amazon_service import AmazonService
    svc = AmazonService()

    products = svc.search_products(keyword, max_results=min(max_products, 50))
    if not products:
        return {"error": f"Rainforest API 未返回「{keyword}」的搜索结果，请尝试其他关键词"}

    # 详情 + 评论抓取限量执行（控制 API 消耗，默认前 12 个）
    detail_limit = min(max_products or 28, 12)
    enriched = []
    for p in products[:detail_limit]:
        detail = svc.get_product_detail(p["asin"]) or p
        detail.setdefault("features", [])
        detail.setdefault("bullet_points", [])
        detail.setdefault("subcategory", "")
        # 抓评论（评论分析需要）
        try:
            rev = svc.get_product_reviews(p["asin"], max_reviews=max_reviews)
            detail["reviews"] = rev.get("reviews", []) or []
        except Exception:
            detail["reviews"] = []
        enriched.append(detail)

    if not enriched:
        return {"error": f"Rainforest API 抓取「{keyword}」失败，请稍后重试"}

    cache_products(enriched)
    return {
        "status": "ok",
        "source": "api",
        "category": keyword,
        "category_en": keyword,
        "engine": "generic",
        "products": enriched,
        "note": "Rainforest API 实时数据",
    }


def get_data_for_keyword(keyword: str, max_products: int = 28,
                         max_reviews: int = 50) -> Dict:
    """混合数据获取：任意品类关键词 → 产品数据

    返回：
      {"status": "ok", "source": "demo"|"api", "category": 品类名,
       "category_en": 关键词, "engine": "tuned"|"generic",
       "products": [...], "note": 数据来源说明}
      或 {"error": 提示信息}
    """
    keyword = (keyword or "").strip()
    if not keyword:
        return {"error": "请输入品类关键词，例如：yoga mat、water bottle、headphone"}

    # 1) 预置演示数据命中
    cat = match_demo_category(keyword)
    if cat:
        products = cat["products"]
        if max_products and max_products > 0:
            products = products[:max_products]
        cache_products(products)
        return {
            "status": "ok",
            "source": "demo",
            "category": cat["name"],
            "category_en": keyword,
            "engine": cat.get("engine", "generic"),
            "products": products,
            "note": "演示数据（真实爬取自 Amazon.com）",
        }

    # 2) Amazon HTTP 实时直抓（任意品类，免费）
    http_result = _fetch_via_http(keyword, max_products)
    if "error" not in http_result:
        return http_result

    # 3) Rainforest API 实时抓取（配置了 Key 时的兜底）
    if config.RAINFOREST_API_KEY:
        return _fetch_via_rainforest(keyword, max_products, max_reviews)

    # 4) 无数据源可用
    return http_result
