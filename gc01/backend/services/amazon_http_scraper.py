"""Amazon HTTP 直抓爬虫 — 免费获取任意品类的 Amazon 真实搜索结果

原理：直接请求 Amazon 公开搜索页，解析 HTML 中的商品卡片数据。
与 Etsy 项目 Node.js 版 scraper.js 的 Amazon 抓取方案一致（该方案已验证可抓取）。

使用方式（本地调试需走代理）：
    set HTTPS_PROXY=http://127.0.0.1:7890
    from services.amazon_http_scraper import scrape_amazon
    products = scrape_amazon("wooden cane")
"""
import os
import re
import time
import random
from typing import Dict, List, Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
    "TE": "trailers",
}


def get_proxies() -> Optional[Dict[str, str]]:
    """从环境变量读取代理配置（本地调试用；生产环境无代理则返回 None）"""
    proxy_url = (
        os.environ.get("HTTPS_PROXY")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("http_proxy")
    )
    if not proxy_url:
        return None
    return {"http": proxy_url, "https": proxy_url}


def _random_headers() -> Dict[str, str]:
    headers = dict(DEFAULT_HEADERS)
    headers["User-Agent"] = random.choice(USER_AGENTS)
    return headers


def _fetch_page(keyword: str, page: int, max_retries: int = 3) -> Optional[str]:
    """抓取 Amazon 搜索页 HTML（503 限流时退避重试）"""
    url = f"https://www.amazon.com/s?k={quote(keyword)}&page={page}"
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(
                url,
                headers=_random_headers(),
                proxies=get_proxies(),
                timeout=20,
                allow_redirects=True,
            )
            if resp.status_code == 503:
                wait = 8 + attempt * 5
                print(f"[AmazonScraper] 第{page}页被限流(503)，{wait}s 后重试 ({attempt}/{max_retries})")
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                print(f"[AmazonScraper] 第{page}页状态码: {resp.status_code}")
                return None
            return resp.text
        except Exception as e:
            wait = 5 + attempt * 4
            print(f"[AmazonScraper] 第{page}页请求失败: {e}，{wait}s 后重试 ({attempt}/{max_retries})")
            time.sleep(wait)
    return None


def _is_sponsored(card) -> bool:
    """判断商品卡片是否为广告（Sponsored）"""
    marker = card.select_one(
        "[data-component-type='sp-sponsored-result'], "
        "span.puis-sponsored-label-text, .AdHolder, .adHolder"
    )
    return marker is not None


def _parse_price(card) -> float:
    """解析价格（多种格式）"""
    off = card.select_one(".a-price .a-offscreen")
    if off and off.get_text(strip=True):
        m = re.search(r"[\d,.]+", off.get_text())
        if m:
            return float(m.group().replace(",", ""))
    whole = card.select_one(".a-price-whole")
    if whole:
        m = re.search(r"[\d,.]+", whole.get_text())
        if m:
            return float(m.group().replace(",", ""))
    return 0.0


def _parse_rating(card) -> float:
    """解析评分"""
    star = card.select_one(".a-icon-star-small, .a-icon-star, [aria-label*='out of']")
    if star:
        label = star.get("aria-label") or star.get_text()
        m = re.search(r"([\d.]+)", label)
        if m:
            return float(m.group(1))
    return 0.0


def _parse_review_count(card) -> int:
    """解析评论数"""
    rev = card.select_one(".a-size-base.s-underline-text, [aria-label*='ratings'], "
                           "a.s-underline-text span, span.a-size-base")
    if rev:
        label = rev.get("aria-label") or rev.get_text()
        m = re.search(r"([\d,]+)", label)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except ValueError:
                return 0
    return 0


def parse_products(html: str) -> List[Dict]:
    """从 Amazon 搜索页 HTML 解析商品卡片"""
    products: List[Dict] = []
    soup = BeautifulSoup(html, "lxml")

    cards = soup.select(
        "div[data-asin], div.s-result-item, div[data-component-type='s-search-result']"
    )

    for card in cards:
        asin = card.get("data-asin") or ""
        if not asin or len(asin) != 10:
            continue
        if _is_sponsored(card):
            continue

        title_el = card.select_one("h2 span") or card.select_one("h2")
        title = title_el.get_text(strip=True) if title_el else ""

        price = _parse_price(card)
        if not title or price <= 0:
            continue

        img_el = card.select_one("img.s-image")
        image = img_el.get("src") if img_el else ""

        link_el = card.select_one("a[href*='/dp/']") or card.select_one("h2 a")
        href = link_el.get("href") if link_el else ""
        dp_match = re.search(r"/dp/([A-Z0-9]{10})", href or "")
        link = f"https://www.amazon.com/dp/{dp_match.group(1)}" if dp_match else (
            href if href.startswith("http") else f"https://www.amazon.com{href}"
        )

        products.append({
            "asin": asin,
            "title": title,
            "brand": "",
            "price": price,
            "currency": "USD",
            "rating": _parse_rating(card),
            "review_count": _parse_review_count(card),
            "main_image": image,
            "product_url": link,
            "category": "",
            "bsr_category": "",
            "features": [],
            "bullet_points": [],
            "color_options": [],
            "subcategory": "",
            "reviews": [],
            "source": "amazon-http",
        })

    # 按唯一 ASIN 去重
    seen = set()
    unique = []
    for p in products:
        if p["asin"] not in seen:
            seen.add(p["asin"])
            unique.append(p)
    return unique


def scrape_amazon(keyword: str, max_pages: int = 3, max_products: int = 28) -> List[Dict]:
    """抓取 Amazon 任意品类搜索结果（多页 + 去重）"""
    keyword = (keyword or "").strip()
    if not keyword:
        return []

    print(f"[AmazonScraper] 开始抓取: \"{keyword}\", 页数: {max_pages}")
    all_products: List[Dict] = []
    seen = set()

    for page in range(1, max_pages + 1):
        html = _fetch_page(keyword, page)
        if not html:
            break

        # 检测是否被验证码/反爬拦截
        if "api-services-support@amazon.com" in html or "captcha" in html.lower():
            print("[AmazonScraper] 触发验证码/反爬，提前结束")
            break

        page_products = parse_products(html)
        added = 0
        for p in page_products:
            if p["asin"] not in seen:
                seen.add(p["asin"])
                all_products.append(p)
                added += 1
        print(f"[AmazonScraper] 第{page}页: 解析到 {len(page_products)} 个（新增 {added}，累计 {len(all_products)}）")

        if len(all_products) >= max_products:
            all_products = all_products[:max_products]
            break

        # 页面间随机延迟，降低限流风险
        time.sleep(1.5 + random.random() * 1.5)

    print(f"[AmazonScraper] 完成，共 {len(all_products)} 个产品")
    return all_products


# ==================== 详情页 / 评论页抓取（提升分析深度） ====================

def _is_blocked(html: str) -> bool:
    """检测 Amazon 反爬/验证码页面"""
    low = html.lower()
    return "api-services-support@amazon.com" in low or "captcha" in low


def _parse_reviews(soup, max_reviews: int = 10) -> List[Dict]:
    """从已解析的 BeautifulSoup 中提取评论（兼容详情页内嵌评论与评论页两种结构）"""
    reviews = []
    for div in soup.select('div[data-hook="review"]'):
        title_el = div.select_one('[data-hook="review-title"] span, [data-hook="reviewTitle"]') \
            or div.select_one(".review-title span")
        body_el = div.select_one('[data-hook="review-body"] span, [data-hook="reviewText"]') \
            or div.select_one(".review-text-content span")
        star_el = div.select_one('[data-hook="review-star-rating"]') or div.select_one(".review-rating")
        date_el = div.select_one('[data-hook="review-date"]') or div.select_one(".review-date")
        helpful_el = div.select_one('[data-hook="helpful-vote-statement"]') or div.select_one(".review-votes")

        title = title_el.get_text(strip=True) if title_el else ""
        content = ""
        if body_el:
            # reviewText 容器取段落文本更干净（过滤 "Brief content visible..." 等提示）
            p_el = body_el.select_one("p")
            content = p_el.get_text(strip=True) if p_el else body_el.get_text(strip=True)
        if not content:
            continue

        rating = 0.0
        if star_el:
            label = star_el.get("aria-label") or star_el.get_text()
            m = re.search(r"([\d.]+)", label)
            if m:
                rating = float(m.group(1))

        date = date_el.get_text(strip=True) if date_el else ""
        helpful = 0
        if helpful_el:
            text = helpful_el.get("aria-label") or helpful_el.get_text()
            m = re.search(r"(\d+)", text)
            if m:
                helpful = int(m.group(1))

        reviews.append({
            "title": title,
            "text": content[:1000],
            "rating": rating,
            "date": date,
            "helpful": helpful,
            "verified": False,
        })
        if len(reviews) >= max_reviews:
            break
    return reviews


def fetch_product_detail(asin: str, max_reviews: int = 10, max_retries: int = 3) -> Dict:
    """抓取产品详情页，提取卖点（bullet points）、规格、品牌与内嵌评论"""
    url = f"https://www.amazon.com/dp/{asin}"
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=_random_headers(), proxies=get_proxies(), timeout=20)
            if resp.status_code == 503:
                wait = 8 + attempt * 5
                print(f"[AmazonScraper] 详情 {asin} 被限流(503)，{wait}s 后重试 ({attempt}/{max_retries})")
                time.sleep(wait)
                continue
            if resp.status_code != 200 or _is_blocked(resp.text):
                return {}
            soup = BeautifulSoup(resp.text, "lxml")

            bullet_points = []
            for li in soup.select("#feature-bullets li span.a-list-item"):
                text = li.get_text(strip=True)
                if text:
                    bullet_points.append(text)

            # 规格表（key → value），转化为可分析的卖点文本
            features = []
            for tr in soup.select("#productOverview_feature_div tr, #productDetails_techSpec_section_1 tr, #detailBullets_feature_div li"):
                text = tr.get_text(" ", strip=True)
                if text and len(text) < 120:
                    features.append(text)

            brand = ""
            byline = soup.select_one("#bylineInfo")
            if byline:
                brand = byline.get_text(strip=True).replace("Visit the", "").replace("Store", "").strip()

            return {
                "bullet_points": bullet_points[:12],
                "features": features[:14],
                "brand": brand,
                "reviews": _parse_reviews(soup, max_reviews),
            }
        except Exception as e:
            wait = 5 + attempt * 4
            print(f"[AmazonScraper] 详情页 {asin} 请求失败: {e}，{wait}s 后重试 ({attempt}/{max_retries})")
            time.sleep(wait)
    return {}


def fetch_product_reviews(asin: str, max_reviews: int = 10) -> List[Dict]:
    """抓取产品评论页，提取评论列表（备用；主流程直接复用详情页内嵌评论）"""
    url = f"https://www.amazon.com/product-reviews/{asin}?sortBy=recent&pageNumber=1"
    try:
        resp = requests.get(url, headers=_random_headers(), proxies=get_proxies(), timeout=20)
        if resp.status_code != 200 or _is_blocked(resp.text):
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        return _parse_reviews(soup, max_reviews)
    except Exception as e:
        print(f"[AmazonScraper] 评论页 {asin} 抓取失败: {e}")
        return []


def enrich_products(products: List[Dict], detail_limit: int = 12,
                    review_limit: int = 10) -> List[Dict]:
    """批量增强产品数据：详情卖点 + 用户评论（限量执行，控制请求频率）"""
    for i, p in enumerate(products[:detail_limit]):
        print(f"[AmazonScraper] 增强 {i+1}/{min(detail_limit, len(products))}: {p['asin']} {p['title'][:30]}...")
        detail = fetch_product_detail(p["asin"], max_reviews=review_limit)
        if detail:
            p["bullet_points"] = detail.get("bullet_points", [])
            p["features"] = detail.get("features", [])
            if detail.get("reviews"):
                p["reviews"] = detail.get("reviews")
            if not p.get("brand") and detail.get("brand"):
                p["brand"] = detail["brand"]
        time.sleep(1.0 + random.random() * 1.5)
    return products


def scrape_amazon_enriched(keyword: str, max_pages: int = 3, max_products: int = 28,
                           detail_limit: int = 12, review_limit: int = 10) -> List[Dict]:
    """抓取任意品类并补充详情卖点与评论（完整版）"""
    products = scrape_amazon(keyword, max_pages=max_pages, max_products=max_products)
    if not products:
        return []
    enrich_products(products, detail_limit=detail_limit, review_limit=review_limit)
    return products


if __name__ == "__main__":
    import sys
    kw = sys.argv[1] if len(sys.argv) > 1 else "wooden cane"
    prods = scrape_amazon(kw, max_pages=3, max_products=28)
    print(f"\n抓取到 {len(prods)} 个产品:")
    for p in prods[:10]:
        print(f"  {p['asin']} | ${p['price']} | {p['rating']}★({p['review_count']}) | {p['title'][:60]}")
