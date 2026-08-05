"""评分引擎 - 计算需求权重、综合评分等"""
from typing import List, Dict, Any
from models.report import ExtractedNeed, DimensionScore


class ScoringEngine:
    """评分引擎"""

    @staticmethod
    def calculate_need_weight(need: Dict) -> float:
        """计算单个需求的综合权重分 (1-10)"""
        freq = need.get("mention_frequency", 3)
        sentiment = need.get("sentiment_intensity", 3)
        impact = need.get("impact_scope", 3)
        competition = need.get("competition_coverage", 3)  # 反向: 越高越有机会
        value = need.get("business_value", 3)

        weight = (
            freq * 0.30 +
            sentiment * 0.25 +
            impact * 0.20 +
            competition * 0.15 +
            value * 0.10
        )
        return round(weight, 2)

    @staticmethod
    def calculate_overall_score(dimension_scores: List[Dict]) -> float:
        """计算产品综合评分"""
        if not dimension_scores:
            return 0
        total = sum(d.get("score", 0) for d in dimension_scores)
        return round(total / len(dimension_scores), 1)

    @staticmethod
    def sort_needs_by_weight(needs: List[Dict]) -> List[Dict]:
        """按权重从高到低排序需求"""
        return sorted(needs, key=lambda n: n.get("weight_score", 0), reverse=True)

    @staticmethod
    def calculate_dimension_importance(needs: List[ExtractedNeed]) -> dict:
        """计算各维度的重要性权重"""
        dimension_weights = {
            "功能需求": 0,
            "体验需求": 0,
            "审美需求": 0,
            "品质需求": 0,
            "价格需求": 0
        }
        for need in needs:
            need_type = need.get("need_type", "")
            weight = need.get("weight_score", 0)
            if need_type in dimension_weights:
                dimension_weights[need_type] += weight
        total = sum(dimension_weights.values()) or 1
        return {
            k: round(v / total, 3) for k, v in dimension_weights.items()
        }

    @staticmethod
    def calculate_category_averages(products: List[Dict]) -> dict:
        """计算品类各维度平均分"""
        dimensions = ["功能维度", "体验维度", "审美维度", "品质维度", "价格维度", "市场维度"]
        result = {}
        for dim in dimensions:
            scores = []
            for p in products:
                for ds in p.get("dimension_scores", []):
                    if ds.get("dimension_name") == dim:
                        scores.append(ds.get("score", 0))
            result[dim] = round(sum(scores) / len(scores), 1) if scores else 0
        return result

    @staticmethod
    def identify_opportunities(competitors: List[Dict], needs: List[Dict]) -> List[Dict]:
        """基于竞品弱点和用户需求识别机会点"""
        opportunities = []

        # 收集所有竞品的弱点
        all_weaknesses = []
        for c in competitors:
            for ds in c.get("dimension_scores", []):
                for w in ds.get("weaknesses", []):
                    all_weaknesses.append({
                        "weakness": w,
                        "dimension": ds.get("dimension_name", ""),
                        "product": c.get("title", "")[:20]
                    })

        # 统计高频弱点
        weakness_count = {}
        for w in all_weaknesses:
            key = w["weakness"][:15]
            weakness_count[key] = weakness_count.get(key, 0) + 1

        # 生成机会点
        for need in needs[:5]:
            opportunities.append({
                "title": f"解决「{need.get('need_description', '')[:20]}」的需求",
                "description": f"该需求权重评分{need.get('weight_score', 0)}，是用户重点关注领域",
                "potential_level": "高" if need.get("weight_score", 0) > 7 else "中",
                "related_dimension": need.get("need_type", "").replace("需求", "维度"),
                "estimated_impact": "高"
            })

        return opportunities
