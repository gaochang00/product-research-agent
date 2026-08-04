"""Amazon 数据采集服务 — 支持 Rainforest API 和演示数据"""
import json
from typing import List, Dict, Optional
from datetime import datetime
import config
from services.demo_data import DEMO_PRODUCTS, DEMO_REVIEWS


class AmazonService:
    """Amazon 产品搜索与数据采集服务"""

    def __init__(self):
        self.api_key = config.RAINFOREST_API_KEY
        self.has_api = bool(self.api_key)

    def search_products(self, keyword: str, max_results: int = 10) -> List[Dict]:
        """搜索亚马逊产品"""
        if self.has_api:
            return self._search_via_api(keyword, max_results)
        else:
            return self._search_demo(keyword, max_results)

    def _search_demo(self, keyword: str, max_results: int) -> List[Dict]:
        """从演示数据中匹配产品"""
        keyword_lower = keyword.lower()
        results = []
        for p in DEMO_PRODUCTS:
            # 简单关键词匹配
            match_fields = [
                p["title"].lower(),
                p["brand"].lower(),
                p["category"].lower(),
                " ".join(p["features"]).lower(),
                p.get("description", "").lower()
            ]
            if keyword_lower in " ".join(match_fields):
                results.append(p)
                if len(results) >= max_results:
                    break

        # 如果匹配不到，返回前几个演示产品
        if not results:
            return DEMO_PRODUCTS[:min(max_results, len(DEMO_PRODUCTS))]

        return results

    def _search_via_api(self, keyword: str, max_results: int) -> List[Dict]:
        """通过Rainforest API搜索"""
        import httpx
        params = {
            "api_key": self.api_key,
            "type": "search",
            "amazon_domain": "amazon.com",
            "search_term": keyword,
            "max_results": max_results
        }
        try:
            resp = httpx.get(config.RAINFOREST_API_URL, params=params, timeout=30)
            data = resp.json()
            products = []
            for item in data.get("search_results", []):
                products.append({
                    "asin": item.get("asin", ""),
                    "title": item.get("title", ""),
                    "brand": item.get("brand", ""),
                    "price": item.get("price", {}).get("value", 0),
                    "currency": item.get("price", {}).get("currency", "USD"),
                    "rating": item.get("rating", 0),
                    "review_count": item.get("ratings_total", 0),
                    "main_image": item.get("image", ""),
                    "product_url": item.get("link", ""),
                    "category": item.get("category", ""),
                    "bsr_category": ""
                })
            return products
        except Exception as e:
            print(f"[Amazon API Error] {e}")
            return self._search_demo(keyword, max_results)

    def get_product_detail(self, asin: str) -> Optional[Dict]:
        """获取产品详细信息"""
        # 先查找演示数据
        for p in DEMO_PRODUCTS:
            if p["asin"] == asin:
                return p

        if self.has_api:
            import httpx
            params = {
                "api_key": self.api_key,
                "type": "product",
                "amazon_domain": "amazon.com",
                "asin": asin
            }
            try:
                resp = httpx.get(config.RAINFOREST_API_URL, params=params, timeout=30)
                data = resp.json().get("product", {})
                return {
                    "asin": data.get("asin", asin),
                    "title": data.get("title", ""),
                    "brand": data.get("brand", ""),
                    "price": data.get("buybox_winner", {}).get("price", {}).get("value", 0),
                    "currency": data.get("buybox_winner", {}).get("price", {}).get("currency", "USD"),
                    "rating": data.get("rating", 0),
                    "review_count": data.get("ratings_total", 0),
                    "main_image": data.get("main_image", ""),
                    "product_images": [img.get("link", "") for img in data.get("images", [])],
                    "description": data.get("description", ""),
                    "bullet_points": data.get("feature_bullets", []),
                    "features": data.get("feature_bullets", []),
                    "dimensions": "",
                    "color_options": []
                }
            except Exception:
                pass
        return None

    def get_product_reviews(self, asin: str, max_reviews: int = 50) -> Dict:
        """获取产品评论"""
        # 从演示数据返回
        reviews = DEMO_REVIEWS.get(asin, [])
        if reviews:
            title = ""
            for p in DEMO_PRODUCTS:
                if p["asin"] == asin:
                    title = p["title"]
                    break
            return {
                "asin": asin,
                "title": title,
                "reviews": reviews[:max_reviews],
                "total_reviews": len(reviews)
            }

        if self.has_api:
            import httpx
            params = {
                "api_key": self.api_key,
                "type": "reviews",
                "amazon_domain": "amazon.com",
                "asin": asin,
                "max_results": min(max_reviews, 100)
            }
            try:
                resp = httpx.get(config.RAINFOREST_API_URL, params=params, timeout=30)
                data = resp.json()
                reviews_data = []
                for r in data.get("reviews", []):
                    reviews_data.append({
                        "review_id": r.get("id", ""),
                        "title": r.get("title", ""),
                        "content": r.get("body", ""),
                        "rating": r.get("rating", 0),
                        "date": r.get("date", ""),
                        "verified_purchase": r.get("verified_purchase", False),
                        "variant": r.get("variant", ""),
                        "helpful_count": r.get("helpful_count", 0)
                    })
                return {
                    "asin": asin,
                    "title": "",
                    "reviews": reviews_data[:max_reviews],
                    "total_reviews": len(reviews_data)
                }
            except Exception:
                pass

        return {"asin": asin, "title": "", "reviews": [], "total_reviews": 0}
