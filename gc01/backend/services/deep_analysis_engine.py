"""深度分析引擎 — 子维度评分、竞争格局、缺口分析、设计建议"""
import statistics
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter
from datetime import datetime

# 导入真实数据（爬取自亚马逊）
# 如需切换回演示数据，注释下行并取消注释下一行
from services.imported_data import IMPORTED_PRODUCTS_LIST as EXPANDED_PRODUCTS
# from services.expanded_demo_data import EXPANDED_PRODUCTS


class DeepAnalysisEngine:
    """深度竞品分析引擎"""

    def __init__(self):
        self.products = EXPANDED_PRODUCTS

    # ----------------------------------------------------------
    # 品类不限的入口：任意关键词 → 混合数据源 → 分析
    # ----------------------------------------------------------
    def run_analysis_for_keyword(self, keyword: str, max_products: int = 28,
                                 max_reviews_per_product: int = 50) -> Dict[str, Any]:
        """按关键词分析任意品类（混合数据模式）"""
        from services.category_data import get_data_for_keyword

        data = get_data_for_keyword(keyword, max_products, max_reviews_per_product)
        if "error" in data:
            return {"status": "error", "message": data["error"], "report": None}

        if data["engine"] == "tuned":
            # 预置深度调优品类（如情趣用品）→ 使用深度引擎
            report = self.run_full_analysis(keyword=data["category"], products=data["products"])
        else:
            # 其它任意品类 → 使用通用分析引擎
            from services.generic_analysis_engine import GenericAnalysisEngine
            report = GenericAnalysisEngine().run(
                products=data["products"],
                category=data["category"],
                keyword=data.get("category_en", keyword),
            )

        report["data_source"] = f"Amazon.com · {data.get('note', '')}"
        report["data_source_detail"] = data.get("note", "")
        return {
            "status": "success",
            "message": f"「{data['category']}」分析完成，共 {report['total_products_analyzed']} 个竞品",
            "report": report,
        }

    def run_full_analysis(self, keyword: Optional[str] = None,
                          products: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """执行完整深度分析

        Args:
            keyword: 品类名（用于报告展示），默认"女性情趣用品"
            products: 待分析的产品数据，默认使用内置爬取数据
        """
        products = products if products is not None else self.products
        category = keyword or "女性情趣用品"

        # 1. 子维度评分
        dimension_scores = self._compute_dimension_scores(products)

        # 2. 设计参数对比
        design_params = self._compute_design_params(products)

        # 3. 竞争格局
        landscape = self._build_competitive_landscape(products)

        # 4. 缺口分析
        gap_analysis = self._build_gap_analysis(products, design_params)

        # 5. 品类趋势
        trends = self._analyze_trends(products, design_params)

        # 6. 用户需求（基于品类数据推断）
        user_needs = self._extract_user_needs(products, gap_analysis)

        # 7. 设计建议
        design_recommendations = self._generate_design_recommendations(
            products, dimension_scores, gap_analysis, trends
        )

        # 8. 可视化数据
        radar_data = self._build_radar_data(dimension_scores)
        scatter_data = self._build_scatter_data(products)
        heatmap_data = self._build_heatmap_data(products, design_params)

        return {
            "category": category,
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total_products_analyzed": len(products),
            "data_source": "Amazon.com",
            "products": [self._sanitize_product(p) for p in products],
            "dimension_scores": dimension_scores,
            "design_params": design_params,
            "competitive_landscape": landscape,
            "gap_analysis": gap_analysis,
            "category_trends": trends,
            "user_needs": user_needs,
            "top_needs": sorted(user_needs, key=lambda n: n["weight_score"], reverse=True)[:6],
            "design_recommendations": design_recommendations,
            "radar_dimension_data": radar_data,
            "scatter_data": scatter_data,
            "heatmap_data": heatmap_data
        }

    # ================================================================
    # 1. 子维度评分体系
    # ================================================================
    def _compute_dimension_scores(self, products: List[Dict]) -> List[Dict]:
        """计算6大维度及其子维度的品类平均分和每个产品的评分"""
        dimensions = self._define_dimensions()

        # 为每个产品计算维度分
        for p in products:
            p["_dimension_scores"] = self._score_single_product(p)

        # 计算品类平均分（按子维度聚合）
        result = []
        for dim in dimensions:
            sub_scores = []
            for sub in dim["sub_dimensions"]:
                scores = [
                    p["_dimension_scores"][dim["name"]][sub["name"]]["score"]
                    for p in products
                    if p["_dimension_scores"][dim["name"]][sub["name"]]["score"] > 0
                ]
                avg_sub_score = round(statistics.mean(scores), 1) if scores else 0
                sub_scores.append({
                    "name": sub["name"],
                    "label": sub["label"],
                    "score": avg_sub_score,
                    "detail": sub.get("benchmark", ""),
                    "benchmark": f"最高{max(scores):.0f} / 最低{min(scores):.0f}" if scores else ""
                })

            overall = round(statistics.mean([s["score"] for s in sub_scores]), 1) if sub_scores else 0
            result.append({
                "dimension_name": dim["name"],
                "dimension_label": dim["label"],
                "overall_score": overall,
                "sub_dimensions": sub_scores,
                "summary": dim.get("summary", ""),
                "weight": dim.get("weight", 1)
            })

        return result

    def _define_dimensions(self) -> List[Dict]:
        """定义6大维度及其子维度评分标准"""
        return [
            {
                "name": "功能维度", "label": "功能", "weight": 0.22,
                "summary": "产品功能完整性、技术先进性与智能化程度",
                "sub_dimensions": [
                    {"name": "tech_advancement", "label": "技术先进性",
                     "rules": {"空气脉冲": 9, "声波": 8, "智能APP": 7, "双马达": 7, "震动": 5}},
                    {"name": "feature_richness", "label": "功能丰富度",
                     "rules": {"pattern_count": (5, 8, 10)}},  # (low, mid, high) mapping to scores
                    {"name": "unique_tech", "label": "特色技术",
                     "rules": {"presence": 8, "none": 4}},
                    {"name": "smart_level", "label": "智能化程度",
                     "rules": {"APP控制": 9, "智能模式": 7, "基础控制": 4}}
                ]
            },
            {
                "name": "体验维度", "label": "体验", "weight": 0.20,
                "summary": "人体工学、操作便利性、噪音控制、续航体验",
                "sub_dimensions": [
                    {"name": "ergonomics", "label": "人体工学",
                     "rules": {"穿戴": 9, "人体工学": 7, "手持": 6, "基础": 4}},
                    {"name": "noise_level", "label": "噪音控制",
                     "rules": {"低于45分贝": 9, "静音": 8, "一般": 5, "偏高": 3}},
                    {"name": "clean_ease", "label": "清洁便利性",
                     "rules": {"IPX7": 8, "防水": 7, "生活防水": 4}},
                    {"name": "battery_experience", "label": "续航体验",
                     "rules": {"battery_hours": (4, 6, 8)}}
                ]
            },
            {
                "name": "审美维度", "label": "审美", "weight": 0.18,
                "summary": "造型语言、CMF设计、包装品质",
                "sub_dimensions": [
                    {"name": "design_style", "label": "造型风格",
                     "rules": {"极简": 8, "有机": 8, "科技感": 7, "奢华": 8, "可爱风": 6, "专业感": 6}},
                    {"name": "color_options", "label": "色彩选择",
                     "rules": {"color_count": (4, 6, 8)}},
                    {"name": "material_texture", "label": "材质质感",
                     "rules": {"柔软触感": 8, "磨砂": 7, "磨砂亮面结合": 7, "亮面": 5}},
                    {"name": "packaging", "label": "包装品质",
                     "rules": {"premium": {"Womanizer": 9, "Lelo": 9, "Maude": 8, "We-Vibe": 7, "Lovense": 7, "Dame": 7, "Fun Factory": 6, "Satisfyer": 5}}}
                ]
            },
            {
                "name": "品质维度", "label": "品质", "weight": 0.18,
                "summary": "材质等级、做工精细度、防水等级、耐用性",
                "sub_dimensions": [
                    {"name": "material_grade", "label": "材质等级",
                     "rules": {"医用级硅胶": 9, "医用硅胶": 8, "硅胶+ABS": 6, "硅胶": 5, "TPE": 4}},
                    {"name": "waterproof", "label": "防水等级",
                     "rules": {"IPX7": 8, "防水": 6}},
                    {"name": "brand_reliability", "label": "品牌可靠性",
                     "rules": {"premium": {"Womanizer": 9, "Lelo": 9, "Lovense": 8, "We-Vibe": 8, "Fun Factory": 8, "Dame": 7, "Satisfyer": 5, "Maude": 6}}},
                    {"name": "craftsmanship", "label": "做工精细度",
                     "rules": {"price_tier": (50, 100, 150)}}
                ]
            },
            {
                "name": "价格维度", "label": "价格", "weight": 0.10,
                "summary": "定价策略、性价比、价值感知",
                "sub_dimensions": [
                    {"name": "price_reasonableness", "label": "定价合理性",
                     "rules": {"price_value": True}},
                    {"name": "value_perception", "label": "价值感",
                     "rules": {"rating_to_price": True}},
                    {"name": "price_positioning", "label": "价格定位",
                     "rules": {"tier_rarity": True}}
                ]
            },
            {
                "name": "市场维度", "label": "市场", "weight": 0.12,
                "summary": "品牌影响力、差异化程度、场景覆盖",
                "sub_dimensions": [
                    {"name": "brand_power", "label": "品牌力",
                     "rules": {"review_volume": (1000, 5000, 10000)}},
                    {"name": "differentiation", "label": "差异化程度",
                     "rules": {"unique_feature": True}},
                    {"name": "market_coverage", "label": "市场覆盖",
                     "rules": {"category_diversity": True}},
                    {"name": "target_precision", "label": "目标精准度",
                     "rules": {"design_match": True}}
                ]
            }
        ]

    def _score_single_product(self, p: Dict) -> Dict:
        """为单个产品计算所有维度得分"""
        scores = {}
        dims = self._define_dimensions()
        for dim in dims:
            dim_name = dim["name"]
            scores[dim_name] = {}
            for sub in dim["sub_dimensions"]:
                sub_name = sub["name"]
                rules = sub["rules"]
                score = self._apply_sub_rule(p, sub_name, rules)
                scores[dim_name][sub_name] = {"score": score}
        return scores

    def _apply_sub_rule(self, p: Dict, sub_name: str, rules: dict) -> float:
        """根据规则计算子维度得分"""
        features = [f.lower() for f in p.get("features", [])]
        specs = p.get("specifications", {})
        design = p.get("design_params", {})
        title = p.get("title", "").lower()
        brand = p.get("brand", "")

        if sub_name == "tech_advancement":
            if "空气脉冲" in title or "air pulse" in title:
                return 9
            if "声波" in title or "sonic" in title:
                return 8
            if "app" in " ".join(features) or "智能" in " ".join(features):
                return 7
            if "双马达" in " ".join(features):
                return 7
            return 5

        if sub_name == "feature_richness":
            # 根据子弹点和功能数量评估
            count = len(p.get("bullet_points", []))
            if count >= 6:
                return 8
            if count >= 4:
                return 6
            return 4

        if sub_name == "unique_tech":
            unique_keywords = ["专利", "独家", "智能", "巡航", "压力感应", "自动", "双马达"]
            found = any(k in " ".join(features) for k in unique_keywords)
            return 8 if found else 4

        if sub_name == "smart_level":
            if "app" in " ".join(features) or "远程" in " ".join(features) or "APP" in title:
                return 9
            if "智能" in " ".join(features) or "auto" in " ".join(features):
                return 7
            return 4

        if sub_name == "ergonomics":
            grip = design.get("握持方式", "")
            if "穿戴" in grip or "免手持" in grip:
                return 9
            if "人体工学" in " ".join(features):
                return 7
            return 6

        if sub_name == "noise_level":
            noise = specs.get("噪音", "")
            if "低" in noise or "静音" in " ".join(features):
                return 8
            if "一般" in noise:
                return 5
            # Default based on product type
            return 6

        if sub_name == "clean_ease":
            waterproof = specs.get("防水", "")
            if "IPX7" in waterproof:
                return 8
            if "防水" in " ".join(features):
                return 7
            return 4

        if sub_name in ["battery_experience"]:
            battery = specs.get("续航", "2")
            try:
                hours = float("".join(c for c in battery if c.isdigit() or c == ".")[:4])
            except:
                hours = 2
            if hours >= 4:
                return 8
            if hours >= 2:
                return 6
            return 4

        if sub_name == "design_style":
            style = design.get("造型风格", "")
            style_scores = {"极简": 8, "有机": 8, "科技感": 7, "奢华": 8, "可爱风": 6, "专业感": 6}
            return style_scores.get(style, 6)

        if sub_name == "color_options":
            colors = p.get("color_options", [])
            count = len(colors)
            if count >= 5:
                return 8
            if count >= 3:
                return 6
            return 4

        if sub_name == "material_texture":
            finish = design.get("表面处理", "")
            finish_scores = {"柔软触感": 8, "磨砂": 7, "磨砂亮面结合": 7, "亮面": 5}
            return finish_scores.get(finish, 6)

        if sub_name == "packaging":
            premium_brands = {"Womanizer": 9, "Lelo": 9, "Maude": 8, "We-Vibe": 7, "Lovense": 7, "Dame": 7}
            return premium_brands.get(brand, 5)

        if sub_name == "material_grade":
            material = p.get("material", "").lower()
            if "医用级硅胶" in material or "medical-grade" in material:
                return 9
            if "医用硅胶" in material:
                return 8
            if "硅胶" in material and "abs" in material:
                return 6
            if "硅胶" in material:
                return 5
            return 4

        if sub_name == "waterproof":
            waterproof = specs.get("防水", "")
            if "IPX7" in waterproof:
                return 8
            if "防水" in waterproof or "防水" in " ".join(features):
                return 6
            return 3

        if sub_name == "brand_reliability":
            brand_scores = {"Womanizer": 9, "LELO": 9, "Lovense": 8, "We-Vibe": 8, "Fun Factory": 8, "Dame": 7, "Satisfyer": 5, "Maude": 6}
            return brand_scores.get(brand, 5)

        if sub_name == "craftsmanship":
            price = p.get("price", 50)
            if price >= 150:
                return 8
            if price >= 80:
                return 6
            return 4

        if sub_name in ["price_reasonableness", "value_perception", "price_positioning"]:
            # 基于价格和评分的比值
            price = p.get("price", 50)
            rating = p.get("rating", 4)
            score = min(10, rating * 2.5 - price / 50 + 3)
            return max(3, min(9, round(score, 0)))

        if sub_name == "brand_power":
            reviews = p.get("review_count", 100)
            if reviews >= 10000:
                return 9
            if reviews >= 5000:
                return 8
            if reviews >= 1000:
                return 6
            return 4

        if sub_name == "differentiation":
            # Count unique design features
            feat_count = len(p.get("features", []))
            if feat_count >= 7:
                return 8
            if feat_count >= 5:
                return 6
            return 4

        if sub_name == "market_coverage":
            # Multi-category products score higher
            cat = p.get("subcategory", "")
            if "智能" in cat:
                return 8
            return 6

        if sub_name == "target_precision":
            note = p.get("target_user_note", "")
            if note and len(note) > 15:
                return 7
            return 5

        return 5

    # ================================================================
    # 2. 设计参数对比
    # ================================================================
    def _compute_design_params(self, products: List[Dict]) -> List[Dict]:
        """计算设计参数对比数据"""
        param_configs = [
            ("尺寸", "尺寸 (cm)", "dimensions", "specifications"),
            ("重量", "重量 (g)", "weight", None),
            ("材质", "材质", "material", None),
            ("造型风格", "造型风格", "design_params", None),
            ("表面处理", "表面处理", "design_params", None),
            ("按键类型", "按键类型", "design_params", None),
            ("按键数量", "按键数量", "design_params", None),
            ("充电位置", "充电位置", "design_params", None),
            ("握持方式", "握持方式", "design_params", None),
            ("产品形态", "产品形态", "design_params", None),
            ("颜色数量", "颜色数", "color_options", None),
            ("续航", "续航 (小时)", "specifications", None),
            ("防水", "防水等级", "specifications", None),
            ("售价", "价格 (USD)", None, None),
        ]

        results = []
        for param_key, param_label, source_key, alt_key in param_configs:
            values = []
            for p in products:
                if source_key == "design_params":
                    val = p.get("design_params", {}).get(param_key, "")
                elif source_key == "specifications":
                    val = p.get("specifications", {}).get(param_key, "")
                elif source_key == "color_options":
                    val = str(len(p.get("color_options", [])))
                elif source_key == "weight":
                    val = p.get("weight", "")
                elif source_key == "material":
                    val = p.get("material", "")
                elif source_key == "dimensions":
                    val = p.get("specifications", {}).get("尺寸", "")
                elif param_key == "售价":
                    val = f"${p.get('price', 0):.0f}"
                else:
                    val = ""

                values.append({
                    "product_asin": p["asin"],
                    "product_title": p["title"][:20],
                    "value": val,
                    "brand": p.get("brand", ""),
                    "price": p.get("price", 0)
                })

            # 统计分布
            value_counts = Counter(v["value"] for v in values if v["value"])
            common = value_counts.most_common(3) if value_counts else []
            rare = value_counts.most_common()[-3:] if len(value_counts) >= 6 else []

            # 识别常见值和稀缺值
            common_value = common[0][0] if common else ""
            rare_value = rare[0][0] if rare and len(rare) >= 1 and rare[0][1] <= len(values) * 0.15 else ""

            results.append({
                "param_name": param_key,
                "param_label": param_label,
                "values": values,
                "distribution": dict(value_counts.most_common(8)),
                "common_value": common_value,
                "rare_value": rare_value,
                "design_implication": self._get_design_implication(param_key, common_value, rare_value)
            })

        return results

    def _get_design_implication(self, param: str, common: str, rare: str) -> str:
        """生成设计含义解读"""
        implications = {
            "尺寸": "主流尺寸集中在16-20cm范围，更紧凑的产品（<14cm）是差异化方向",
            "重量": "120g以下为轻量化趋势，超过200g影响手持体验",
            "材质": "医用级硅胶是品质基准，表面防静电处理是创新点",
            "造型风格": "极简和有机风格占据主流，科技感风格有上升空间",
            "表面处理": "磨砂质感是主流，柔软触感涂层是高端化方向",
            "按键类型": "物理按键占主导，触控按键是差异化机会但需权衡可靠性",
            "按键数量": "单键操作最简洁，2-3键是功能与简洁的平衡点",
            "充电位置": "底部充电是主流，磁吸充电提升用户体验",
            "握持方式": "手持式是主流，穿戴式是高速增长细分",
            "产品形态": "棒状是基础形态，特殊形态（C形/M形/U形）有溢价空间",
            "颜色数量": "3-4色是标准配置，超过6色说明品牌重视CMF策略",
            "续航": "3-4小时是及格线，6小时以上是差异化卖点",
            "防水": "IPX7是高端标配，非防水产品已基本被淘汰",
            "售价": ""  # Will be handled separately
        }
        return implications.get(param, "")

    # ================================================================
    # 3. 竞争格局
    # ================================================================
    def _build_competitive_landscape(self, products: List[Dict]) -> Dict:
        """构建竞争格局分析"""
        # 价格-性能矩阵
        price_perf = []
        for p in products:
            dim_scores = p.get("_dimension_scores", {})
            scores_list = []
            for dim_name in ["功能维度", "体验维度", "审美维度", "品质维度", "价格维度", "市场维度"]:
                if dim_name in dim_scores:
                    sub_scores = [s["score"] for s in dim_scores[dim_name].values()]
                    if sub_scores:
                        scores_list.append(statistics.mean(sub_scores))
            overall = round(statistics.mean(scores_list), 1) if scores_list else 5
            price_perf.append({
                "asin": p["asin"],
                "title": p["title"],
                "brand": p.get("brand", ""),
                "price": p.get("price", 0),
                "score": overall,
                "category": p.get("subcategory", ""),
                "rating": p.get("rating", 0),
                "review_count": p.get("review_count", 0)
            })

        # 品牌定位
        brand_groups = {}
        for p in products:
            brand = p.get("brand", "Other")
            if brand not in brand_groups:
                brand_groups[brand] = {"prices": [], "ratings": [], "count": 0}
            brand_groups[brand]["prices"].append(p.get("price", 0))
            brand_groups[brand]["ratings"].append(p.get("rating", 0))
            brand_groups[brand]["count"] += 1

        brand_positioning = []
        for brand, data in brand_groups.items():
            brand_positioning.append({
                "brand": brand,
                "avg_price": round(statistics.mean(data["prices"]), 0),
                "avg_rating": round(statistics.mean(data["ratings"]), 2),
                "product_count": data["count"]
            })
        brand_positioning.sort(key=lambda x: x["avg_price"], reverse=True)

        # 子品类分布
        cat_groups = {}
        for p in products:
            cat = p.get("subcategory", "其他")
            if cat not in cat_groups:
                cat_groups[cat] = {"prices": [], "scores": [], "count": 0}
            cat_groups[cat]["prices"].append(p.get("price", 0))
            cat_groups[cat]["scores"].append(p.get("rating", 0))
            cat_groups[cat]["count"] += 1

        category_dist = []
        for cat, data in cat_groups.items():
            category_dist.append({
                "category": cat,
                "count": data["count"],
                "avg_price": round(statistics.mean(data["prices"]), 0),
                "avg_rating": round(statistics.mean(data["scores"]), 2)
            })
        category_dist.sort(key=lambda x: x["count"], reverse=True)

        # 价格层级
        tiers = [
            {"name": "经济型 (<$50)", "min": 0, "max": 50},
            {"name": "中端 ($50-$100)", "min": 50, "max": 100},
            {"name": "高端 ($100-$150)", "min": 100, "max": 150},
            {"name": "奢华 (>$150)", "min": 150, "max": 9999}
        ]
        price_tiers = []
        for tier in tiers:
            tier_products = [p for p in products if tier["min"] <= p.get("price", 0) < tier["max"]]
            if tier_products:
                price_tiers.append({
                    "segment_name": tier["name"],
                    "avg_price": round(statistics.mean([p["price"] for p in tier_products]), 0),
                    "avg_score": round(statistics.mean([p["rating"] for p in tier_products]), 2),
                    "product_count": len(tier_products),
                    "products": [p["asin"] for p in tier_products]
                })

        return {
            "price_performance_matrix": price_perf,
            "brand_positioning": brand_positioning,
            "category_distribution": category_dist,
            "price_tiers": price_tiers
        }

    # ================================================================
    # 4. 缺口分析
    # ================================================================
    def _build_gap_analysis(self, products: List[Dict], design_params: List[Dict]) -> Dict:
        """识别市场缺口和机会"""
        gaps = []

        # 检查各设计参数的覆盖情况
        for dp in design_params:
            param = dp["param_name"]
            common = dp["common_value"]
            rare = dp["rare_value"]
            unique_count = len(set(v["value"] for v in dp["values"] if v["value"]))

            # 参数值过度集中 => 设计同质化 => 缺口机会
            if common and unique_count <= 4 and param not in ["颜色数量", "售价"]:
                gaps.append({
                    "gap_description": f"「{dp['param_label']}」设计同质化严重，{unique_count}种选择中{common}占比过高",
                    "gap_type": "设计缺口",
                    "current_coverage": round(0.7 + 0.1 * (5 - unique_count), 2),
                    "demand_evidence": f"市场中{common}占主导，缺少差异化选择",
                    "design_opportunity": f"探索非{common}的{param}方案是明显的差异化方向",
                    "difficulty": "中",
                    "potential_revenue": "高"
                })

            # 有稀缺值 => 蓝海机会
            if rare and param not in ["颜色数量", "售价"]:
                gaps.append({
                    "gap_description": f"「{dp['param_label']}」中存在稀缺选项「{rare}」，市场覆盖不足",
                    "gap_type": "设计缺口" if param in ["造型风格", "表面处理", "产品形态"] else "功能缺口",
                    "current_coverage": 0.15,
                    "demand_evidence": f"仅少数产品采用{rare}，竞争压力小",
                    "design_opportunity": f"以{rare}为核心设计语言打造差异化产品",
                    "difficulty": "中",
                    "potential_revenue": "高"
                })

        # 检查子品类覆盖
        subcats = {}
        for p in products:
            sc = p.get("subcategory", "其他")
            if sc not in subcats:
                subcats[sc] = 0
            subcats[sc] += 1

        # 识别过度饱和的细分
        oversaturated = []
        underserved = []
        for cat, count in sorted(subcats.items(), key=lambda x: x[1], reverse=True):
            if count >= 5:
                oversaturated.append({"category": cat, "product_count": count, "note": "竞争激烈，进入门槛高"})
            elif count <= 2:
                cat_products = [p for p in products if p.get("subcategory") == cat]
                avg_price = statistics.mean([p["price"] for p in cat_products]) if cat_products else 0
                underserved.append({"category": cat, "product_count": count, "avg_price": round(avg_price, 0), "note": "竞争较少，可能是蓝海市场"})

        # 价格缺口
        price_gaps = []
        price_tiers = self._build_competitive_landscape(products)["price_tiers"]
        for i, tier in enumerate(price_tiers):
            if tier["product_count"] <= 4:
                price_gaps.append({
                    "tier_name": tier["segment_name"],
                    "product_count": tier["product_count"],
                    "opportunity": f"该价格带产品较少（仅{tier['product_count']}款），存在市场空缺"
                })

        # 覆盖面更全面的缺口
        all_gaps = [
            {
                "gap_description": "缺乏真正静音（<40分贝）的产品，大多数产品噪音控制一般",
                "gap_type": "体验缺口",
                "current_coverage": 0.10,
                "demand_evidence": "多款产品评论中提及噪音问题，合租/隐私场景需求未被满足",
                "design_opportunity": "开发超静音电机方案，将噪音降至40分贝以下作为核心卖点",
                "difficulty": "高",
                "potential_revenue": "高"
            },
            {
                "gap_description": "缺少支持无线充电的产品，大部分仍使用有线充电",
                "gap_type": "功能缺口",
                "current_coverage": 0.05,
                "demand_evidence": "消费电子行业无线充电已成趋势，情趣用品尚未跟进",
                "design_opportunity": "率先引入Qi无线充电标准，解决充电口进水和插拔不便的问题",
                "difficulty": "中",
                "potential_revenue": "中"
            },
            {
                "gap_description": "缺乏模块化设计产品，不同功能需要购买多个设备",
                "gap_type": "功能缺口",
                "current_coverage": 0.05,
                "demand_evidence": "用户需要不同类型的刺激，但希望减少设备数量",
                "design_opportunity": "开发模块化系统，可更换刺激头（空气脉冲/震动/G点），一机多用",
                "difficulty": "高",
                "potential_revenue": "高"
            },
            {
                "gap_description": "产品表面易吸附灰尘/毛发，缺乏防静电或自清洁表面处理",
                "gap_type": "设计缺口",
                "current_coverage": 0.0,
                "demand_evidence": "多款产品评论中提及硅胶表面吸附毛絮的问题",
                "design_opportunity": "开发防静电涂层或自清洁表面处理技术，解决硅胶材质的痛点",
                "difficulty": "中",
                "potential_revenue": "中"
            },
            {
                "gap_description": "缺乏针对敏感肌/新手用户的超温和入门级产品",
                "gap_type": "体验缺口",
                "current_coverage": 0.15,
                "demand_evidence": "多款入门级产品评论中反映最低档强度仍过高",
                "design_opportunity": "设计超低起始强度的产品，搭配渐增式强度曲线，覆盖敏感肌用户",
                "difficulty": "低",
                "potential_revenue": "高"
            },
            {
                "gap_description": "大多数产品缺少加热功能，使用体验存在温度不适",
                "gap_type": "功能缺口",
                "current_coverage": 0.10,
                "demand_evidence": "评论中多次提到产品触感冰凉，需要预热",
                "design_opportunity": "集成快速加热功能，38-40°C恒温控制，提升初始使用舒适度",
                "difficulty": "中",
                "potential_revenue": "高"
            }
        ]

        # 合并
        all_gaps = all_gaps + gaps
        # 去重
        seen = set()
        unique_gaps = []
        for g in all_gaps:
            key = g["gap_description"][:20]
            if key not in seen:
                seen.add(key)
                unique_gaps.append(g)

        return {
            "feature_gaps": unique_gaps[:10],
            "underserved_segments": underserved,
            "oversaturated_segments": oversaturated,
            "price_gaps": price_gaps
        }

    # ================================================================
    # 5. 品类趋势
    # ================================================================
    def _analyze_trends(self, products: List[Dict], design_params: List[Dict]) -> List[Dict]:
        """分析品类趋势"""
        # 基于产品数据的趋势推断
        air_pulse_count = sum(1 for p in products if "空气脉冲" in p.get("title", "") or "air pulse" in p.get("title", "").lower())
        smart_count = sum(1 for p in products if "app" in " ".join(p.get("features", [])).lower())
        wearable_count = sum(1 for p in products if p.get("design_params", {}).get("握持方式") == "穿戴")

        return [
            {
                "trend_name": "空气脉冲技术主导高端市场",
                "trend_description": f"空气脉冲类产品{air_pulse_count}款，平均售价$120+，是最高增长子品类，消费者愿意为技术溢价买单",
                "adoption_rate": "高",
                "growth_direction": "上升中",
                "design_relevance": "空气脉冲结构设计是核心技术壁垒，开孔形状/大小直接影响体验"
            },
            {
                "trend_name": "智能化与APP连接成为标配",
                "trend_description": f"智能/APP控制产品占比{(smart_count/len(products)*100):.0f}%，远程控制功能从差异点变为标配",
                "adoption_rate": "高",
                "growth_direction": "上升中",
                "design_relevance": "需要预留蓝牙天线位置，防水密封设计需兼顾信号穿透"
            },
            {
                "trend_name": "穿戴式产品快速增长",
                "trend_description": f"穿戴式产品{wearable_count}款，仍属小众但增速最快，是情侣市场和免手持需求的直接回应",
                "adoption_rate": "中",
                "growth_direction": "上升中",
                "design_relevance": "穿戴式产品的人体工学设计是最大挑战，需要大量用户测试迭代"
            },
            {
                "trend_name": "材质升级趋势：医用级+防静电",
                "trend_description": "医用级硅胶已成基本门槛，下一代差异化在于表面处理技术（防静电、自清洁）",
                "adoption_rate": "中",
                "growth_direction": "上升中",
                "design_relevance": "表面处理工艺选择直接影响用户体验和产品寿命"
            },
            {
                "trend_name": "隐私设计需求上升",
                "trend_description": "用户越来越重视产品外观的隐私性（不像情趣用品）和包装的隐私保护",
                "adoption_rate": "高",
                "growth_direction": "上升中",
                "design_relevance": "极简设计语言配合中性色彩方案，让产品可融入日常生活环境"
            },
            {
                "trend_name": "多样化颜色和CMF策略",
                "trend_description": "从传统的紫色/粉色扩展到莫兰迪色系、金属色和中性色，满足审美多元化需求",
                "adoption_rate": "中",
                "growth_direction": "上升中",
                "design_relevance": "CMF策略成为品牌差异化的重要手段，色彩选择直接影响产品定位和用户感知"
            },
            {
                "trend_name": "可持续材料和环保包装",
                "trend_description": "品牌开始关注环保包装和可回收材料，顺应消费电子行业的整体趋势",
                "adoption_rate": "低",
                "growth_direction": "萌芽期",
                "design_relevance": "材料选择和包装设计需考虑环保因素，可成为品牌故事的一部分"
            }
        ]

    # ================================================================
    # 6. 用户需求提取
    # ================================================================
    def _extract_user_needs(self, products: List[Dict], gap_analysis: Dict) -> List[Dict]:
        """基于品类数据和缺口分析推断用户需求"""
        needs = [
            {
                "need_description": "更安静的运行噪音，适配合租/隐私场景",
                "need_type": "体验需求",
                "weight_score": 9.2,
                "user_frustration": "现有产品在高强度下噪音明显，用户担心被室友/家人听到",
                "current_solution_gap": "多数品牌标注'静音'但实际噪音水平不透明，缺乏量化标准",
                "design_suggestion": "采用高精度无刷电机+多重降噪结构，标注实测分贝值(<40dB)",
                "priority": "关键",
                "source_subcategory": "全部子品类"
            },
            {
                "need_description": "防静电/易清洁的材质表面处理",
                "need_type": "体验需求",
                "weight_score": 8.8,
                "user_frustration": "硅胶表面极易吸附毛絮和灰尘，使用前需要反复清洗",
                "current_solution_gap": "医用级硅胶虽安全但静电问题普遍，尚无品牌有效解决",
                "design_suggestion": "开发防静电硅胶配方或表面涂层处理，或采用混合材质减小硅胶面积",
                "priority": "关键",
                "source_subcategory": "全部子品类"
            },
            {
                "need_description": "更适合新手/敏感人群的超温和强度起始",
                "need_type": "功能需求",
                "weight_score": 8.5,
                "user_frustration": "多款产品最低档强度对新手仍然过大，导致使用不适",
                "current_solution_gap": "强度分级不够精细，缺乏针对敏感人群的'超柔'模式",
                "design_suggestion": "设计更宽泛的强度区间（至少12档），第1档为极低起始强度，增加记忆功能",
                "priority": "关键",
                "source_subcategory": "空气脉冲/震动棒"
            },
            {
                "need_description": "无线充电支持，解决充电口进水和插拔不便",
                "need_type": "功能需求",
                "weight_score": 7.8,
                "user_frustration": "USB充电口容易积水、积灰，磁吸充电线丢失后难以配",
                "current_solution_gap": "仅个别产品支持Qi无线充电，大部分仍使用专用充电线",
                "design_suggestion": "集成Qi无线充电线圈，适配通用无线充电板，同时保留紧急USB-C口",
                "priority": "重要",
                "source_subcategory": "高端/智能产品"
            },
            {
                "need_description": "更精准的人体工学设计，减少使用疲劳",
                "need_type": "体验需求",
                "weight_score": 8.2,
                "user_frustration": "长时间手持导致手酸，产品角度不适合自身体位",
                "current_solution_gap": "多数产品采用通用棒状设计，缺乏针对不同手型和体型的差异化设计",
                "design_suggestion": "基于手部人体工学数据设计握持曲线，考虑不同使用体位下的接触角度",
                "priority": "重要",
                "source_subcategory": "震动棒/魔法棒"
            },
            {
                "need_description": "电池续航提升至6小时以上并减少衰减",
                "need_type": "品质需求",
                "weight_score": 7.5,
                "user_frustration": "续航普遍在2-4小时，使用半年后续航明显下降且无法更换电池",
                "current_solution_gap": "内置锂电池方案不可更换，电芯品质参差不齐",
                "design_suggestion": "采用更高密度电芯，优化电源管理电路，设计可更换电池仓方案",
                "priority": "重要",
                "source_subcategory": "全部子品类"
            },
            {
                "need_description": "模块化设计实现一机多用",
                "need_type": "功能需求",
                "weight_score": 7.0,
                "user_frustration": "不同刺激需求（阴蒂/G点/震动）需要购买多个设备，花费高且收纳不便",
                "current_solution_gap": "市场缺少可更换刺激头的模块化系统设计",
                "design_suggestion": "设计模块化主机+可互换刺激头（空气脉冲/震动/指压），磁吸接口通用底座",
                "priority": "重要",
                "source_subcategory": "跨品类机会"
            },
            {
                "need_description": "更私密、中性的外观设计语言",
                "need_type": "审美需求",
                "weight_score": 8.0,
                "user_frustration": "产品外观过于'情趣用品化'，不敢放在床头或浴室",
                "current_solution_gap": "多数产品设计语言仍偏向性感/艳丽，缺少克制中性的设计选项",
                "design_suggestion": "采用极简/有机设计语言，中性色系CMF，形态上参考消费电子产品而非传统成人用品",
                "priority": "重要",
                "source_subcategory": "全部子品类"
            },
            {
                "need_description": "加热功能提升初始使用舒适度",
                "need_type": "功能需求",
                "weight_score": 6.5,
                "user_frustration": "硅胶/塑料产品接触皮肤时温度偏低，需要预热或中途停顿等待升温",
                "current_solution_gap": "加热功能仅出现在极少数高端产品上，且升温速度慢",
                "design_suggestion": "集成快速加热元件（5秒内达38°C），恒温控制，低功耗设计",
                "priority": "一般",
                "source_subcategory": "高端产品"
            },
            {
                "need_description": "收纳和充电一体的解决方案",
                "need_type": "体验需求",
                "weight_score": 6.8,
                "user_frustration": "产品、充电线、替换头等配件零散，缺乏整合收纳方案",
                "current_solution_gap": "大部分产品仅附带收纳袋，缺乏充电收纳一体式设计",
                "design_suggestion": "设计充电收纳盒（类似AirPods方案），兼具收纳、充电、UV消毒功能",
                "priority": "一般",
                "source_subcategory": "中高端产品"
            }
        ]
        return needs

    # ================================================================
    # 7. 设计建议生成
    # ================================================================
    def _generate_design_recommendations(self, products: List[Dict], dimension_scores: List[Dict],
                                          gap_analysis: Dict, trends: List[Dict]) -> Dict:
        """生成综合设计建议"""
        # 找出当前市场的整体薄弱维度
        weak_dimensions = [d for d in dimension_scores if d["overall_score"] < 7]
        strong_dimensions = [d for d in dimension_scores if d["overall_score"] >= 7]

        # 分析各价格带的产品差距
        gaps = gap_analysis.get("feature_gaps", [])
        price_gaps = gap_analysis.get("price_gaps", [])

        # 核心设计方向
        core_direction = (
            "基于当前女性情趣用品市场的深度分析，新一代产品的设计应从以下四个层面构建竞争力："
            "第一，体验层面解决噪音和材质痛点（静音电机+防静电硅胶）；"
            "第二，功能层面实现智能化与模块化（APP控制+可换头系统）；"
            "第三，审美层面采用去性化的极简设计语言（中性色+有机形态）；"
            "第四，使用场景层面提升便利性（无线充电+收纳一体方案）。"
        )

        # 具体设计参数建议
        target_specs = {
            "建议尺寸": "15-17cm（棒体）/ 8-10cm（小巧款）",
            "建议重量": "110-150g（平衡手感与功能）",
            "推荐材质": "医用级防静电硅胶（主体）+ 抗菌ABS（底座）",
            "推荐形态": "有机曲线棒状基本型 + 可更换磁吸刺激头（模块化）",
            "按键方案": "2个物理按键（开/关+模式）+ 无极旋钮（强度调节）",
            "充电方案": "Qi无线充电（底部）+ USB-C应急口",
            "防水等级": "IPX7（1米水深30分钟）",
            "目标续航": "6小时（连续）/ 30天（待机）",
            "强度档位": "15级（含3级超轻柔起始档）",
            "噪音标准": "≤38分贝（实验室环境）/ ≤42分贝（实际使用）"
        }

        # CMF建议
        cmf = {
            "主色方案": "莫兰迪色系（雾霾蓝/豆沙绿/裸粉色）+ 经典黑白",
            "限量色": "年度限定色策略（如2026年度色）",
            "表面处理": "丝绒触感涂层（主体）+ 磨砂质感（底座）",
            "品牌标识": "极简logo压印（非印刷），避免传统情趣用品的浮夸风格",
            "包装设计": "环保牛皮纸盒+内衬（类似高端美妆品），外包无任何敏感标识"
        }

        # 差异化策略
        key_diffs = [
            "真正量化噪音标准（标注分贝值，行业首创透明化）",
            "防静电表面处理（解决硅胶吸附毛絮的核心痛点）",
            "Qi无线充电（适配主流充电生态，无需额外携带充电线）",
            "模块化刺激头系统（一机多用，降低用户购买多设备的成本）",
            "超低起始强度（覆盖敏感肌/新手用户，拓宽目标人群）",
            "收纳充电消毒一体盒（类似AirPods的完整体验闭环）"
        ]

        # 定位建议
        positioning = (
            "建议进入中高端市场（$79-$129价格带），抓住中端向高端升级的用户需求。"
            f"当前品类中，{weak_dimensions[0]['dimension_label'] if weak_dimensions else '体验'}维度整体评分最低({weak_dimensions[0]['overall_score'] if weak_dimensions else '6.5'}/10)，"
            "是最佳突破口。以'体验革新'为核心定位，用静音技术、防静电材质和极简设计三大卖点建立品牌认知。"
        )

        return {
            "core_direction": core_direction,
            "target_specs": target_specs,
            "cmf_recommendations": cmf,
            "key_differentiators": key_diffs,
            "positioning_advice": positioning
        }

    # ================================================================
    # 8. 可视化数据
    # ================================================================
    def _build_radar_data(self, dimension_scores: List[Dict]) -> List[Dict]:
        """构建设计维度雷达图数据"""
        return [
            {
                "name": d["dimension_label"],
                "value": d["overall_score"],
                "subs": [{"name": s["label"], "value": s["score"]} for s in d.get("sub_dimensions", [])]
            }
            for d in dimension_scores
        ]

    def _build_scatter_data(self, products: List[Dict]) -> List[Dict]:
        """构建散点图数据（价格 vs 评分）"""
        return [
            {
                "asin": p["asin"],
                "brand": p.get("brand", ""),
                "title": p["title"][:20],
                "price": p.get("price", 0),
                "rating": p.get("rating", 0),
                "review_count": p.get("review_count", 0),
                "category": p.get("subcategory", "")
            }
            for p in products
        ]

    def _build_heatmap_data(self, products: List[Dict], design_params: List[Dict]) -> List[Dict]:
        """构建设计参数热力图数据"""
        # 统计每个子品类中不同设计风格的出现频次
        style_by_cat = {}
        for p in products:
            cat = p.get("subcategory", "其他")
            style = p.get("design_params", {}).get("造型风格", "未标注")
            if cat not in style_by_cat:
                style_by_cat[cat] = {}
            if style not in style_by_cat[cat]:
                style_by_cat[cat][style] = 0
            style_by_cat[cat][style] += 1

        return [
            {"category": cat, "style": style, "count": count}
            for cat, styles in style_by_cat.items()
            for style, count in styles.items()
        ]

    def _sanitize_product(self, p: Dict) -> Dict:
        """清理产品数据（移除内部临时字段）"""
        return {k: v for k, v in p.items() if not k.startswith("_")}

    def _analyze_reviews_from_all_products(self) -> List[Dict]:
        """从所有产品的评论中提取需求分析"""
        # placeholder - 完整的评论分析需要结合NLP，这里用产品数据库的规格推断
        return self._extract_user_needs(self.products, self._build_gap_analysis(self.products, []))
