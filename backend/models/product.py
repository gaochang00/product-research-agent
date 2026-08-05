"""产品数据模型"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ProductSearchResult(BaseModel):
    """亚马逊搜索结果中的单个产品"""
    asin: str
    title: str
    brand: Optional[str] = ""
    price: Optional[float] = 0
    currency: str = "USD"
    rating: Optional[float] = 0
    review_count: Optional[int] = 0
    main_image: Optional[str] = ""
    product_url: str = ""
    category: Optional[str] = ""
    bsr_category: Optional[str] = ""


class ProductSearchResponse(BaseModel):
    """搜索结果响应"""
    products: List[ProductSearchResult]
    total_results: int = 0
    search_keyword: str = ""


class ProductDetail(BaseModel):
    """产品详细信息"""
    asin: str
    title: str
    brand: Optional[str] = ""
    price: Optional[float] = 0
    currency: str = "USD"
    rating: Optional[float] = 0
    review_count: Optional[int] = 0
    main_image: Optional[str] = ""
    product_images: List[str] = []
    product_url: str = ""
    category: Optional[str] = ""
    bsr_category: Optional[str] = ""
    description: Optional[str] = ""
    bullet_points: List[str] = []
    specifications: dict = {}
    dimensions: Optional[str] = ""
    weight: Optional[str] = ""
    color_options: List[str] = []
    material: Optional[str] = ""
    features: List[str] = []
    estimated_monthly_sales: Optional[int] = 0


class ReviewItem(BaseModel):
    """单条评论"""
    review_id: Optional[str] = ""
    title: Optional[str] = ""
    content: str = ""
    rating: float = 0
    date: Optional[str] = ""
    verified_purchase: bool = False
    variant: Optional[str] = ""
    helpful_count: int = 0


class ProductReviews(BaseModel):
    """产品评论集合"""
    asin: str
    title: str
    reviews: List[ReviewItem]
    total_reviews: int = 0
    rating_distribution: dict = {}
