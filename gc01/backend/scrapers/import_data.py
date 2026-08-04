"""
数据导入脚本 — 将爬取的亚马逊数据导入分析系统
=================================================
使用方法：
  1. 先运行 amazon_scraper.py 爬取数据
  2. 运行本脚本导入数据到分析系统
  3. 重启后端服务，即可在Web页面看到真实数据

也可以手动指定JSON文件：
  python import_data.py data/amazon_products_20260304_120000.json
"""

import json
import sys
import shutil
from pathlib import Path

# 路径配置
BACKEND_DIR = Path(__file__).parent.parent
DATA_DIR = BACKEND_DIR.parent / "data"
SCRAPED_DATA_DIR = DATA_DIR

# 目标文件：分析引擎使用的数据文件
TARGET_FILE = BACKEND_DIR / "services" / "expanded_demo_data.py"


def find_latest_json() -> Path:
    """查找最新的爬取数据文件"""
    json_files = sorted(SCRAPED_DATA_DIR.glob("amazon_products_*.json"))
    if not json_files:
        return None
    return json_files[-1]


def load_json_data(filepath: Path) -> list:
    """加载JSON数据"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"📄 已加载 {len(data)} 个产品数据")
    return data


def generate_python_data(products: list) -> str:
    """生成 Python 数据文件内容"""
    lines = []
    lines.append('"""自动导入的亚马逊爬取数据 — 由 import_data.py 生成"""')
    lines.append('')
    lines.append('# ============================================================')
    lines.append('# 自动导入数据 - 请勿手动修改此文件')
    lines.append(f'# 数据来源: Amazon.com')
    lines.append(f'# 产品数量: {len(products)}')
    lines.append('# ============================================================')
    lines.append('')
    lines.append('')
    lines.append('IMPORTED_PRODUCTS = [')
    
    for i, p in enumerate(products):
        # 格式化产品数据
        asin = p.get("asin", f"BIMPORT{i:03d}")
        title = p.get("title", "").replace("'", "\\'").replace('"', '\\"')
        brand = p.get("brand", "").replace("'", "\\'").replace('"', '\\"')
        price = p.get("price", 0)
        rating = p.get("rating", 0)
        review_count = p.get("review_count", 0)
        main_image = p.get("main_image", "")
        product_url = p.get("product_url", f"https://www.amazon.com/dp/{asin}")
        subcategory = p.get("subcategory", "Clitoral Stimulators")
        bsr = p.get("bsr_category", "")
        description = p.get("description", "").replace("'", "\\'").replace('"', '\\"')
        
        # 规格
        specs = p.get("specifications", {})
        specs_str = "{"
        for k, v in specs.items():
            k_clean = k.replace("'", "\\'")
            v_clean = v.replace("'", "\\'")
            specs_str += f'"{k_clean}": "{v_clean}", '
        specs_str += "}"
        
        # 卖点
        bullets = p.get("bullet_points", [])
        bullets_str = "[" + ", ".join(f'"{b.replace(chr(34), chr(39))}"' for b in bullets[:6]) + "]"
        
        # 功能
        features = p.get("features", [])
        features_str = "[" + ", ".join(f'"{f}"' for f in features) + "]"
        
        # 颜色
        colors = p.get("color_options", [])
        colors_str = "[" + ", ".join(f'"{c}"' for c in colors[:6]) + "]"
        
        dimensions = p.get("dimensions", "")
        weight = p.get("weight", "")
        material = p.get("material", "").replace("'", "\\'")
        
        # 从标题推断子品类
        title_lower = title.lower()
        if "air pulse" in title_lower or "satisfyer" in title_lower:
            subcategory = "空气脉冲/阴蒂刺激器"
        elif "wand" in title_lower or "magic" in title_lower:
            subcategory = "魔法棒/强震棒"
        elif "rabbit" in title_lower:
            subcategory = "兔兔/双头刺激器"
        elif "g-spot" in title_lower or "g spot" in title_lower:
            subcategory = "G点专用棒"
        elif "bullet" in title_lower or "mini" in title_lower:
            subcategory = "迷你/子弹震"
        elif "wearable" in title_lower or "panty" in title_lower:
            subcategory = "穿戴式"
        elif "couple" in title_lower or "couples" in title_lower:
            subcategory = "情侣互动"
        else:
            subcategory = "Clitoral Stimulators"
        
        lines.append('')
        lines.append('{')
        lines.append(f'    "asin": "{asin}",')
        lines.append(f'    "title": "{title}",')
        lines.append(f'    "brand": "{brand}",')
        lines.append(f'    "price": {price},')
        lines.append(f'    "currency": "USD",')
        lines.append(f'    "rating": {rating},')
        lines.append(f'    "review_count": {review_count},')
        lines.append(f'    "main_image": "{main_image}",')
        lines.append(f'    "product_url": "{product_url}",')
        lines.append(f'    "category": "女性情趣用品",')
        lines.append(f'    "subcategory": "{subcategory}",')
        lines.append(f'    "bsr_category": "{bsr}",')
        lines.append(f'    "description": """{description[:300]}""",')
        lines.append(f'    "bullet_points": {bullets_str},')
        lines.append(f'    "specifications": {specs_str},')
        lines.append(f'    "dimensions": "{dimensions}",')
        lines.append(f'    "weight": "{weight}",')
        lines.append(f'    "color_options": {colors_str},')
        lines.append(f'    "material": "{material}",')
        lines.append(f'    "features": {features_str},')
        lines.append(f'    "estimated_monthly_sales": 0,')
        
        # 评论数据
        reviews = p.get("reviews", [])
        if reviews:
            reviews_str = json.dumps(reviews, ensure_ascii=False)
            # 转义JSON字符串中的特殊字符用于Python代码
            reviews_str = reviews_str.replace("'", "\\'")
            lines.append(f'    "reviews": {reviews_str},')
        else:
            lines.append(f'    "reviews": [],')
        
        # 评论摘要
        review_summary = p.get("review_summary", {})
        if review_summary:
            summary_str = json.dumps(review_summary, ensure_ascii=False)
            lines.append(f'    "review_summary": {summary_str}')
        else:
            lines.append(f'    "review_summary": {{}}')
        
        lines.append('},')
    
    lines.append(']')
    lines.append('')
    lines.append('# ============================================================')
    lines.append('# 导出列表 — 直接覆盖 EXPANDED_PRODUCTS 即可使用')
    lines.append('# ============================================================')
    lines.append('')
    lines.append('IMPORTED_PRODUCTS_LIST = IMPORTED_PRODUCTS')
    lines.append('')
    
    return '\n'.join(lines)


def main():
    print("=" * 50)
    print("  亚马逊数据导入工具")
    print("=" * 50)
    
    # 确定输入文件
    input_file = None
    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
        if not input_file.exists():
            print(f"❌ 文件不存在: {input_file}")
            return
    else:
        input_file = find_latest_json()
        if not input_file:
            print("❌ 未找到爬取数据文件")
            print("   请先运行: python amazon_scraper.py")
            print("   或指定文件: python import_data.py data/xxx.json")
            return
    
    print(f"📂 输入文件: {input_file}")
    
    # 加载数据
    products = load_json_data(input_file)
    if not products:
        print("❌ 数据为空")
        return
    
    # 生成Python代码
    print("🔄 正在生成数据文件...")
    py_content = generate_python_data(products)
    
    # 保存到 services 目录
    output_path = BACKEND_DIR / "services" / "imported_data.py"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(py_content)
    
    print(f"✅ 已生成: {output_path}")
    print(f"📊 共导入 {len(products)} 个产品")
    print()
    print("下一步操作:")
    print("  1. 打开 backend/services/deep_analysis_engine.py")
    print("  2. 把开头的导入语句从:")
    print("     from services.expanded_demo_data import EXPANDED_PRODUCTS")
    print("     改为:")
    print("     from services.imported_data import IMPORTED_PRODUCTS_LIST as EXPANDED_PRODUCTS")
    print("  3. 重启后端服务即可查看真实数据")
    print()


if __name__ == "__main__":
    main()