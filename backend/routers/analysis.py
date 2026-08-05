"""分析 API 路由 - 深度分析版"""
from fastapi import APIRouter, HTTPException, Query
from models.report import AnalysisRequest, AnalysisResponse
from services.deep_analysis_engine import DeepAnalysisEngine
from services.review_analyzer import ReviewAnalyzer, compare_products as cmp_func

router = APIRouter(prefix="/api", tags=["analysis"])
deep_engine = DeepAnalysisEngine()
review_analyzer = ReviewAnalyzer()


@router.post("/analyze")
async def analyze(request: AnalysisRequest):
    """执行完整的深度竞品分析（任意品类关键词）"""
    try:
        result = deep_engine.run_analysis_for_keyword(
            request.keyword,
            max_products=request.max_products,
            max_reviews_per_product=request.max_reviews_per_product,
        )
        if result.get("status") == "error":
            return {"status": "error", "message": result["message"], "report": None, "progress": 0}
        return {
            "status": "success",
            "message": result["message"],
            "report": result["report"],
            "progress": 100
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/review-analysis/{asin}")
async def get_review_analysis(asin: str):
    """获取单个产品的用户评价深度分析"""
    try:
        result = review_analyzer.analyze_product_reviews(asin)
        if "error" in result:
            # 尝试从扩展数据中查找
            from services.expanded_demo_data import EXPANDED_PRODUCTS
            for p in EXPANDED_PRODUCTS:
                if p["asin"] == asin:
                    return {
                        "status": "success",
                        "asin": asin,
                        "product_title": p["title"],
                        "product_url": p.get("product_url", f"https://www.amazon.com/dp/{asin}"),
                        "brand": p.get("brand", ""),
                        "price": p.get("price", 0),
                        "rating": p.get("rating", 0),
                        "review_stats": {"total_reviews": 0, "note": "该产品暂无详细评论数据"},
                        "liked_points": [],
                        "disliked_points": [],
                        "dimension_analysis": [],
                        "review_highlights": {"most_helpful_positive": [], "most_helpful_negative": [], "recent_reviews": []}
                    }
            return {"status": "error", "message": result["error"], "asin": asin}
        return {"status": "success", **result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "Product Research Agent v2.0"}


@router.post("/compare-reviews")
async def compare_reviews(request: dict):
    """多产品评论环比分析"""
    try:
        asin_list = request.get("asins", [])
        if not asin_list or len(asin_list) < 2:
            return {"status": "error", "message": "请提供至少2个ASIN"}
        result = cmp_func(asin_list)
        return {"status": "success", **result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
