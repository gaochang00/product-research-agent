"""评论分析器 — 对单个产品的评论进行深度多维分析"""
from typing import Dict, List, Any
import re
from collections import Counter
from services.imported_data import IMPORTED_PRODUCTS_LIST


# 构建 ASIN 到产品的映射
_ALL_PRODUCTS = {p["asin"]: p for p in IMPORTED_PRODUCTS_LIST if p.get("asin")}


def _parse_helpful(helpful_str) -> int:
    """解析亚马逊的 'X people found this helpful' 字符串为数字"""
    if isinstance(helpful_str, (int, float)):
        return int(helpful_str)
    if not helpful_str:
        return 0
    try:
        match = re.search(r'(\d+)', str(helpful_str))
        return int(match.group(1)) if match else 0
    except:
        return 0


class ReviewAnalyzer:
    """评论分析器"""

    def analyze_product_reviews(self, asin: str) -> Dict[str, Any]:
        """分析单个产品的评论"""
        # 从导入的真实数据中查找产品
        product = _ALL_PRODUCTS.get(asin)
        if not product:
            # 支持任意品类：查找最近一次分析缓存中的产品
            from services.category_data import get_product_from_cache
            product = get_product_from_cache(asin)
        if not product:
            return {"error": "未找到该产品", "asin": asin}

        # 获取评论数据（从爬取数据中提取）
        raw_reviews = product.get("reviews", [])
        
        # 标准化评论字段（爬虫数据使用 text 字段，分析器使用 content 字段）
        reviews = []
        for r in raw_reviews:
            reviews.append({
                "title": r.get("title", ""),
                "content": r.get("text", r.get("content", "")),
                "rating": r.get("rating", 0),
                "date": r.get("date", ""),
                "helpful_count": _parse_helpful(r.get("helpful", r.get("helpful_count", 0))),
                "verified": r.get("verified", r.get("verified_purchase", False)),
            })

        if not reviews:
            return {"error": "该产品暂无评论数据", "asin": asin}

        # 基础统计
        total = len(reviews)
        ratings = [r["rating"] for r in reviews]
        avg_rating = sum(ratings) / total if total else 0
        rating_dist = dict(Counter(ratings))

        # 好评/差评分类
        positive = [r for r in reviews if r["rating"] >= 4]
        negative = [r for r in reviews if r["rating"] <= 2]
        neutral = [r for r in reviews if 2 < r["rating"] < 4]

        # 提取用户喜欢的点（从好评中提取关键词）
        liked_points = self._extract_liked_points(positive)

        # 提取用户讨厌的点（从差评中提取关键词）
        disliked_points = self._extract_disliked_points(negative)

        # 多维评价分析
        dimension_analysis = self._analyze_dimensions(reviews, product)

        # 逐条评论分析
        review_highlights = self._get_review_highlights(reviews, product)

        return {
            "asin": asin,
            "product_title": product["title"],
            "product_url": product.get("product_url", f"https://www.amazon.com/dp/{asin}"),
            "brand": product.get("brand", ""),
            "price": product.get("price", 0),
            "rating": product.get("rating", 0),
            "reviews": reviews,  # 全部完整评论（含展开全文）
            "review_stats": {
                "total_reviews": total,
                "average_rating": round(avg_rating, 2),
                "rating_distribution": rating_dist,
                "positive_count": len(positive),
                "negative_count": len(negative),
                "neutral_count": len(neutral),
                "positive_ratio": round(len(positive) / total * 100, 1) if total else 0
            },
            "liked_points": liked_points,
            "disliked_points": disliked_points,
            "dimension_analysis": dimension_analysis,
            "review_highlights": review_highlights
        }

    def _extract_liked_points(self, positive_reviews: List[Dict]) -> List[Dict]:
        """从好评中提取用户喜欢的点"""
        points = []
        keywords = {
            "效果出色": ["效果", "有用", "有效", "好", "喜欢", "棒", "great", "amazing", "love"],
            "设计美观": ["设计", "美", "漂亮", "好看", "beautiful", "sleek", "stylish", "elegant"],
            "使用舒适": ["舒适", "舒服", "柔软", "comfortable", "soft", "gentle"],
            "操作简单": ["简单", "容易", "方便", "easy", "simple", "intuitive"],
            "静音": ["安静", "静音", "quiet", "silent", "discreet"],
            "品质好": ["质量", "品质", "做工", "quality", "premium", "solid"],
            "性价比高": ["价格", "值", "worth", "value", "affordable"],
            "包装好": ["包装", "隐私", "包装", "discreet", "packaging"],
            "续航好": ["续航", "电池", "电", "battery", "long"],
            "功能丰富": ["模式", "功能", "模式", "强度", "modes", "patterns"]
        }

        for keyword, terms in keywords.items():
            count = 0
            sample_reviews = []
            for r in positive_reviews:
                content = r.get("content", "").lower()
                title = r.get("title", "").lower()
                combined = content + " " + title
                if any(t in combined for t in terms):
                    count += 1
                    if len(sample_reviews) < 2:
                        sample_reviews.append(r.get("content", "")[:80])

            if count > 0:
                points.append({
                    "point": keyword,
                    "mention_count": count,
                    "ratio": round(count / len(positive_reviews) * 100, 1) if positive_reviews else 0,
                    "sample_reviews": sample_reviews
                })

        return sorted(points, key=lambda x: x["mention_count"], reverse=True)[:8]

    def _extract_disliked_points(self, negative_reviews: List[Dict]) -> List[Dict]:
        """从差评中提取用户讨厌的点"""
        points = []
        keywords = {
            "噪音大": ["噪音", "声音", "响", "noise", "loud", "buzzing", "sound"],
            "强度不适": ["太强", "太弱", "强度", "力度", "strong", "weak", "intense", "powerful"],
            "续航短": ["续航", "电池", "没电", "充电", "battery", "charge", "die"],
            "材质问题": ["材质", "硅胶", "吸附", "灰尘", "毛", "material", "silicone", "dust", "lint", "hair"],
            "操作不便": ["按键", "按钮", "操作", "复杂", "button", "hard to", "difficult", "confusing"],
            "设计缺陷": ["设计", "角度", "贴合", "fit", "design", "angle", "position"],
            "品控问题": ["坏了", "故障", "问题", "broken", "stopped", "defect", "malfunction"],
            "尺寸不适": ["尺寸", "大", "小", "size", "big", "small", "large"],
            "清洁困难": ["清洁", "清洗", "洗", "clean", "hard to clean"],
            "价格偏高": ["贵", "价格", "不值", "expensive", "overpriced", "not worth"]
        }

        for keyword, terms in keywords.items():
            count = 0
            sample_reviews = []
            for r in negative_reviews:
                content = r.get("content", "").lower()
                title = r.get("title", "").lower()
                combined = content + " " + title
                if any(t in combined for t in terms):
                    count += 1
                    if len(sample_reviews) < 2:
                        sample_reviews.append(r.get("content", "")[:80])

            if count > 0:
                points.append({
                    "point": keyword,
                    "mention_count": count,
                    "ratio": round(count / len(negative_reviews) * 100, 1) if negative_reviews else 0,
                    "sample_reviews": sample_reviews
                })

        return sorted(points, key=lambda x: x["mention_count"], reverse=True)[:8]

    def _analyze_dimensions(self, reviews: List[Dict], product: Dict) -> List[Dict]:
        """从评论中进行多维评价分析"""
        dimensions = {
            "功能体验": ["功能", "效果", "有用", "模式", "强度", "function", "effect", "useful", "mode", "strength"],
            "使用体验": ["舒适", "舒服", "手感", "握持", "角度", "comfortable", "feel", "ergonomic", "grip"],
            "噪音体验": ["噪音", "声音", "安静", "静音", "noise", "quiet", "silent", "buzzing"],
            "设计美感": ["设计", "美", "漂亮", "颜色", "外观", "design", "beautiful", "color", "look", "aesthetic"],
            "材质品质": ["材质", "硅胶", "做工", "质量", "material", "silicone", "quality", "premium", "build"],
            "续航充电": ["续航", "电池", "充电", "battery", "charge", "power"],
            "性价比": ["价格", "值", "性价比", "price", "value", "worth", "cost"]
        }

        results = []
        for dim_name, keywords in dimensions.items():
            # 计算积极/消极提及
            positive_mentions = 0
            negative_mentions = 0
            total_mentions = 0

            for r in reviews:
                content = r.get("content", "").lower()
                title = r.get("title", "").lower()
                combined = content + " " + title
                if any(k in combined for k in keywords):
                    total_mentions += 1
                    if r["rating"] >= 4:
                        positive_mentions += 1
                    elif r["rating"] <= 2:
                        negative_mentions += 1

            if total_mentions > 0:
                sentiment_score = round(
                    (positive_mentions - negative_mentions) / total_mentions * 5 + 5, 1
                )
                sentiment_score = max(1, min(10, sentiment_score))
                results.append({
                    "dimension": dim_name,
                    "mention_count": total_mentions,
                    "positive_mentions": positive_mentions,
                    "negative_mentions": negative_mentions,
                    "sentiment_score": sentiment_score,
                    "sentiment_label": "优秀" if sentiment_score >= 8 else "良好" if sentiment_score >= 6 else "一般" if sentiment_score >= 4 else "较差"
                })

        return sorted(results, key=lambda x: x["mention_count"], reverse=True)

    def _get_review_highlights(self, reviews: List[Dict], product: Dict) -> Dict:
        """获取代表性评论摘要"""
        # 最有帮助的好评
        helpful_positive = sorted(
            [r for r in reviews if r["rating"] >= 4],
            key=lambda r: r.get("helpful_count", 0),
            reverse=True
        )[:3]

        # 最有帮助的差评
        helpful_negative = sorted(
            [r for r in reviews if r["rating"] <= 2 or (r["rating"] <= 3 and r.get("helpful_count", 0) > 5)],
            key=lambda r: r.get("helpful_count", 0),
            reverse=True
        )[:3]

        # 最近评论
        recent = sorted(reviews, key=lambda r: r.get("date", ""), reverse=True)[:3]

        return {
            "most_helpful_positive": [
                {
                    "title": r.get("title", ""),
                    "content": r.get("content", "")[:200],
                    "rating": r.get("rating", 0),
                    "helpful_count": r.get("helpful_count", 0),
                    "date": r.get("date", "")
                }
                for r in helpful_positive
            ],
            "most_helpful_negative": [
                {
                    "title": r.get("title", ""),
                    "content": r.get("content", "")[:200],
                    "rating": r.get("rating", 0),
                    "helpful_count": r.get("helpful_count", 0),
                    "date": r.get("date", "")
                }
                for r in helpful_negative
            ],
            "recent_reviews": [
                {
                    "title": r.get("title", ""),
                    "content": r.get("content", "")[:150],
                    "rating": r.get("rating", 0),
                    "date": r.get("date", "")
                }
                for r in recent
            ]
        }

    def compare_products(self, asin_list: List[str]) -> Dict[str, Any]:
        """多产品评论环比分析"""
        results = []
        for asin in asin_list:
            analysis = self.analyze_product_reviews(asin)
            if "error" not in analysis:
                results.append(analysis)

        if not results:
            return {"error": "没有可比较的产品"}

        # 维度对比（按dimension名称聚合）
        dimension_names = set()
        for r in results:
            for dim in r.get("dimension_analysis", []):
                dimension_names.add(dim["dimension"])
        
        dimension_comparison = []
        for dim_name in sorted(dimension_names):
            entries = []
            for r in results:
                for dim in r.get("dimension_analysis", []):
                    if dim["dimension"] == dim_name:
                        entries.append({
                            "asin": r["asin"],
                            "product_title": r["product_title"][:30],
                            "sentiment_score": dim["sentiment_score"],
                            "sentiment_label": dim["sentiment_label"],
                            "mention_count": dim["mention_count"]
                        })
            if entries:
                avg_score = round(sum(e["sentiment_score"] for e in entries) / len(entries), 1)
                dimension_comparison.append({
                    "dimension": dim_name,
                    "average_score": avg_score,
                    "products": sorted(entries, key=lambda x: x["sentiment_score"], reverse=True)
                })

        # 总体评分对比
        rating_comparison = []
        for r in results:
            stats = r.get("review_stats", {})
            rating_comparison.append({
                "asin": r["asin"],
                "product_title": r["product_title"][:40],
                "product_url": r["product_url"],
                "average_rating": stats.get("average_rating", 0),
                "total_reviews": stats.get("total_reviews", 0),
                "positive_ratio": stats.get("positive_ratio", 0),
                "brand": r.get("brand", ""),
                "price": r.get("price", 0)
            })

        # 喜好/厌恶点对比
        liked_points_compare = {}
        for r in results:
            for p in r.get("liked_points", []):
                if p["point"] not in liked_points_compare:
                    liked_points_compare[p["point"]] = {}
                liked_points_compare[p["point"]][r["asin"]] = {
                    "ratio": p["ratio"],
                    "product_title": r["product_title"][:20]
                }

        disliked_points_compare = {}
        for r in results:
            for p in r.get("disliked_points", []):
                if p["point"] not in disliked_points_compare:
                    disliked_points_compare[p["point"]] = {}
                disliked_points_compare[p["point"]][r["asin"]] = {
                    "ratio": p["ratio"],
                    "product_title": r["product_title"][:20]
                }

        return {
            "status": "success",
            "product_count": len(results),
            "rating_comparison": sorted(rating_comparison, key=lambda x: x["average_rating"], reverse=True),
            "dimension_comparison": sorted(dimension_comparison, key=lambda x: x["average_score"], reverse=True),
            "liked_points_comparison": liked_points_compare,
            "disliked_points_comparison": disliked_points_compare
        }


# 全局单例
_analyzer = ReviewAnalyzer()


def analyze_product_reviews(asin: str) -> Dict[str, Any]:
    """便捷函数：分析单个产品评论"""
    return _analyzer.analyze_product_reviews(asin)


def compare_products(asin_list: List[str]) -> Dict[str, Any]:
    """便捷函数：多产品评论环比分析"""
    return _analyzer.compare_products(asin_list)