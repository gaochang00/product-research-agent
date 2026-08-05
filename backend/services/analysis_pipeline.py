"""分析编排器 - 串联数据采集 → AI分析 → 评分 → 报告生成"""
import json
import importlib
from datetime import datetime
from typing import Dict, Any, List

from services.amazon_service import AmazonService
from services.llm_service import LLMService
from services.scoring_engine import ScoringEngine


class AnalysisPipeline:
    """分析编排器"""

    def __init__(self):
        self.amazon = AmazonService()
        self.llm = LLMService()
        self.scoring = ScoringEngine()

    def run_full_analysis(self, keyword: str, max_products: int = 8, max_reviews: int = 50) -> Dict[str, Any]:
        """运行完整的分析流程"""
        # 1. 搜索产品
        products = self.amazon.search_products(keyword, max_products)

        # 2. 逐个产品分析
        competitor_analyses = []
        all_reviews_flat = []

        for i, product in enumerate(products):
            print(f"[分析进度] 正在分析产品 {i+1}/{len(products)}: {product['title'][:30]}...", flush=True)

            # 获取评论
            reviews_data = self.amazon.get_product_reviews(product["asin"], max_reviews)
            reviews = reviews_data.get("reviews", [])
            all_reviews_flat.extend(reviews)

            # 使用AI分析评论
            analysis = self.llm.analyze_reviews(product["title"], reviews)

            # 计算综合评分
            overall_score = self.scoring.calculate_overall_score(
                analysis.get("dimension_scores", [])
            )

            competitor_analyses.append({
                "asin": product["asin"],
                "title": product["title"],
                "brand": product.get("brand", ""),
                "price": product.get("price", 0),
                "rating": product.get("rating", 0),
                "review_count": product.get("review_count", 0),
                "main_image": product.get("main_image", ""),
                "product_url": product.get("product_url", ""),
                "dimension_scores": analysis.get("dimension_scores", []),
                "overall_score": overall_score,
                "pros": analysis.get("pros", []),
                "cons": analysis.get("cons", []),
                "target_users": analysis.get("target_users", []),
                "usage_scenarios": analysis.get("usage_scenarios", [])
            })

        # 3. 提取用户需求并计算权重
        raw_needs = self.llm.extract_user_needs(all_reviews_flat, products)

        # 计算每个需求的权重分
        for need in raw_needs:
            need["weight_score"] = self.scoring.calculate_need_weight(need)

        # 按权重排序
        sorted_needs = self.scoring.sort_needs_by_weight(raw_needs)

        # 4. 识别机会点
        opportunities = self.scoring.identify_opportunities(competitor_analyses, sorted_needs)

        # 5. 品类平均分
        category_avg = self.scoring.calculate_category_averages(competitor_analyses)

        # 6. 维度重要性
        dim_importance = self.scoring.calculate_dimension_importance(sorted_needs)

        # 7. 生成设计方向建议
        design_data = {
            "competitors": [{"title": c["title"], "score": c["overall_score"], "price": c["price"]} for c in competitor_analyses],
            "top_needs": [{"desc": n.get("need_description", ""), "weight": n.get("weight_score", 0)} for n in sorted_needs[:3]],
            "opportunities": opportunities[:3]
        }
        design_direction = self.llm.generate_design_direction(design_data)

        # 8. 组装最终报告
        report = {
            "category": "女性情趣用品",
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "analyzed_products": competitor_analyses,
            "user_needs": sorted_needs,
            "top_needs": sorted_needs[:5],
            "opportunity_points": opportunities,
            "design_direction": design_direction.get("design_direction", ""),
            "key_differentiators": design_direction.get("key_differentiators", []),
            "cmf_trends": design_direction.get("cmf_trends", ""),
            "target_price_range": design_direction.get("target_price_range", ""),
            "category_average_scores": category_avg,
            "dimension_importance": dim_importance
        }

        return report

    def get_demo_analysis(self) -> Dict[str, Any]:
        """加载预计算的分析结果（用于快速演示）"""
        import services.demo_analysis_results as dar
        importlib.reload(dar)
        return dar.DEMO_ANALYSIS_RESULT
