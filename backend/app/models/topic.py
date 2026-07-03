"""Topic and analysis data models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field




class DashboardMetric(BaseModel):
    name: str
    value: float | int | str | None = None
    previous_value: float | int | str | None = None
    change_percent: float | None = None
    unit: str = ""
    source_ids: List[str] = Field(default_factory=list)


class DashboardSourceEvidence(BaseModel):
    id: str
    source_type: str = "unknown"
    platform: str = ""
    media_name: str = ""
    author: str = ""
    published_at: Optional[datetime] = None
    country: str = ""
    language: str = ""
    url: str = ""
    title: str = ""
    summary: str = ""
    reach: float | int | None = None
    ave: float | int | None = None
    sentiment: str = "neutral"
    brands: List[str] = Field(default_factory=list)
    models: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    engagement: dict = Field(default_factory=dict)
    credibility: str = "medium"


class DashboardContainer(BaseModel):
    topic_id: str
    analysis_id: str = ""
    generated_at: datetime = Field(default_factory=datetime.now)
    metrics: dict[str, DashboardMetric] = Field(default_factory=dict)
    sentiment: dict = Field(default_factory=dict)
    sources: List[DashboardSourceEvidence] = Field(default_factory=list)

# 5 preset topics with default prompts
DEFAULT_TOPICS = [
    {
        "id": "flash-charge-launch",
        "name": "比亚迪3月5日闪充中国发布会",
        "description": "2026年3月5日比亚迪「闪充中国」发布会舆情分析",
        "icon": "⚡",
        "default_prompt": """请针对2026年3月5日比亚迪“闪充中国”发布会开展全面深入的舆情分析，以海外社交媒体反馈为核心，结合国内外平台进行对比洞察。从技术传播、用户体验、竞品对比、基础设施影响等维度展开多层次逻辑推理和因果链分析，尤其关注以下要点：

闪充技术亮点在海外的传播热度、接受程度，以及官方演示与用户实际反馈的差异。
与特斯拉、宁德时代等竞品充电技术的海外讨论量、情绪倾向和用户偏好对比。
安全、电网负荷、实际场景适配性等质疑在海外的演化路径、峰值变化及传播特征。
发布会前后14天内（2026年2月19日-3月19日）海外市场热度持续性及对品牌形象、销量的实际影响。

数据要求（严格减少幻觉）：

重点抓取 X平台、Instagram、Telegram、Reddit、YouTube、Facebook、TikTok国际版、LinkedIn 等海外平台数据，同时对比国内平台。
必须通过多源交叉验证确认信息准确性，优先采用官方发布、主流媒体及可核实的用户反馈，避免未经验证的内容。
精准量化热度趋势与情绪变化，明确标注数据来源与可信度。

输出结构：

执行摘要（突出海外核心发现）
海外舆情核心发现（分维度）
国内外对比分析
数据量化支撑与因果链推理
趋势预测
差异化传播优化策略与风险对冲建议（特别针对海外市场）

请基于真实、可交叉验证的数据进行客观、中立、可靠的分析，所有结论均需有数据支撑，避免推测性表述。""",
        "data_source_path": "",
    },
    {
        "id": "q1-financial-report",
        "name": "比亚迪第一季度财报",
        "description": "2026年第一季度财报舆情与市场影响分析",
        "icon": "📊",
        "default_prompt": """请针对比亚迪2026年第一季度财报开展专业、深入的舆情与市场影响分析，以海外市场反馈为核心，结合国内外多源数据进行对比洞察。从财务指标解读、投资者情绪、竞品对比、资本市场反应等维度展开多层次逻辑推理和因果链分析，尤其关注以下重点：

营收、净利润、销量及分业务（新能源汽车、电池、海外）数据的同比/环比变化及市场解读。
毛利率、成本控制、现金流等关键指标引发的投资者和行业讨论。
与特斯拉、理想、小米等竞品的业绩对比声音。
资本市场反应（股价、评级）及消费者信心变化。

数据要求（严格减少幻觉）：

重点分析财报发布前后10-14天内的实时数据。
优先覆盖 X平台、Instagram、Telegram、Reddit、YouTube、LinkedIn、金融论坛等海外渠道，并交叉验证官方财报、主流财经媒体及机构报告。
所有数据必须多源交叉验证，量化积极信号与潜在风险，明确标注数据出处。

输出结构：

执行摘要（突出海外核心发现）
核心财务指标舆情分析
竞品对比与市场认知
资本市场及消费者信心变化
国内外舆情对比
因果链推理与趋势预测
舆情风险预判与应对策略（针对后续季度）

请基于真实、可验证的数据进行客观、严谨、可靠的分析，所有结论均需有明确数据或来源支撑。""",
        "data_source_path": "",
    },
    {
        "id": "smart-chip-launch",
        "name": "比亚迪5月28日智驾芯片发布会",
        "description": "2026年5月28日智驾芯片发布会深度分析",
        "icon": "🧠",
        "default_prompt": """请针对2026年5月28日比亚迪智驾芯片发布会开展深度舆情与技术竞争力分析，以海外社交媒体反馈为核心，结合国内外平台进行对比洞察。从技术参数解读、用户信任构建、竞品对比、品牌形象影响等维度展开多层次逻辑推理和因果链分析，尤其关注以下重点：

自研智驾芯片技术亮点：核心技术参数、性能突破的传播效果，以及与华为、地平线、英伟达等竞品的对比讨论热度与倾向。
功能演示与真实反馈：端到端智驾、城市NOA等功能的演示效果、海外用户真实体验反馈及信任度变化。
关键叙事传播：数据安全、国产替代等话题的传播路径、观点分歧及情绪演化。
品牌形象提升：发布会对比亚迪高端化与智能驾驶形象的实际拉动作用。

数据要求：

重点整合发布会前后14天内（2026年5月14日-6月11日）的全平台实时数据。
优先覆盖 X平台、Instagram、Telegram、Reddit、YouTube、LinkedIn 以及科技/汽车垂直论坛等海外渠道，同时对比国内微博、抖音、B站等平台。
精准量化技术可信度讨论、安全担忧等关键话题的热度趋势与情绪分数变化，标注重要传播节点。

输出结构：

执行摘要（突出海外核心发现）
技术亮点与竞品对比分析
用户反馈与信任度评估
关键叙事与风险舆情
国内外舆情对比
因果链推理与趋势预测
差异化传播策略与技术叙事优化建议

请基于最新可获取的真实数据，进行客观、严谨且具有前瞻性的分析，注重深层逻辑关联与全球用户视角，提供高实用价值的技术传播与品牌提升建议。""",
        "data_source_path": "",
    },
    {
        "id": "dod-1260h-list",
        "name": "美国国防部1260h清单事件",
        "description": "美国国防部将比亚迪纳入1260h清单舆情风险分析",
        "icon": "🛡️",
        "default_prompt": """请针对美国国防部将比亚迪纳入1260h清单的事件开展全面舆情风险与危机传播分析，以海外舆情为核心，结合国内外多语言数据进行深度对比洞察。从事件演变、舆情差异、连锁影响、企业回应等维度展开多层次逻辑推理和因果链分析，尤其关注以下重点：

事件全貌梳理：事件具体细节、官方解读以及完整时间线还原。
国内外舆情差异：国内（爱国情绪、国产替代预期）与国际（供应链担忧、出口限制、地缘风险）舆情的显著差异、互动传播及情绪特征。
连锁市场反应：对比亚迪海外业务、股价、合作伙伴以及中国新能源产业链的潜在影响与传导路径。
企业回应效果：比亚迪及相关方回应策略的传播效果、公众接受度及信任修复情况。

数据要求：

重点整合事件发生前后14天内的实时多语言数据。
优先覆盖 X平台、Instagram、Telegram、Reddit、YouTube、LinkedIn 等海外平台及国际主流媒体，同时对比国内微博、微信公众号、财经论坛等渠道。
精准量化正面与负面声音比例，识别关键传播节点与高影响力账号。

输出结构：

执行摘要（突出海外风险核心发现）
事件时间线与事实梳理
国内外舆情对比分析
连锁影响评估
企业回应效果评价
因果链推理与趋势预测
短期危机应对措施与中长期国际化风险对冲策略

请基于最新可获取的真实数据，进行客观、严谨且具有前瞻性的分析，注重深层逻辑关联、中美关系背景与全球舆情动态，提供高可操作性的危机管理建议。""",
        "data_source_path": "",
    },
    {
        "id": "goodwood-festival",
        "name": "BYD Goodwood Festival of Speed活动",
        "description": "2026年Goodwood活动海外舆情分析",
        "icon": "🏁",
        "default_prompt": """请针对BYD参加2026年Goodwood Festival of Speed（https://www.goodwood.com/motorsport/festival-of-speed/）开展全面深入的舆情分析，以海外社交媒体反馈为核心，结合国内外平台进行对比洞察。从活动传播、用户体验、竞品对比、品牌形象、性能文化认知等维度展开多层次逻辑推理和因果链分析，尤其关注以下要点：

活动传播热度：BYD在Goodwood活动中的曝光、传播热度、海外受众接受程度，以及现场展示与海外用户真实反馈之间的差异。
竞品对比讨论：与特斯拉、保时捷、Rimac、莲花等性能/电动竞品在Goodwood语境下的讨论量、情绪倾向和用户偏好对比。
品牌与性能叙事：BYD在海外高性能、豪华、赛道/爬坡等场景中的品牌认知变化，以及是否形成“技术实力”或“性能突破”的新叙事。
风险与质疑：关于质量、速度、续航、品牌调性、车迷圈接受度等质疑在海外的演化路径、峰值变化及传播特征。

数据要求（严格减少幻觉）：

重点抓取活动前后14天内（以实际活动日期为中心）的实时多语言数据。
优先覆盖 X平台、Instagram、Telegram、Reddit、YouTube、LinkedIn 以及 Goodwood 相关论坛、汽车垂直媒体与车迷社区，同时对比国内微博、抖音、B站等平台。
必须通过多源交叉验证确认信息准确性，优先采用官方发布、主流媒体及可核实的用户反馈，避免未经验证的内容。
精准量化热度趋势与情绪变化，明确标注数据来源与可信度。

输出结构：

执行摘要（突出海外核心发现）
海外舆情核心发现（分维度）
国内外对比分析
数据量化支撑与因果链推理
趋势预测
差异化传播优化策略与风险对冲建议（特别针对海外市场）

请基于真实、可交叉验证的数据进行客观、中立、可靠的分析，所有结论均需有数据支撑，避免推测性表述。""",
        "data_source_path": "",
    },
    {
        "id": "custom-report",
        "name": "通用舆情报告",
        "description": "自定义标题，生成专业汽车行业舆情分析报告",
        "icon": "📝",
        "default_prompt": """你是一位顶尖的汽车行业舆情战略分析师，具备强大的实时跨平台数据聚合能力和深度洞察推理优势，能够即时融合多源信息、进行因果逻辑分析、复杂观点聚类与多情景趋势预测。为车企舆情监控部门撰写高质量专业报告。

充分利用实时公开信息与社交媒体数据，进行客观中立、数据驱动的分析。报告结构统一为：
1. 事件/主题概述（关键事实、时间线）
2. 舆情传播概况（媒体覆盖量、平台分布、峰值时间、传播路径）
3. 舆情情绪分析（整体情绪分布比例、核心观点聚类、情绪演变趋势）
4. 关键影响与风险评估（品牌、销量、股价、政策、供应链等多维度影响）
5. 竞品/行业对比分析
6. 战略建议（短期应对、中长期布局，具备高可执行性）
7. 数据来源与分析方法说明（突出实时数据融合与深度推理过程）

语言专业、简洁、有力，使用文字形式描述关键趋势与预测情景。充分发挥实时数据聚合、深度因果洞察与战略前瞻能力。""",
        "data_source_path": "",
    },
]


class Topic(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    prompt: str
    default_prompt: str
    data_source_path: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PromptVersion(BaseModel):
    topic_id: str
    version: int
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    is_current: bool = True


class AnalysisResult(BaseModel):
    id: str
    topic_id: str
    model: str
    prompt: str
    content: str
    sentiment: dict = {}
    created_at: datetime = Field(default_factory=datetime.now)


class UploadFileItem(BaseModel):
    name: str
    url: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None
    storage_path: Optional[str] = None
    note: Optional[str] = None


class AnalysisRequest(BaseModel):
    topic_id: str
    model: Optional[str] = None
    data_source_path: Optional[str] = None
    custom_title: Optional[str] = None
    uploaded_files: List[UploadFileItem] = Field(default_factory=list)
    social_updates_limit: int = 10
    # True means the user clicked “重新分析”: bypass and clear today's cache/snapshot, then call the model again.
    force_refresh: bool = False


class PromptUpdateRequest(BaseModel):
    content: str


class RefreshConfig(BaseModel):
    enabled: bool = True
    updates_per_day: int = 2
    update_hours: list[int] = Field(default_factory=lambda: [9, 21])

    def normalized_hours(self) -> list[int]:
        hours = [hour for hour in self.update_hours if 0 <= hour <= 23]
        if not hours:
            return [9, 21]
        unique_hours = sorted(dict.fromkeys(hours))
        return unique_hours[:2] if len(unique_hours) > 2 else unique_hours
