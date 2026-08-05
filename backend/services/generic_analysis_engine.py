"""通用品类分析引擎 — 支持任意品类
=====================================
对任意关键词抓取到的 Amazon 产品数据，计算与深度分析引擎
相同的报告结构（dimension_scores / design_params / competitive_landscape /
gap_analysis / category_trends / user_needs / design_recommendations /
可视化数据），保证前端组件无需区分品类即可渲染。

维度采用通用可计算的规则（价格、评分、评论量、功能点、卖点文本等），
不依赖特定品类的中文关键词。
"""
import statistics
import re
from typing import Dict, List, Any, Tuple
from collections import Counter
from datetime import datetime


# ============================================================
# 通用关键词库（中英双语，按子维度匹配）
# ============================================================
_TERMS = {
    # 功能
    "smart": ["app", "bluetooth", "smart", "智能", "连接", "wifi", "wireless"],
    "multi_function": ["mode", "multiple", "多功能", "模式", "多种"],
    "unique_feature": ["unique", "专利", "patent", "exclusive", "innovative", "独家", "创新", "可拆卸", "detachable", "折叠", "foldable", "adjustable", "可调节"],
    "specs": ["spec", "parameter", "尺寸", "规格", "参数"],
    # 体验
    "easy": ["easy", "simple", "ergonomic", "方便", "简单", "人体工学", "舒适"],
    "quiet": ["quiet", "silent", "whisper", "静音", "安静", "低噪"],
    "clean": ["clean", "washable", "waterproof", "ipx", "防尘", "防水", "易清洁", "可水洗"],
    "battery": ["battery", "charge", "usb", "续航", "电池", "充电", "usb-c"],
    # 审美
    "design": ["design", "sleek", "style", "aesthetic", "minimalist", "设计", "造型", "极简", "美学"],
    "material": ["silicone", "stainless", "aluminum", "wood", "bamboo", "glass", "leather", "steel", "硅胶", "不锈钢", "铝合金", "木质", "竹", "皮革", "玻璃", "钢"],
    # 品质
    "durable": ["durable", "sturdy", "solid", "long-lasting", "耐用", "牢固", "坚固"],
    "premium": ["premium", "high-quality", "quality", "优质", "高品质", "精工"],
}


class GenericAnalysisEngine:
    """通用品类分析引擎"""

    def __init__(self):
        self.products: List[Dict] = []
        self.keyword = ""
        self.category = ""

    @staticmethod
    def _safe_mean(values: List, default: float = 0.0) -> float:
        """对可能为空/全为0的序列求均值，避免 statistics.mean([]) 异常"""
        values = [v for v in values if v]
        return statistics.mean(values) if values else default

    # ----------------------------------------------------------
    # 主入口
    # ----------------------------------------------------------
    def run(self, products: List[Dict], category: str = "", keyword: str = "") -> Dict[str, Any]:
        self.products = [p for p in products if p]
        self.keyword = keyword or category
        self.category = category or (keyword or "未知品类")

        # 1. 产品标准化
        for p in self.products:
            p.setdefault("features", [])
            p.setdefault("bullet_points", [])
            p.setdefault("color_options", [])
            p.setdefault("reviews", [])
            p.setdefault("subcategory", "")

        # 2. 各分析模块
        dimension_scores = self._compute_dimension_scores()
        design_params = self._compute_design_params()
        landscape = self._build_competitive_landscape()
        gap_analysis = self._build_gap_analysis(design_params)
        trends = self._build_trends(design_params)
        user_needs = self._extract_user_needs(design_params, gap_analysis)
        recommendations = self._generate_recommendations(
            dimension_scores, design_params, gap_analysis, user_needs)

        # 3. 可视化数据
        radar_data = self._build_radar_data(dimension_scores)
        scatter_data = self._build_scatter_data()
        heatmap_data = self._build_heatmap_data(design_params)

        return {
            "category": self.category,
            "category_en": self.keyword,
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total_products_analyzed": len(self.products),
            "data_source": "Amazon.com",
            "products": [self._sanitize_product(p) for p in self.products],
            "dimension_scores": dimension_scores,
            "design_params": design_params,
            "competitive_landscape": landscape,
            "gap_analysis": gap_analysis,
            "category_trends": trends,
            "user_needs": user_needs,
            "top_needs": sorted(user_needs, key=lambda n: n["weight_score"], reverse=True)[:6],
            "design_recommendations": recommendations,
            "radar_dimension_data": radar_data,
            "scatter_data": scatter_data,
            "heatmap_data": heatmap_data,
        }

    # ----------------------------------------------------------
    # 文本匹配工具
    # ----------------------------------------------------------
    def _text(self, p: Dict) -> str:
        """汇总产品可分析文本"""
        parts = [p.get("title", "")]
        parts += p.get("bullet_points", [])
        parts += p.get("features", [])
        return " ".join(str(x) for x in parts).lower()

    def _has_any(self, text: str, terms: List[str]) -> bool:
        return any(t in text for t in terms)

    def _count_terms(self, text: str, terms: List[str]) -> int:
        return sum(1 for t in terms if t in text)

    # ----------------------------------------------------------
    # 1. 维度评分（品类平均）
    # ----------------------------------------------------------
    def _define_dimensions(self) -> List[Dict]:
        return [
            {
                "name": "功能维度", "label": "功能", "weight": 0.22,
                "summary": "功能完整度、智能程度与差异化卖点",
                "subs": ["feature_richness", "smart_level", "unique_tech", "spec_clarity"],
            },
            {
                "name": "体验维度", "label": "体验", "weight": 0.20,
                "summary": "使用便利性、噪音控制、清洁维护与续航",
                "subs": ["ease_of_use", "noise_control", "clean_maintain", "battery_life"],
            },
            {
                "name": "审美维度", "label": "审美", "weight": 0.18,
                "summary": "造型设计、色彩选择与材质质感",
                "subs": ["design_language", "color_options", "material_texture"],
            },
            {
                "name": "品质维度", "label": "品质", "weight": 0.18,
                "summary": "材质等级、用户口碑与耐用性",
                "subs": ["material_grade", "user_rating", "durability"],
            },
            {
                "name": "价格维度", "label": "价格", "weight": 0.10,
                "summary": "定价策略、性价比与价格带分布",
                "subs": ["price_reasonableness", "value_perception", "tier_rarity"],
            },
            {
                "name": "市场维度", "label": "市场", "weight": 0.12,
                "summary": "市场热度、口碑规模与差异化程度",
                "subs": ["market_heat", "review_volume", "differentiation"],
            },
        ]

    def _score_product_dimensions(self, p: Dict) -> Dict[str, float]:
        """为单个产品计算各子维度得分（1-10）"""
        text = self._text(p)
        price = float(p.get("price") or 0)
        rating = float(p.get("rating") or 0)
        reviews = int(p.get("review_count") or 0)
        bullets = p.get("bullet_points", []) or []
        features = p.get("features", []) or []
        colors = p.get("color_options", []) or []

        # 价格参考区间（用全部产品的中位数）
        prices = [float(x.get("price") or 0) for x in self.products if x.get("price")]
        med_price = statistics.median(prices) if prices else price or 1

        s = {}

        # --- 功能 ---
        s["feature_richness"] = min(10, 4 + len(bullets) + len(features))
        s["smart_level"] = 8 if self._has_any(text, _TERMS["smart"]) else 4
        s["unique_tech"] = 8 if self._has_any(text, _TERMS["unique_feature"]) else 4
        s["spec_clarity"] = 8 if self._has_any(text, _TERMS["specs"]) else 4

        # --- 体验 ---
        s["ease_of_use"] = 7 if self._has_any(text, _TERMS["easy"]) else 5
        s["noise_control"] = 8 if self._has_any(text, _TERMS["quiet"]) else 5
        s["clean_maintain"] = 8 if self._has_any(text, _TERMS["clean"]) else 4
        s["battery_life"] = 7 if self._has_any(text, _TERMS["battery"]) else 4

        # --- 审美 ---
        s["design_language"] = 7 if self._has_any(text, _TERMS["design"]) else 5
        s["color_options"] = min(10, 4 + len(colors))
        s["material_texture"] = 7 if self._has_any(text, _TERMS["material"]) else 4

        # --- 品质 ---
        s["material_grade"] = 7 if self._has_any(text, _TERMS["premium"] + _TERMS["material"]) else 5
        s["user_rating"] = min(10, max(1, rating / 0.5)) if rating else 4
        s["durability"] = 7 if self._has_any(text, _TERMS["durable"]) else 5

        # --- 价格 ---
        if price > 0:
            ratio = price / (med_price or 1)
            s["price_reasonableness"] = 8 if 0.7 <= ratio <= 1.5 else (6 if ratio < 0.7 else 5)
            s["value_perception"] = min(10, 4 + rating) if rating and price > 0 else 5
        else:
            s["price_reasonableness"] = 5
            s["value_perception"] = 5
        s["tier_rarity"] = 6

        # --- 市场 ---
        s["market_heat"] = min(10, 3 + (reviews ** 0.3)) if reviews else 4
        s["review_volume"] = min(10, 2 + (reviews ** 0.35)) if reviews else 3
        # 差异化：标题/卖点中特色词数量
        s["differentiation"] = min(10, 4 + self._count_terms(text, _TERMS["unique_feature"]) * 2)

        return s

    def _compute_dimension_scores(self) -> List[Dict]:
        """品类平均维度分（与深度引擎输出结构一致）"""
        dimensions = self._define_dimensions()
        per_products = [self._score_product_dimensions(p) for p in self.products]

        result = []
        for dim in dimensions:
            sub_scores = []
            for sub_name in dim["subs"]:
                scores = [pp[sub_name] for pp in per_products if pp.get(sub_name, 0) > 0]
                avg = round(statistics.mean(scores), 1) if scores else 0
                labels = {
                    "feature_richness": "功能丰富度", "smart_level": "智能程度",
                    "unique_tech": "特色卖点", "spec_clarity": "规格清晰度",
                    "ease_of_use": "使用便利性", "noise_control": "噪音控制",
                    "clean_maintain": "清洁维护", "battery_life": "续航能力",
                    "design_language": "造型设计", "color_options": "色彩选择",
                    "material_texture": "材质质感", "material_grade": "材质等级",
                    "user_rating": "用户口碑", "durability": "耐用性",
                    "price_reasonableness": "定价合理性", "value_perception": "性价比",
                    "tier_rarity": "价格带覆盖", "market_heat": "市场热度",
                    "review_volume": "口碑规模", "differentiation": "差异化程度",
                }
                sub_scores.append({
                    "name": sub_name,
                    "label": labels.get(sub_name, sub_name),
                    "score": avg,
                    "detail": "",
                    "benchmark": f"最高{max(scores):.0f} / 最低{min(scores):.0f}" if scores else "",
                })
            overall = round(statistics.mean([s["score"] for s in sub_scores]), 1) if sub_scores else 0
            result.append({
                "dimension_name": dim["name"],
                "dimension_label": dim["label"],
                "overall_score": overall,
                "sub_dimensions": sub_scores,
                "summary": dim["summary"],
                "weight": dim["weight"],
            })
        return result

    # ----------------------------------------------------------
    # 2. 设计参数
    # ----------------------------------------------------------
    def _compute_design_params(self) -> List[Dict]:
        """价格、评分、材质、功能点等参数分布"""
        prices = [float(p.get("price") or 0) for p in self.products if p.get("price")]
        ratings = [float(p.get("rating") or 0) for p in self.products if p.get("rating")]
        reviews = [int(p.get("review_count") or 0) for p in self.products if p.get("review_count")]

        params = []

        if prices:
            # 价格分布
            price_dist = Counter()
            for pr in prices:
                bucket = f"${int(pr // 20 * 20)}-{int(pr // 20 * 20 + 20)}"
                price_dist[bucket] += 1
            common_price = price_dist.most_common(1)[0][0] if price_dist else "-"
            rare_price = price_dist.most_common()[-1][0] if price_dist else "-"
            params.append({
                "param_name": "价格分布", "param_label": "价格带",
                "distribution": dict(price_dist),
                "common_value": common_price, "rare_value": rare_price,
                "design_implication": f"中位价 ${statistics.median(prices):.0f}，平均价 ${statistics.mean(prices):.0f}。",
            })

        if ratings:
            rating_dist = Counter(ratings)
            common_r = rating_dist.most_common(1)[0][0] if rating_dist else 0
            params.append({
                "param_name": "评分分布", "param_label": "用户评分",
                "distribution": {f"{k:.1f}分": v for k, v in sorted(rating_dist.items())},
                "common_value": f"{common_r:.1f}分", "rare_value": f"{rating_dist.most_common()[-1][0]:.1f}分",
                "design_implication": f"平均评分 {statistics.mean(ratings):.2f}，多数产品集中在 {common_r:.1f} 分。",
            })

        if reviews:
            total_reviews = sum(reviews)
            params.append({
                "param_name": "评论规模", "param_label": "口碑规模",
                "distribution": {"头部(≥1000)": sum(1 for r in reviews if r >= 1000),
                                 "腰部(100-999)": sum(1 for r in reviews if 100 <= r < 1000),
                                 "长尾(<100)": sum(1 for r in reviews if r < 100)},
                "common_value": "长尾(<100)" if sum(1 for r in reviews if r < 100) else "头部(≥1000)",
                "rare_value": "头部(≥1000)",
                "design_implication": f"共 {total_reviews} 条评论，可用于判断市场需求热度。",
            })

        # 材质/卖点词频
        text_all = " ".join(self._text(p) for p in self.products)
        mat_counter = Counter()
        for term in _TERMS["material"]:
            c = text_all.count(term)
            if c:
                mat_counter[term] = c
        if mat_counter:
            top_mats = mat_counter.most_common(4)
            params.append({
                "param_name": "材质关键词", "param_label": "常用材质",
                "distribution": {k: v for k, v in top_mats},
                "common_value": top_mats[0][0], "rare_value": top_mats[-1][0],
                "design_implication": "卖点中高频出现的材质词，可作为 CMF 方向参考。",
            })

        return params

    # ----------------------------------------------------------
    # 3. 竞争格局
    # ----------------------------------------------------------
    def _build_competitive_landscape(self) -> Dict[str, Any]:
        prods = self.products

        # 品牌定位
        brand_map: Dict[str, List] = {}
        for p in prods:
            b = p.get("brand") or "未知品牌"
            brand_map.setdefault(b, []).append(p)
        brand_positioning = [
            {
                "brand": b,
                "product_count": len(items),
                "avg_price": round(self._safe_mean([float(x.get("price") or 0) for x in items]), 1),
                "avg_rating": round(self._safe_mean([float(x.get("rating") or 0) for x in items]), 2),
            }
            for b, items in brand_map.items()
        ]
        brand_positioning.sort(key=lambda x: x["avg_price"], reverse=True)

        # 价格分层
        prices = [float(p.get("price") or 0) for p in prods if p.get("price")]
        price_tiers = []
        if prices:
            q1 = sorted(prices)[len(prices) // 4]
            q3 = sorted(prices)[3 * len(prices) // 4]
            for name, lo, hi in [("入门", 0, q1), ("主流", q1, q3), ("高端", q3, float("inf"))]:
                items = [p for p in prods if lo <= float(p.get("price") or 0) < hi] if hi != float("inf") else \
                        [p for p in prods if float(p.get("price") or 0) >= q3]
                if items:
                    price_tiers.append({
                        "segment_name": name,
                        "avg_price": round(self._safe_mean([float(x.get("price") or 0) for x in items]), 1),
                        "avg_score": round(self._safe_mean([float(x.get("rating") or 0) for x in items]), 1),
                        "product_count": len(items),
                    })

        # 子品类分布
        cat_map: Dict[str, List] = {}
        for p in prods:
            c = p.get("subcategory") or "通用"
            cat_map.setdefault(c, []).append(p)
        category_distribution = [
            {
                "category": c,
                "count": len(items),
                "avg_price": round(self._safe_mean([float(x.get("price") or 0) for x in items]), 0),
                "avg_rating": round(self._safe_mean([float(x.get("rating") or 0) for x in items]), 1),
            }
            for c, items in cat_map.items()
        ]
        category_distribution.sort(key=lambda x: x["count"], reverse=True)

        return {
            "brand_positioning": brand_positioning,
            "price_tiers": price_tiers,
            "category_distribution": category_distribution,
            "top_products": sorted(
                prods, key=lambda p: (float(p.get("rating") or 0), int(p.get("review_count") or 0)),
                reverse=True)[:10],
        }

    # ----------------------------------------------------------
    # 4. 缺口分析
    # ----------------------------------------------------------
    def _build_gap_analysis(self, design_params: List[Dict]) -> Dict[str, Any]:
        """缺口分析（输出与调优引擎一致的前端兼容字段）"""
        feature_gaps = []
        prods = self.products

        # 价格缺口：主流价格带中缺乏高端/低端选择
        tiers = self._build_competitive_landscape()["price_tiers"]
        if len(tiers) < 3:
            feature_gaps.append({
                "gap_description": "价格带结构单一",
                "gap_type": "功能缺口",
                "current_coverage": 0.3,
                "demand_evidence": f"当前价格分层仅覆盖 {len(tiers)} 段，可能存在未被满足的价格需求区间。",
                "design_opportunity": "补充缺失价格带的差异化产品定义。",
                "difficulty": "低",
                "source_products": f"共 {len(prods)} 款产品",
            })
        else:
            for t in tiers:
                if t["product_count"] <= 2:
                    feature_gaps.append({
                        "gap_description": f"「{t['segment_name']}」价格带产品稀疏",
                        "gap_type": "功能缺口",
                        "current_coverage": 0.2,
                        "demand_evidence": f"该价格带仅有 {t['product_count']} 款产品，竞争较弱。",
                        "design_opportunity": "可评估进入该价格带的产品机会。",
                        "difficulty": "中" if t["segment_name"] != "入门" else "低",
                        "source_products": f"{t['segment_name']}价格带",
                    })

        # 评分缺口：低分产品集中暴露的维度
        low_rated = [p for p in prods if float(p.get("rating") or 0) > 0 and float(p.get("rating")) < 4.0]
        if low_rated:
            feature_gaps.append({
                "gap_description": "存在明显低分产品",
                "gap_type": "体验缺口",
                "current_coverage": 0.4,
                "demand_evidence": f"{len(low_rated)} 款产品评分低于 4.0，说明品类内仍有体验/品质短板未被头部解决。",
                "design_opportunity": "从低分差评中提炼具体痛点作为设计切入点。",
                "difficulty": "高",
                "source_products": "、".join(p.get("title", "")[:30] for p in low_rated[:3]),
            })

        # 评论数据充足性
        with_reviews = [p for p in prods if p.get("reviews")]
        if with_reviews:
            feature_gaps.append({
                "gap_description": "评论反馈可挖掘",
                "gap_type": "功能缺口",
                "current_coverage": 0.5,
                "demand_evidence": f"{len(with_reviews)} 款产品采集到真实用户评论，可继续下钻逐条分析。",
                "design_opportunity": "进入「用户评价深度分析」查看每条评论与多维评价。",
                "difficulty": "低",
                "source_products": "、".join(p.get("title", "")[:30] for p in with_reviews[:3]),
            })

        return {
            "feature_gaps": feature_gaps,
            "underserved_segments": [],
            "oversaturated_segments": [],
            "price_gaps": [],
        }

    # ----------------------------------------------------------
    # 5. 品类趋势
    # ----------------------------------------------------------
    def _build_trends(self, design_params: List[Dict]) -> List[Dict]:
        trends = []
        text_all = " ".join(self._text(p) for p in self.products)
        total = len(self.products) or 1

        trend_defs = [
            ("智能/连接功能", _TERMS["smart"], "功能", "智能化（App/蓝牙/无线）是当前主流卖点方向。"),
            ("防水/易清洁", _TERMS["clean"], "体验", "防水与易清洁属性正从高端卖点变为普遍预期。"),
            ("便携/人体工学", _TERMS["easy"], "体验", "人体工学与舒适握持成为用户选购的核心理由。"),
            ("环保/高端材质", _TERMS["premium"] + _TERMS["material"], "品质", "材质升级是品类高端化的主要表达方式。"),
        ]
        for name, terms, dim, desc in trend_defs:
            count = self._count_terms(text_all, terms)
            if count >= max(1, total // 5):
                trends.append({
                    "trend_name": name,
                    "trend_description": f"{desc}（{count}/{total} 款产品卖点中提及）",
                    "adoption_rate": f"{round(count / total * 100)}%",
                    "growth_direction": "up",
                    "design_relevance": dim,
                    "data": [{"label": "提及产品", "value": count}],
                })
        if not trends:
            trends.append({
                "trend_name": "品类卖点分散",
                "trend_description": "当前品类尚未形成明确的高频卖点共识，差异化空间较大。",
                "adoption_rate": "-",
                "growth_direction": "stable",
                "design_relevance": "综合",
                "data": [],
            })
        return trends

    # ----------------------------------------------------------
    # 6. 用户需求
    # ----------------------------------------------------------
    def _extract_user_needs(self, design_params: List[Dict], gap_analysis: Dict) -> List[Dict]:
        needs = []
        reviews = [r for p in self.products for r in (p.get("reviews") or [])]

        # 基于评论聚合需求
        if reviews:
            # 按条聚合：统计"提及该需求的评论条数"而非关键词种类数
            all_texts = [(r.get("text") or r.get("content") or "").lower() for r in reviews]
            pos_texts = [t for t, r in zip(all_texts, reviews) if float(r.get("rating") or 0) >= 4]
            neg_texts = [t for t, r in zip(all_texts, reviews) if 0 < float(r.get("rating") or 0) <= 3]
            total = len(reviews)

            need_rules = [
                ("使用体验与便利性", "体验需求", _TERMS["easy"], "用户普遍在意易用与舒适度，操作复杂会成为差评来源。", "以人体工学与直观交互为核心优化点。"),
                ("噪音控制", "体验需求", _TERMS["quiet"], "噪音是影响使用体验的关键因素，低噪是普遍诉求。", "采用低噪方案并把噪音水平作为可量化的卖点。"),
                ("清洁与维护", "品质需求", _TERMS["clean"], "清洁便利性与防水等级直接影响长期使用意愿。", "提升防水等级与可拆洗结构设计。"),
                ("续航与充电", "体验需求", _TERMS["battery"], "续航与充电便利性是差评高频项。", "延长续航并统一为通用充电接口。"),
                ("耐用与品质", "品质需求", _TERMS["durable"] + _TERMS["premium"], "做工与耐用性决定复购与口碑传播。", "强化结构强度与材质等级背书。"),
                ("材质与触感", "审美需求", _TERMS["material"], "材质触感与质感是用户感知品质的第一印象。", "在 CMF 上提升触感与视觉质感。"),
                ("价格与性价比", "价格需求", ["price", "worth", "value", "价格", "值"], "价格与价值感知影响下单决策。", "用配置/材质差异建立价格梯度。"),
                ("功能与模式", "功能需求", _TERMS["multi_function"], "功能模式丰富度是核心卖点比较维度。", "聚焦 2-3 个高使用率模式，避免功能堆砌。"),
            ]

            for label, need_type, terms, frustration, suggestion in need_rules:
                mentions = sum(1 for t in all_texts if any(term in t for term in terms))
                # 阈值放宽：小样本评论集（如 niche 品类）也能提取需求
                if mentions < max(1, total // 10):
                    continue
                freq = min(5, 2 + mentions / max(1, total) * 8)
                neg_mentions = sum(1 for t in neg_texts if any(term in t for term in terms))
                intensity = min(5, 2 + neg_mentions)
                weight_score = round(min(10, freq * 1.2 + intensity * 0.8), 1)
                needs.append({
                    "need_description": label,
                    "need_type": need_type,
                    "mention_frequency": round(freq, 1),
                    "sentiment_intensity": round(intensity, 1),
                    "impact_scope": round(min(5, 3 + freq / 3), 1),
                    "competition_coverage": 3.0,
                    "business_value": round(min(5, 3 + intensity / 3), 1),
                    "weight_score": weight_score,
                    "priority": "high" if weight_score >= 7 else ("medium" if weight_score >= 5 else "low"),
                    "user_frustration": frustration,
                    "design_suggestion": suggestion,
                    "source_reviews": [],
                })
        else:
            # 无评论时基于卖点特征推断
            text_all = " ".join(self._text(p) for p in self.products)
            infer_rules = [
                ("功能与模式", "功能需求", _TERMS["multi_function"], "卖点中频繁出现多模式/多功能描述。"),
                ("智能连接", "功能需求", _TERMS["smart"], "智能化（App/蓝牙/无线）是当前主流卖点。"),
                ("清洁维护", "品质需求", _TERMS["clean"], "防水易清洁被广泛宣传。"),
                ("材质质感", "审美需求", _TERMS["material"], "材质是卖点表达的常见维度。"),
                ("便携设计", "体验需求", _TERMS["easy"], "人体工学/便携设计被普遍强调。"),
            ]
            for label, need_type, terms, desc in infer_rules:
                c = self._count_terms(text_all, terms)
                if c >= max(1, len(self.products) // 5):
                    needs.append({
                        "need_description": label,
                        "need_type": need_type,
                        "mention_frequency": round(min(5, 2 + c / max(1, len(self.products)) * 4), 1),
                        "sentiment_intensity": 3.0,
                        "impact_scope": 3.0,
                        "competition_coverage": 3.0,
                        "business_value": 3.0,
                        "weight_score": round(min(10, 4 + c / max(1, len(self.products)) * 5), 1),
                        "priority": "medium",
                        "user_frustration": "",
                        "design_suggestion": desc,
                        "source_reviews": [],
                    })

        # 保底：至少输出一条需求
        if not needs:
            needs.append({
                "need_description": f"{self.category} 品类基础需求定义",
                "need_type": "功能需求",
                "mention_frequency": 3.0, "sentiment_intensity": 3.0,
                "impact_scope": 3.0, "competition_coverage": 3.0,
                "business_value": 3.0, "weight_score": 5.0, "priority": "medium",
                "user_frustration": "", "design_suggestion": "基于竞品参数与卖点建立品类基准。",
                "source_reviews": [],
            })
        return needs

    # ----------------------------------------------------------
    # 7. 设计建议
    # ----------------------------------------------------------
    def _generate_recommendations(self, dimension_scores: List[Dict], design_params: List[Dict],
                                  gap_analysis: Dict, user_needs: List[Dict]) -> Dict[str, Any]:
        dims = {d["dimension_label"]: d["overall_score"] for d in dimension_scores}
        weak_dims = sorted(dims.items(), key=lambda x: x[1])[:2] if dims else []

        # 价格建议
        price_param = next((p for p in design_params if p["param_name"] == "价格分布"), None)
        if price_param and price_param.get("design_implication"):
            price_advice = price_param["design_implication"]
        else:
            price_advice = "建议结合目标用户与竞品价格带确定定价区间。"

        top_needs = sorted(user_needs, key=lambda n: n["weight_score"], reverse=True)[:3]
        focus_areas = [n["need_description"] for n in top_needs]

        core = (f"围绕「{' / '.join(focus_areas) if focus_areas else self.category}」构建差异化卖点，"
                f"优先补齐弱项维度（{'、'.join(f'{k}({v:.1f}分)' for k, v in weak_dims)}）")

        key_diffs = [f"解决{n['need_description']}" for n in top_needs[:3]]
        if len(key_diffs) < 3:
            key_diffs.append("数据驱动的定价与配置梯度")

        # 目标规格
        target_specs = {}
        battery_p = next((p for p in design_params if p["param_name"] == "材质关键词"), None)
        if battery_p:
            top_mat = list(battery_p["distribution"].keys())[:2]
            target_specs["材质方向"] = " / ".join(top_mat) if top_mat else "根据目标价位选择"
        if price_param:
            target_specs["目标价格带"] = price_param.get("common_value", "主流价格带")
        target_specs["核心人群"] = "以好评用户画像与差评场景为准"
        target_specs["验证方式"] = "对 Top 需求做可用性测试"

        return {
            "core_direction": core,
            "key_differentiators": key_diffs,
            "target_specs": target_specs,
            "cmf_recommendations": {
                "材质": {"recommendation": target_specs.get("材质方向", "根据目标价位选择"), "rationale": "来自竞品卖点高频材质"},
                "色彩": {"recommendation": "参考主流配色 + 1 个差异化色", "rationale": "色彩选择是低成本的差异化手段"},
                "表面处理": {"recommendation": "哑光质感优先", "rationale": "哑光更耐指纹、更显品质"},
            },
            "positioning_advice": (
                f"以「{self.category}」为目标品类，聚焦用户高频需求（{'、'.join(focus_areas[:2])}）"
                "建立清晰的卖点表达，用可量化的参数建立信任。"
            ),
            "validation_plan": "先用低成本样机验证核心功能与体验，再扩展到 CMF 与包装。",
            "price_strategy": price_advice,
        }

    # ----------------------------------------------------------
    # 8. 可视化数据
    # ----------------------------------------------------------
    def _build_radar_data(self, dimension_scores: List[Dict]) -> Dict[str, Any]:
        return {
            "indicators": [{"name": d["dimension_label"], "max": 10} for d in dimension_scores],
            "data": [{"value": [d["overall_score"] for d in dimension_scores], "name": "品类平均"}],
        }

    def _build_scatter_data(self) -> List[Dict]:
        """价格-评分-评论量散点"""
        prices = [float(p.get("price") or 0) for p in self.products if p.get("price")]
        q3 = sorted(prices)[3 * len(prices) // 4] if prices else 0
        return [{
            "price": float(p.get("price") or 0),
            "rating": float(p.get("rating") or 0),
            "review_count": int(p.get("review_count") or 0),
            "title": (p.get("title") or "")[:60],
            "category": "高端" if (p.get("price") or 0) >= q3 else "主流",
        } for p in self.products]

    def _build_heatmap_data(self, design_params: List[Dict]) -> List[Dict]:
        """参数-品类热度矩阵（简化版）"""
        return [{
            "category": p.get("param_name", ""),
            "value": sum(p.get("distribution", {}).values()) if p.get("distribution") else 0,
        } for p in design_params]

    def _sanitize_product(self, p: Dict) -> Dict:
        return {k: v for k, v in p.items() if not k.startswith("_")}
