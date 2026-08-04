"""分析报告数据模型"""
from pydantic import BaseModel
from typing import Optional, List


class DimensionScore(BaseModel):
    """单一维度的评分"""
    dimension_name: str  # 功能、体验、审美、品质、价格、市场
    score: float  # 1-10分
    summary: str  # 该维度分析总结
    strengths: List[str] = []  # 优势点
    weaknesses: List[str] = []  # 劣势点


class ExtractedNeed(BaseModel):
    """从评论中提取的用户需求"""
    need_description: str  # 需求描述
    need_type: str  # 功能需求/体验需求/审美需求/品质需求
    mention_frequency: float  # 提及频率 1-5
    sentiment_intensity: float  # 情感强度 1-5
    impact_scope: float  # 影响范围 1-5
    competition_coverage: float  # 竞品覆盖度 1-5(反向)
    business_value: float  # 商业价值 1-5
    weight_score: float  # 综合权重分
    source_reviews: List[str] = []  # 来源评论摘录


class OpportunityPoint(BaseModel):
    """机会点"""
    title: str
    description: str
    potential_level: str  # 高/中/低
    related_dimension: str
    estimated_impact: str


class CompetitorAnalysis(BaseModel):
    """单个竞品的多维度分析"""
    asin: str
    title: str
    brand: str
    price: float
    rating: float
    review_count: int
    main_image: str
    product_url: str = ""  # 亚马逊产品链接
    dimension_scores: List[DimensionScore]
    overall_score: float  # 综合评分
    pros: List[str] = []  # 优点总结
    cons: List[str] = []  # 缺点总结
    target_users: List[str] = []  # 目标用户
    usage_scenarios: List[str] = []  # 使用场景


class DesignInputReport(BaseModel):
    """最终设计输入报告"""
    # 基本信息
    category: str = "女性情趣用品"
    analysis_date: str = ""
    
    # 竞品概览
    analyzed_products: List[CompetitorAnalysis]
    
    # 市场需求
    user_needs: List[ExtractedNeed]
    top_needs: List[ExtractedNeed]  # Top需求的快速入口
    
    # 机会点
    opportunity_points: List[OpportunityPoint]
    
    # 设计建议
    design_direction: str  # 设计方向建议
    key_differentiators: List[str]  # 关键差异化方向
    cmf_trends: str  # CMF趋势
    target_price_range: str  # 目标价格区间
    
    # 可视化数据
    category_average_scores: dict  # 品类平均分
    dimension_importance: dict  # 各维度重要性权重


class AnalysisRequest(BaseModel):
    """分析请求"""
    keyword: str  # 搜索关键词
    max_products: int = 8  # 最多分析产品数
    max_reviews_per_product: int = 50  # 每个产品最多分析评论数
    use_demo_data: bool = True  # 是否使用示例数据（无API时）


class AnalysisResponse(BaseModel):
    """分析响应"""
    status: str
    message: str
    report: Optional[DesignInputReport] = None
    progress: int = 0
