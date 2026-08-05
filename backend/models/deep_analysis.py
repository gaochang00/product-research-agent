"""深度分析数据模型 — 支持子维度评分、竞争格局、缺口分析"""
from pydantic import BaseModel
from typing import Optional, List


# ===== 子维度评分 =====
class SubDimensionScore(BaseModel):
    """子维度评分"""
    name: str
    score: float  # 1-10
    detail: str = ""  # 评分依据
    benchmark: str = ""  # 行业基准


class DimensionScore(BaseModel):
    """维度评分（含子维度）"""
    dimension_name: str
    dimension_label: str  # 中文简称
    overall_score: float  # 综合得分 1-10
    sub_dimensions: List[SubDimensionScore] = []
    summary: str = ""
    weight: float = 0  # 该维度在品类中的重要性权重


# ===== 设计参数 =====
class DesignParamComparison(BaseModel):
    """设计参数对比项"""
    param_name: str  # 参数名
    param_label: str  # 中文标签
    values: List[dict] = []  # [{product_asin, product_title, value}]
    distribution: dict = {}  # 值分布统计
    common_value: str = ""  # 最常见值
    rare_value: str = ""    # 稀缺值（机会点）
    design_implication: str = ""  # 设计含义


# ===== 市场格局 =====
class MarketSegment(BaseModel):
    """市场细分"""
    segment_name: str
    avg_price: float
    avg_score: float
    product_count: int
    products: List[str] = []  # ASIN列表


class CompetitiveLandscape(BaseModel):
    """竞争格局"""
    price_performance_matrix: List[dict] = []  # [{product, price, score, category}]
    brand_positioning: List[dict] = []  # [{brand, avg_price, avg_score, product_count}]
    category_distribution: List[dict] = []  # [{category, count, avg_price, avg_score}]
    price_tiers: List[MarketSegment] = []


# ===== 缺口分析 =====
class FeatureGap(BaseModel):
    """功能/设计缺口"""
    gap_description: str
    gap_type: str  # 功能缺口/设计缺口/体验缺口/价格缺口
    current_coverage: float  # 当前市场覆盖率 0-1
    demand_evidence: str  # 需求证据
    design_opportunity: str  # 设计机会
    difficulty: str  # 实现难度：高/中/低
    potential_revenue: str  # 潜在收益：高/中/低


class GapAnalysis(BaseModel):
    """缺口分析报告"""
    feature_gaps: List[FeatureGap]
    underserved_segments: List[dict]  # 未被充分服务的细分市场
    oversaturated_segments: List[dict]  # 过度饱和的细分
    price_gaps: List[dict]  # 价格空档


# ===== 品类趋势 =====
class CategoryTrend(BaseModel):
    """品类趋势"""
    trend_name: str
    trend_description: str
    adoption_rate: str  # 高/中/低
    growth_direction: str  # 上升中/稳定/下降
    design_relevance: str  # 设计相关性描述


# ===== 用户需求（增强版） =====
class DeepUserNeed(BaseModel):
    """用户需求（含设计映射）"""
    need_description: str
    need_type: str  # 功能/体验/审美/品质/价格
    weight_score: float  # 综合权重 1-10
    user_frustration: str = ""  # 当前用户的挫折点
    current_solution_gap: str = ""  # 现有方案的不足
    design_suggestion: str = ""  # 具体设计建议
    priority: str = ""  # 关键/重要/一般
    source_subcategory: str = ""  # 来源子品类


# ===== 最终设计输入 =====
class DeepDesignInput(BaseModel):
    """深度设计输入报告"""
    # 基础信息
    category: str = "女性情趣用品"
    analysis_date: str = ""
    total_products_analyzed: int = 0
    data_source: str = "Amazon.com"

    # 产品深度分析
    products: List[dict] = []  # 包含完整设计参数的产品数据
    dimension_scores: List[DimensionScore] = []
    design_params: List[DesignParamComparison] = []

    # 竞争格局
    competitive_landscape: CompetitiveLandscape = CompetitiveLandscape()

    # 缺口分析
    gap_analysis: GapAnalysis = GapAnalysis()

    # 品类趋势
    category_trends: List[CategoryTrend] = []

    # 用户需求
    user_needs: List[DeepUserNeed] = []
    top_needs: List[DeepUserNeed] = []

    # 设计建议
    design_recommendations: dict = {}
    cmf_recommendations: dict = {}
    target_specs: dict = {}  # 推荐的目标规格
    positioning_advice: str = ""

    # 可视化数据
    radar_dimension_data: List[dict] = []
    scatter_data: List[dict] = []
    heatmap_data: List[dict] = []
