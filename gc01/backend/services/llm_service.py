"""AI 分析服务 - 调用大语言模型进行Review分析和需求提取"""
import json
import re
from typing import List, Dict, Any
from config import OPENAI_API_KEY, OPENAI_BASE_URL, AI_MODEL
from models.report import DimensionScore, ExtractedNeed, OpportunityPoint


class LLMService:
    """大语言模型分析服务"""

    def __init__(self):
        self.api_key = OPENAI_API_KEY
        self.base_url = OPENAI_BASE_URL
        self.model = AI_MODEL
        self.client = None

    def _init_client(self):
        """初始化OpenAI客户端"""
        if self.client is not None:
            return
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        except Exception:
            self.client = None

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """调用LLM"""
        self._init_client()
        if self.client is None or not self.api_key:
            return ""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"[LLM Error] {e}")
            return ""

    def analyze_reviews(self, product_title: str, reviews: List[Dict]) -> Dict[str, Any]:
        """分析评论，提取需求、优缺点、目标用户等"""
        # 整理评论文本
        review_texts = []
        for i, r in enumerate(reviews[:30]):  # 最多分析30条
            review_texts.append(f"[评论{i+1}] 评分:{r.get('rating', 0)}/5 | {r.get('content', '')}")

        reviews_str = "\n".join(review_texts)

        system_prompt = """你是资深的产品分析专家和工业设计师。你需要从亚马逊产品评论中提取对产品设计有价值的信息。
请严格按照JSON格式返回分析结果。"""

        user_prompt = f"""分析以下产品评论，从6个维度评估产品，并提取用户需求、机会点等信息。

产品名称: {product_title}

评论数据:
{reviews_str}

请返回如下JSON格式（不要加markdown包装）:
{{
    "dimension_scores": [
        {{
            "dimension_name": "功能维度",
            "score": 0-10之间的整数,
            "summary": "该维度分析总结（50字以内）",
            "strengths": ["优势1", "优势2"],
            "weaknesses": ["劣势1", "劣势2"]
        }},
        {{
            "dimension_name": "体验维度",
            "score": 0-10,
            "summary": "...",
            "strengths": [...],
            "weaknesses": [...]
        }},
        {{
            "dimension_name": "审美维度",
            "score": 0-10,
            "summary": "...",
            "strengths": [...],
            "weaknesses": [...]
        }},
        {{
            "dimension_name": "品质维度",
            "score": 0-10,
            "summary": "...",
            "strengths": [...],
            "weaknesses": [...]
        }},
        {{
            "dimension_name": "价格维度",
            "score": 0-10,
            "summary": "...",
            "strengths": [...],
            "weaknesses": [...]
        }},
        {{
            "dimension_name": "市场维度",
            "score": 0-10,
            "summary": "...",
            "strengths": [...],
            "weaknesses": [...]
        }}
    ],
    "pros": ["产品优点总结1", "优点2"],
    "cons": ["产品缺点总结1", "缺点2"],
    "target_users": ["目标用户描述1", "用户描述2"],
    "usage_scenarios": ["使用场景1", "场景2"]
}}

注意：
- 功能维度：产品功能是否完善、技术是否先进
- 体验维度：人机交互、操作便利性、使用舒适度
- 审美维度：外观设计、色彩、材质美感
- 品质维度：做工质量、耐用性、材质档次
- 价格维度：性价比、价格合理性
- 市场维度：定位是否清晰、差异化程度、目标人群匹配"""

        result = self._call_llm(system_prompt, user_prompt)
        if result:
            # 清理可能存在的markdown包装
            result = re.sub(r'```json\s*', '', result)
            result = re.sub(r'```\s*', '', result)
            result = result.strip()
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                pass

        # LLM调用失败时返回空结构
        return {
            "dimension_scores": [],
            "pros": [], "cons": [],
            "target_users": [], "usage_scenarios": []
        }

    def extract_user_needs(self, all_reviews: List[Dict], competitors: List[Dict]) -> List[Dict]:
        """从所有评论中提取用户需求并计算权重"""
        # 收集所有评论内容
        review_samples = []
        for r in all_reviews[:50]:
            review_samples.append(r.get('content', ''))

        reviews_str = "\n".join(review_samples[:10])  # 取前10条代表性评论

        system_prompt = """你是资深产品分析师。从用户评论中提取关键需求，并评估每个需求的权重。
请严格按照JSON格式返回。"""

        user_prompt = f"""分析以下用户评论，提取出5-8个核心用户需求。

评论内容:
{reviews_str}

竞品列表: {', '.join([c.get('title', '') for c in competitors[:5]])}

对每个需求，请评估：
1. mention_frequency (1-5): 该需求在评论中被提及的频率
2. sentiment_intensity (1-5): 用户表达该需求时的情感强烈程度
3. impact_scope (1-5): 该需求影响多少用户
4. competition_coverage (1-5, 反向): 竞品已经解决该需求的程度（越高说明竞品做得越少）
5. business_value (1-5): 解决该需求能带来的商业价值

返回JSON格式:
{{
    "needs": [
        {{
            "need_description": "需求描述（带具体产品语境）",
            "need_type": "功能需求/体验需求/审美需求/品质需求/价格需求",
            "mention_frequency": 0-5,
            "sentiment_intensity": 0-5,
            "impact_scope": 0-5,
            "competition_coverage": 0-5,
            "business_value": 0-5
        }}
    ]
}}"""

        result = self._call_llm(system_prompt, user_prompt)
        if result:
            result = re.sub(r'```json\s*', '', result)
            result = re.sub(r'```\s*', '', result)
            result = result.strip()
            try:
                data = json.loads(result)
                return data.get("needs", [])
            except json.JSONDecodeError:
                pass
        return []

    def generate_opportunity_points(self, competitors: List[Dict], all_needs: List[Dict]) -> List[Dict]:
        """生成机会点"""
        system_prompt = """你是资深产品策略师。基于竞品分析和用户需求，识别产品机会点。
请严格按照JSON格式返回。"""

        user_prompt = f"""基于以下竞品信息和用户需求，生成3-5个产品机会点。

竞品列表:
{json.dumps([{'title': c.get('title'), 'cons': c.get('cons', [])} for c in competitors[:5]], ensure_ascii=False)}

用户需求:
{json.dumps([{'desc': n.get('need_description'), 'type': n.get('need_type')} for n in all_needs[:5]], ensure_ascii=False)}

返回JSON格式:
{{
    "opportunities": [
        {{
            "title": "机会点标题",
            "description": "详细描述",
            "potential_level": "高/中/低",
            "related_dimension": "相关维度（功能/体验/审美/品质/价格/市场）",
            "estimated_impact": "预估影响"
        }}
    ]
}}"""

        result = self._call_llm(system_prompt, user_prompt)
        if result:
            result = re.sub(r'```json\s*', '', result)
            result = re.sub(r'```\s*', '', result)
            result = result.strip()
            try:
                data = json.loads(result)
                return data.get("opportunities", [])
            except json.JSONDecodeError:
                pass
        return []

    def generate_design_direction(self, analysis_data: Dict) -> Dict[str, Any]:
        """生成设计方向建议"""
        system_prompt = """你是资深工业设计师。基于产品和市场分析，提供设计方向建议。
请严格按照JSON格式返回。"""

        user_prompt = f"""基于以下分析数据，提供设计方向建议。

数据:
{json.dumps(analysis_data, ensure_ascii=False, default=str)[:2000]}

返回JSON格式:
{{
    "design_direction": "总体设计方向建议（100字以内）",
    "key_differentiators": ["差异化方向1", "方向2", "方向3"],
    "cmf_trends": "CMF色彩/材质/表面处理趋势建议（50字以内）",
    "target_price_range": "建议目标价格区间"
}}"""

        result = self._call_llm(system_prompt, user_prompt)
        if result:
            result = re.sub(r'```json\s*', '', result)
            result = re.sub(r'```\s*', '', result)
            result = result.strip()
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                pass

        return {
            "design_direction": "",
            "key_differentiators": [],
            "cmf_trends": "",
            "target_price_range": ""
        }
