# Oracle 舆情看板客户新需求 Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task. 每个任务都应小到可以由 gpt-5.4-mini 独立完成，并在任务完成后运行对应验证命令。

**Goal:** 将客户反馈中的“可视化、指标、文本分析、数据源追溯、一天两次更新”需求，分阶段落地到 BYDGEO 舆情分析系统。

**Architecture:** 先不重构整套系统，而是在现有 Topic 分析结果之上增量增加结构化 dashboard 数据层。后端负责标准化 metrics / sources / trends / evidence，前端负责扁平化展示 KPI、图表和来源追溯弹窗。日报一致性、重新分析、历史报告等现有能力保持不变。

**Tech Stack:** FastAPI + Pydantic + 本地 JSON 存储 + React + Ant Design + ECharts + Vite。

---

## 0. 当前需求拆解

客户图中的需求拆成 5 大块：

1. 数据可视化呈现
   - Campaign Overview
   - Sentiment Trend / Sentiment Breakdown
   - Coverage by Market / Country
   - Countries with Most Coverage
   - Top Sources by Mentions
   - Coverage Most Shared in Social Media
   - Coverage with Highest Potential Views

2. 重点指标
   - Total Mentions
   - Total Reach
   - Total AVE
   - Total Social Engagement
   - Sentiment

3. 文本分析
   - 核心传播主题
   - 高频关键词
   - 正面及负面报道重点
   - 主要媒体观点与潜在风险议题
   - 品牌、车型及竞品相关讨论
   - 重点新闻摘要

4. 数据源追溯
   - 原始文章链接
   - 媒体名称
   - 发布时间
   - 国家及语言
   - 作者
   - Reach
   - AVE
   - Sentiment
   - 文章摘要
   - 相关品牌、车型及关键词

5. 更新频率
   - 一天两次
   - 普通分析读取最新当日快照
   - 重新分析强制刷新

---

## 1. 实施原则

1. 不一次性大改。
2. 先建立数据结构，再接 UI。
3. 所有图表必须来自同一份 dashboard JSON。
4. 情绪图、报告正文、sentiment JSON 必须一致。
5. 没有真实数据时，字段写 `null` 或“未检索到”，禁止伪造。
6. 先做 P0，再做 P1/P2。
7. 每个任务完成后必须运行验证命令。

---

## 2. 分阶段路线

### Phase 1：后端 dashboard 数据结构和 API

目标：让每个 topic 分析完成后都能生成一份结构化 dashboard JSON。

### Phase 2：前端 KPI + 可视化基础展示

目标：在 Topic 页面显示客户图中最核心的 KPI、情绪图、来源排行。

### Phase 3：数据源追溯

目标：所有指标和分析结果都可点击查看来源详情。

### Phase 4：一天两次刷新

目标：增加定时刷新配置和状态展示。

### Phase 5：验收、远端同步、回归

目标：验证远端 129.153.168.220 上的完整体验。

---

# Phase 1：后端 dashboard 数据结构和 API

## Task 1: 新增 Dashboard 数据模型

**Objective:** 定义结构化 dashboard 数据模型，作为后续图表和来源追溯的统一数据契约。

**Files:**
- Modify: `backend/app/models/topic.py`

**Steps:**
1. 在 `topic.py` 中新增 Pydantic 模型：
   - `DashboardMetric`
   - `SentimentPoint`
   - `CountryCoverage`
   - `SourceEvidence`
   - `DashboardData`
2. 字段先覆盖 P0：
   - mentions / reach / ave / social_engagement
   - sentiment
   - sources
   - generated_at
3. 不影响现有 `AnalysisRequest` / `AnalysisResult`。

**Suggested model shape:**

```python
class DashboardMetric(BaseModel):
    name: str
    value: float | int | str | None = None
    previous_value: float | int | str | None = None
    change_percent: float | None = None
    unit: str = ""
    source_ids: List[str] = Field(default_factory=list)

class SourceEvidence(BaseModel):
    id: str
    topic_id: str
    source_type: str = "unknown"
    platform: str = ""
    media_name: str = ""
    author: str = ""
    published_at: Optional[str] = None
    country: str = ""
    language: str = ""
    url: str = ""
    title: str = ""
    summary: str = ""
    reach: Optional[float] = None
    ave: Optional[float] = None
    sentiment: str = "neutral"
    brands: List[str] = Field(default_factory=list)
    models: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    engagement: dict = Field(default_factory=dict)
    credibility: str = "medium"

class DashboardData(BaseModel):
    topic_id: str
    analysis_id: str = ""
    generated_at: datetime = Field(default_factory=datetime.now)
    metrics: dict[str, DashboardMetric] = Field(default_factory=dict)
    sentiment: dict = Field(default_factory=dict)
    sources: List[SourceEvidence] = Field(default_factory=list)
```

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/backend
python3 -m py_compile app/models/topic.py
```

Expected: exit 0.

---

## Task 2: 新增 dashboard 存储工具

**Objective:** 将 dashboard 数据持久化到 `backend/data/dashboard.json`，避免只存在内存中。

**Files:**
- Modify: `backend/app/utils/store.py`

**Steps:**
1. 增加 `DASHBOARD_FILE`。
2. 增加 `_load_dashboard()`、`_save_dashboard()`。
3. 增加：
   - `save_dashboard(topic_id: str, data: dict)`
   - `get_dashboard(topic_id: str) -> dict`
   - `clear_dashboard(topic_id: str | None = None)`
4. 使用 tmp 文件 + `os.replace`，避免写坏 JSON。

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/backend
python3 -m py_compile app/utils/store.py
```

Expected: exit 0.

---

## Task 3: 新增 dashboard 生成服务骨架

**Objective:** 从 `AnalysisResult.content` 中提取基础 dashboard JSON。

**Files:**
- Create: `backend/app/services/dashboard_service.py`

**Steps:**
1. 新建 `DashboardService`。
2. 增加 `build_from_analysis(result, topic_name="") -> dict`。
3. 第一版只做：
   - sentiment 直接使用 result.sentiment
   - total_mentions / total_reach / total_ave 先从正文正则提取
   - 提取不到则为 `None`
   - sources 先从 `【参考文献】` 和 `【社交媒体最新信息】` 中粗提取链接
4. 不调用大模型。

**Minimal implementation:**

```python
import re
from datetime import datetime

class DashboardService:
    def build_from_analysis(self, result, topic_name: str = "") -> dict:
        content = result.content or ""
        return {
            "topic_id": result.topic_id,
            "analysis_id": result.id,
            "generated_at": datetime.now().isoformat(),
            "metrics": {
                "total_mentions": self._metric("Total Mentions", self._extract_number(content, ["Total Mentions", "总提及量"])),
                "total_reach": self._metric("Total Reach", self._extract_number(content, ["Total Reach", "总触达量"])),
                "total_ave": self._metric("Total AVE", self._extract_number(content, ["Total AVE", "AVE"])),
            },
            "sentiment": result.sentiment or {},
            "sources": self._extract_sources(content, result.topic_id),
        }
```

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/backend
python3 -m py_compile app/services/dashboard_service.py
```

Expected: exit 0.

---

## Task 4: 为 dashboard_service 写最小单元测试

**Objective:** 验证基础指标和链接能被提取。

**Files:**
- Create: `backend/tests/test_dashboard_service.py`

**Steps:**
1. 构造一个假的 result。
2. content 中写入：
   - `Total Mentions: 190`
   - `Total Reach: 145m`
   - `Total AVE: 12345`
   - 一个 URL
3. 调用 `DashboardService.build_from_analysis()`。
4. 断言 metrics 和 sources 不为空。

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO
PYTHONPATH=backend python3 -m pytest backend/tests/test_dashboard_service.py -q
```

Expected: `passed`.

---

## Task 5: 分析完成后生成 dashboard 数据

**Objective:** 每次分析完成后自动生成并保存 dashboard JSON。

**Files:**
- Modify: `backend/app/routers/analysis.py`

**Steps:**
1. 在普通分析和流式分析完成后：
   - 调用 `DashboardService().build_from_analysis(result)`
   - 调用 `save_dashboard(req.topic_id, dashboard)`
2. 不改变原有 report history 逻辑。
3. 如果 dashboard 生成失败，打印错误，但不能影响分析报告返回。

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/backend
python3 -m py_compile app/routers/analysis.py app/services/dashboard_service.py app/utils/store.py
```

Expected: exit 0.

---

## Task 6: 新增 dashboard API

**Objective:** 前端可通过 API 获取每个 topic 的 dashboard 数据。

**Files:**
- Create: `backend/app/routers/dashboard.py`
- Modify: `backend/app/main.py`

**Steps:**
1. 新建 router：`prefix="/api/dashboard"`。
2. 增加接口：
   - `GET /api/dashboard/{topic_id}`
   - `GET /api/dashboard/{topic_id}/sources`
   - `GET /api/dashboard/{topic_id}/sources/{source_id}`
3. 在 `main.py` 注册 router。

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/backend
python3 -m py_compile app/routers/dashboard.py app/main.py
```

Expected: exit 0.

---

# Phase 2：前端 KPI + 可视化基础展示

## Task 7: 前端 API 增加 dashboard 请求

**Objective:** 前端 services 层支持 dashboard 数据读取。

**Files:**
- Modify: `frontend/src/services/api.ts`

**Steps:**
1. 增加：

```ts
export const getDashboard = (topicId: string) => api.get(`/dashboard/${topicId}`);
export const getDashboardSources = (topicId: string) => api.get(`/dashboard/${topicId}/sources`);
export const getDashboardSource = (topicId: string, sourceId: string) => api.get(`/dashboard/${topicId}/sources/${sourceId}`);
```

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/frontend
npm run build
```

Expected: build success.

---

## Task 8: 新增 KPI 卡片组件

**Objective:** 显示 Total Mentions / Reach / AVE / Social Engagement。

**Files:**
- Create: `frontend/src/components/DashboardKpiCards.tsx`

**Steps:**
1. 接收 `metrics` prop。
2. 使用 Ant Design `Card` + `Statistic`。
3. 无数据时显示 `未检索到`。
4. 如果有 `change_percent`，显示升降趋势。

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/frontend
npm run build
```

Expected: build success.

---

## Task 9: TopicPage 拉取 dashboard 数据

**Objective:** 分析完成或进入页面后加载 dashboard 数据。

**Files:**
- Modify: `frontend/src/pages/TopicPage.tsx`

**Steps:**
1. 引入 `getDashboard`。
2. 增加 state：`dashboard`、`loadingDashboard`。
3. `loadDashboard()` 根据 `topicId` 调用 API。
4. topic 切换时调用。
5. 分析完成后调用。
6. 不影响现有分析结果展示。

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/frontend
npm run build
```

Expected: build success.

---

## Task 10: TopicPage 展示 KPI 卡片

**Objective:** 在 topic 标题下方、扁平分析控制台下方展示 KPI 卡片。

**Files:**
- Modify: `frontend/src/pages/TopicPage.tsx`
- Use: `frontend/src/components/DashboardKpiCards.tsx`

**Steps:**
1. 在 `TopicPage` 中插入 `<DashboardKpiCards metrics={dashboard?.metrics} />`。
2. 只在 dashboard 有数据时展示。
3. 无数据时不占高度。

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/frontend
npm run build
```

Expected: build success.

---

## Task 11: 新增来源排行组件

**Objective:** 显示 Top Sources by Mentions 的基础列表。

**Files:**
- Create: `frontend/src/components/TopSourcesList.tsx`

**Steps:**
1. 接收 `sources` prop。
2. 展示：媒体名称、标题、国家、语言、sentiment、reach、url。
3. 点击条目触发 `onSelect(source)`。
4. 无数据时显示 `暂无来源数据`。

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/frontend
npm run build
```

Expected: build success.

---

# Phase 3：数据源追溯

## Task 12: 新增 SourceDetailDrawer

**Objective:** 点击来源后打开详情抽屉。

**Files:**
- Create: `frontend/src/components/SourceDetailDrawer.tsx`

**Steps:**
1. 使用 Ant Design `Drawer`。
2. 展示字段：
   - 原始文章链接
   - 媒体名称
   - 发布时间
   - 国家及语言
   - 作者
   - Reach
   - AVE
   - Sentiment
   - 文章摘要
   - 品牌/车型/关键词
3. URL 用 `<a target="_blank">`。

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/frontend
npm run build
```

Expected: build success.

---

## Task 13: TopicPage 接入来源详情抽屉

**Objective:** 来源排行可点击追溯详情。

**Files:**
- Modify: `frontend/src/pages/TopicPage.tsx`

**Steps:**
1. 增加 `selectedSource` state。
2. 在 `TopSourcesList` 中传 `onSelect`。
3. 渲染 `SourceDetailDrawer`。

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/frontend
npm run build
```

Expected: build success.

---

# Phase 4：趋势和图表

## Task 14: 新增 MentionsReachTrend 组件

**Objective:** 展示 Mentions 与 Reach 趋势图。

**Files:**
- Create: `frontend/src/components/MentionsReachTrend.tsx`

**Steps:**
1. 使用 `ReactECharts`。
2. 接收 `trend` 数组。
3. Mentions 用柱状图，Reach 用折线图。
4. 无数据时不渲染。

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/frontend
npm run build
```

Expected: build success.

---

## Task 15: 新增 CountryCoverageChart 组件

**Objective:** 先用横向 bar chart 展示 Countries with Most Coverage，不做地图。

**Files:**
- Create: `frontend/src/components/CountryCoverageChart.tsx`

**Steps:**
1. 使用 ECharts bar。
2. 展示国家和覆盖量。
3. 无数据时显示 Empty。

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/frontend
npm run build
```

Expected: build success.

---

# Phase 5：一天两次刷新

## Task 16: 新增刷新配置模型

**Objective:** 后端保存 dashboard 自动刷新配置。

**Files:**
- Modify: `backend/app/models/topic.py`
- Modify: `backend/app/utils/store.py`

**Steps:**
1. 新增字段：
   - enabled
   - times: `["09:00", "18:00"]`
   - timezone: `Asia/Hong_Kong`
2. store 中增加 get/update refresh config。

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/backend
python3 -m py_compile app/models/topic.py app/utils/store.py
```

Expected: exit 0.

---

## Task 17: 新增刷新状态 API

**Objective:** 前端可显示最近更新时间和下次更新时间。

**Files:**
- Modify: `backend/app/routers/dashboard.py`

**Steps:**
1. 增加 `GET /api/dashboard/{topic_id}/refresh-status`。
2. 返回：
   - last_refreshed_at
   - next_refresh_at
   - frequency: 一天两次

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/backend
python3 -m py_compile app/routers/dashboard.py
```

Expected: exit 0.

---

## Task 18: 前端展示刷新状态

**Objective:** 在 TopicPage 显示“最近更新时间 / 下次更新时间 / 一天两次”。

**Files:**
- Modify: `frontend/src/pages/TopicPage.tsx`

**Steps:**
1. 增加 refreshStatus state。
2. 拉取 `/refresh-status`。
3. 在扁平分析控制台附近展示小 Tag。

**Verify:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/frontend
npm run build
```

Expected: build success.

---

# Phase 6：回归验证和远端同步

## Task 19: 本地全量验证

**Objective:** 保证后端编译、前端构建均通过。

**Commands:**

```bash
cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/backend
python3 -m py_compile app/models/topic.py app/utils/store.py app/services/dashboard_service.py app/routers/dashboard.py app/routers/analysis.py app/main.py

cd /Users/juxiaobing/dev-work/claude_workspace/BYDGEO/frontend
npm run build
```

Expected:
- Python py_compile exit 0
- Vite build success

---

## Task 20: 远端同步到 129.153.168.220

**Objective:** 将通过验证的文件同步到远端并重启服务。

**Files likely to sync:**
- `backend/app/models/topic.py`
- `backend/app/utils/store.py`
- `backend/app/services/dashboard_service.py`
- `backend/app/routers/dashboard.py`
- `backend/app/routers/analysis.py`
- `backend/app/main.py`
- `frontend/src/services/api.ts`
- `frontend/src/pages/TopicPage.tsx`
- `frontend/src/components/DashboardKpiCards.tsx`
- `frontend/src/components/TopSourcesList.tsx`
- `frontend/src/components/SourceDetailDrawer.tsx`
- `frontend/src/components/MentionsReachTrend.tsx`
- `frontend/src/components/CountryCoverageChart.tsx`

**Verify remote:**

```bash
ssh -i <key> ubuntu@129.153.168.220 'cd ~/GEOSYS/bydgeo && ./scripts/restart_bydgeo.sh && sleep 5 && curl -s http://127.0.0.1:8000/health'
```

Expected:

```json
{"status":"ok","version":"1.0.0"}
```

---

## Task 21: 远端端到端验收

**Objective:** 证明客户需求第一版可用。

**Steps:**
1. 登录远端页面。
2. 打开 Goodwood topic。
3. 点击“重新分析”。
4. 确认报告生成。
5. 确认 KPI 卡片出现。
6. 确认情绪图有值，且与报告 JSON 一致。
7. 确认 Top Sources 有来源列表。
8. 点击来源，确认弹窗显示：
   - 原始文章链接
   - 媒体名称
   - 发布时间
   - 国家语言
   - 作者
   - Reach
   - AVE
   - Sentiment
   - 摘要
   - 品牌/车型/关键词

---

# gpt-5.4-mini 子任务清单汇总

以下每个子任务都应单独派发给 gpt-5.4-mini：

1. 添加 Dashboard 数据模型。
2. 添加 dashboard JSON 存储工具。
3. 创建 DashboardService 骨架。
4. 为 DashboardService 写最小测试。
5. 分析完成后生成 dashboard 数据。
6. 新增 dashboard API router。
7. 前端 api.ts 增加 dashboard 请求。
8. 创建 DashboardKpiCards。
9. TopicPage 拉取 dashboard 数据。
10. TopicPage 展示 KPI 卡片。
11. 创建 TopSourcesList。
12. 创建 SourceDetailDrawer。
13. TopicPage 接入来源详情抽屉。
14. 创建 MentionsReachTrend。
15. 创建 CountryCoverageChart。
16. 新增刷新配置模型。
17. 新增刷新状态 API。
18. 前端展示刷新状态。
19. 本地全量验证。
20. 远端同步并重启。
21. 远端端到端验收。

---

## 暂不做的内容

以下内容先不进入第一版，避免任务过大：

- 世界地图热力图真实 geojson 渲染。
- AVE 精确商业计算模型。
- 多平台真实爬虫。
- 完整定时任务后台调度器。
- Excel 导出 dashboard。
- 复杂权限系统。

---

## 第一版验收口径

第一版只要做到：

1. 每个 topic 页面显示核心 KPI。
2. 报告生成后能产生 dashboard JSON。
3. 来源可以点击追溯详情。
4. 情绪图与后端 sentiment 一致。
5. UI 结构接近客户截图中的 Campaign Overview + Source Traceability。
6. 一天两次刷新先展示状态和配置，自动执行可第二阶段增强。

即可算 P0 完成。
