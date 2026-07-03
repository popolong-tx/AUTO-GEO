import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Card, Typography, Select, Button, Space, Tag,
  Spin, Empty, message, Tabs, Input, Upload, List, Collapse, Divider,
} from 'antd';
import {
  PlayCircleOutlined, EditOutlined, ReloadOutlined,
  FilePdfOutlined, UploadOutlined, DeleteOutlined, EyeOutlined,
} from '@ant-design/icons';
import { useParams } from 'react-router-dom';
import {
  getTopic, streamAnalysis, generateReport, listReports, uploadReferenceFile, getDashboard, getDashboardSources,
} from '../services/api';

import PromptEditor from '../components/PromptEditor';
import SentimentChart from '../components/SentimentChart';
import MentionsReachTrendChart from '../components/MentionsReachTrendChart';
import CountryCoverageChart from '../components/CountryCoverageChart';
import ReportList from '../components/ReportList';
import StreamingContent from '../components/StreamingContent';
import SourceDetailDrawer from '../components/SourceDetailDrawer';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const socialLimitOptions = [10, 50, 100];

const TopicPage: React.FC = () => {
  const { topicId } = useParams<{ topicId: string }>();
  const [topic, setTopic] = useState<any>(null);
  const [selectedModel, setSelectedModel] = useState<string>('xai.grok-4.20-multi-agent-0309');
  const [models, setModels] = useState<any[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [streamContent, setStreamContent] = useState('');
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [promptEditorOpen, setPromptEditorOpen] = useState(false);
  const [reports, setReports] = useState<any[]>([]);
  const [loadingReports, setLoadingReports] = useState(false);
  const [dashboard, setDashboard] = useState<any>(null);
  const [loadingDashboard, setLoadingDashboard] = useState(false);
  const [dashboardSources, setDashboardSources] = useState<any[]>([]);
  const [loadingDashboardSources, setLoadingDashboardSources] = useState(false);
  const [sourceDrawerOpen, setSourceDrawerOpen] = useState(false);
  const [selectedSource, setSelectedSource] = useState<any>(null);
  const [loadingSourceDetail, setLoadingSourceDetail] = useState(false);
  const [sourceDetailContent, setSourceDetailContent] = useState<any>(null);
  const [customTitle, setCustomTitle] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState<any[]>([]);
  const [previewFile, setPreviewFile] = useState<any>(null);
  const [socialUpdatesLimit, setSocialUpdatesLimit] = useState<number>(10);
  const streamRef = useRef<any>(null);
  const forceRefreshRef = useRef(false);

  const isCustom = topicId === 'custom-report';

  useEffect(() => {
    if (!topicId) return;
    getTopic(topicId).then((res) => setTopic(res.data));
    setModels([
      { id: 'xai.grok-4.20-multi-agent-0309', name: 'Grok 4.20', description: '复杂分析 / 默认' },
      { id: 'xai.grok-4.3', name: 'Grok 4.3', description: '更快 / 通用分析' },
    ]);
    setSelectedModel('xai.grok-4.20-multi-agent-0309');
    loadReports();
    loadDashboard();
    loadDashboardSources();
    setCustomTitle('');
    setUploadedFiles([]);
    setAnalysisResult(null);
    setStreamContent('');
    setPreviewFile(null);
    setSocialUpdatesLimit(10);
  }, [topicId]);

  const loadReports = () => {
    if (!topicId) return;
    setLoadingReports(true);
    listReports(topicId)
      .then((res) => setReports(res.data.reports))
      .catch(() => {})
      .finally(() => setLoadingReports(false));
  };

  const loadDashboard = () => {
    if (!topicId) return;
    setLoadingDashboard(true);
    getDashboard(topicId)
      .then((res) => {
        const payload = res.data;
        // API returns {topic_id, dashboard: {...}} — unwrap the nested dashboard
        const dash = payload && typeof payload === 'object' && payload.dashboard ? payload.dashboard : payload;
        setDashboard(dash);
      })
      .catch(() => setDashboard(null))
      .finally(() => setLoadingDashboard(false));
  };

  const loadDashboardSources = () => {
    if (!topicId) return;
    setLoadingDashboardSources(true);
    getDashboardSources(topicId)
      .then((res) => setDashboardSources(Array.isArray(res.data?.sources) ? res.data.sources : res.data || []))
      .catch(() => setDashboardSources([]))
      .finally(() => setLoadingDashboardSources(false));
  };

  const openSourceDrawer = async (source: any) => {
    setSelectedSource(source);
    setSourceDetailContent(source);
    setSourceDrawerOpen(true);
    const sourceId = source?.id || source?.source_id || source?.url || source?.title;
    if (!topicId || !sourceId) return;
    setLoadingSourceDetail(true);
    try {
      const res = await getDashboardSource(topicId, String(sourceId));
      const detail = res.data?.source || res.data?.detail || res.data || source;
      setSourceDetailContent(detail);
    } catch {
      // keep drawer usable with the list payload when detail lookup fails
      setSourceDetailContent(source);
    } finally {
      setLoadingSourceDetail(false);
    }
  };

  const clearUploads = () => {
    setUploadedFiles([]);
    setPreviewFile(null);
  };

  const handleAnalyze = (forceRefresh = false) => {
    if (!topicId || analyzing) return;
    if (isCustom && !customTitle.trim()) {
      message.warning('请输入报告标题（系统将据此进行 Grok + 搜索工具 + 外部数据联合分析）');
      return;
    }
    setAnalyzing(true);
    setStreamContent('');
    setAnalysisResult(null);

    forceRefreshRef.current = forceRefresh;
    streamRef.current = streamAnalysis(
      topicId,
      selectedModel || undefined,
      (text) => setStreamContent((prev) => prev + text),
      (data) => {
        setAnalyzing(false);
        const normalized = {
          ...data,
          created_at: data?.created_at || new Date().toISOString(),
        };
        setAnalysisResult(normalized);
        loadDashboard();
        clearUploads();
        message.success(forceRefreshRef.current ? '已重新分析并更新当日缓存' : '分析完成，已清空本次上传文件');
      },
      (error) => {
        setAnalyzing(false);
        clearUploads();
        message.error(`分析失败: ${error}`);
      },
      isCustom ? customTitle.trim() : undefined,
      socialUpdatesLimit,
      forceRefresh,
    );
  };

  const handleGenerateReport = async () => {
    if (!analysisResult?.id) {
      message.warning('请先完成分析');
      return;
    }
    try {
      const res = await generateReport(analysisResult.id);
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `BYD_${isCustom ? customTitle : topic?.name || 'report'}_${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      message.success('报告已导出');
    } catch {
      message.error('报告导出失败');
    }
  };

  const handlePromptSaved = (newPrompt: string) => {
    if (topic) setTopic({ ...topic, prompt: newPrompt });
    setPromptEditorOpen(false);
    message.success('提示词已更新');
  };

  const handleFileUpload = async (file: any) => {
    try {
      const data = await uploadReferenceFile(topicId || '', file);
      setUploadedFiles((prev) => [
        ...prev,
        {
          uid: file.uid,
          name: data.name || file.name,
          status: 'done',
          url: data.url || '',
          content_type: data.content_type || file.type,
          size: data.size || file.size,
          storage_path: data.storage_path || '',
          resize_meta: data.resize_meta,
          local: data.local,
        },
      ]);
      message.success(`已上传参考文件：${file.name}`);
    } catch {
      setUploadedFiles((prev) => [
        ...prev,
        {
          uid: file.uid,
          name: file.name,
          status: 'done',
          url: '',
          content_type: file.type,
          size: file.size,
          note: '上传失败，已作为本地参考文件保留',
        },
      ]);
      message.warning(`参考文件 ${file.name} 上传失败，将仅作为本地参考素材使用`);
    }
    return false;
  };

  const removeUploadedFile = (uid: string) => {
    setUploadedFiles((prev) => prev.filter((item) => item.uid !== uid));
  };

  const socialUpdates = useMemo(() => {
    const content = analysisResult?.content || '';
    const marker = '【社交媒体最新信息】';
    const idx = content.indexOf(marker);
    if (idx === -1) return [];
    let section = content.slice(idx + marker.length).trim();
    const nextMarkers = ['【国家覆盖】', '【引用备注】', '【参考文献】'];
    for (const m of nextMarkers) {
      const pos = section.indexOf(m);
      if (pos !== -1) section = section.slice(0, pos).trim();
    }
    const isRealUrl = (url: string) => {
      const lowered = url.toLowerCase();
      if (/(example|placeholder|dummy|fake|\/video\/example|\/post\/example|\/watch\/example)/i.test(lowered)) return false;
      if (/^https?:\/\/(www\.)?(x|twitter|tiktok|youtube|instagram|facebook|reddit|linkedin)\.com\/?$/i.test(lowered)) return false;
      let parsed: URL;
      try {
        parsed = new URL(url);
      } catch {
        return false;
      }
      const host = parsed.hostname.replace(/^www\./, '').toLowerCase();
      const path = parsed.pathname.replace(/^\/+|\/+$/g, '');
      if (!host || !path) return false;
      if (host === 'x.com' || host === 'twitter.com') {
        const parts = path.split('/');
        const statusId = parts[2] || '';
        if (parts.length < 3 || parts[1].toLowerCase() !== 'status') return false;
        if (!/^\d{15,22}$/.test(statusId)) return false;
        if (statusId === '1808123456789123456' || /(123456|234567|345678|456789|567890|678901|789012|890123)/.test(statusId)) return false;
      }
      if (host === 'tiktok.com') {
        const parts = path.split('/');
        const videoId = parts[2] || '';
        if (parts.length < 3 || !parts[0].startsWith('@') || parts[1].toLowerCase() !== 'video') return false;
        if (!/^\d{17,22}$/.test(videoId)) return false;
        if (videoId === '1234567890' || /(1234567890|0123456789|9876543210)/.test(videoId)) return false;
      }
      if (host === 'facebook.com') {
        if (/(posts|videos|photos)\/abc\d+/i.test(path)) return false;
        if (/(posts|videos|photos)\//i.test(path)) {
          const tail = path.split('/').filter(Boolean).pop() || '';
          if (!/^\d{8,}$/.test(tail)) return false;
        }
      }
      return true;
    };
    return section
      .split('\n')
      .map((line: string) => line.trim())
      .filter((line: string) => {
        if (!line) return false;
        const urlMatch = line.match(/https?:\/\/[^\s)\]}]+/i);
        if (!urlMatch) return false;
        return isRealUrl(urlMatch[0].replace(/[.,，。；;:]+$/, ''));
      });
  }, [analysisResult]);

  const dashboardData = analysisResult?.dashboard ?? dashboard;
  const dashboardKpis = dashboardData?.kpis || dashboardData?.cards || dashboardData?.metrics;
  const hasDashboardData = Boolean(
    dashboardData && (
      (Array.isArray(dashboardKpis) && dashboardKpis.length > 0) ||
      (dashboardKpis && typeof dashboardKpis === 'object' && Object.keys(dashboardKpis).length > 0)
    )
  );
  const showDashboardCard = hasDashboardData || loadingDashboard;
  const dashboardSourceList = useMemo(() => {
    const candidates = [
      dashboardData?.sources,
      dashboardData?.top_sources,
      dashboardData?.topSources,
      dashboardData?.source_list,
      dashboardSources,
    ];
    for (const candidate of candidates) {
      if (Array.isArray(candidate) && candidate.length > 0) return candidate;
    }
    return [];
  }, [dashboardData, dashboardSources]);
  const showSourceCard = dashboardSourceList.length > 0 || loadingDashboardSources;
  const dashboardTrendData = useMemo(() => {
    const raw = dashboardData?.trend || dashboardData?.trends || dashboardData?.mentions_reach_trend || dashboardData?.mentionsReachTrend || dashboardData?.chart_data?.trend;
    const rows = Array.isArray(raw)
      ? raw
      : raw && typeof raw === 'object'
        ? Object.entries(raw as Record<string, any>).map(([date, value]) => (value && typeof value === 'object' ? { date, ...value } : { date, mentions: value }))
        : [];
    return rows
      .map((item: any, index: number) => ({
        date: item?.date || item?.label || `P${index + 1}`,
        mentions: Number(item?.mentions ?? item?.count ?? item?.value ?? item?.sources ?? 0),
        reach: Number(item?.reach ?? item?.views ?? item?.impressions ?? item?.engagement ?? 0),
      }))
      .filter((item) => item.date && (Number.isFinite(item.mentions) || Number.isFinite(item.reach)));
  }, [dashboardData]);
  const countryCoverageData = useMemo(() => {
    const raw = dashboardData?.country_coverage || dashboardData?.countryCoverage || dashboardData?.countries || dashboardData?.coverage_by_country || dashboardData?.top_countries || dashboardData?.country_count;
    const rows = Array.isArray(raw)
      ? raw
      : raw && typeof raw === 'object'
        ? Object.entries(raw as Record<string, any>).map(([country, value]) => (value && typeof value === 'object' ? { country, ...value } : { country, coverage: value }))
        : [];
    return rows
      .map((item: any, index: number) => ({
        country: String(item?.country || item?.name || item?.label || `Country ${index + 1}`),
        value: Number(item?.coverage ?? item?.count ?? item?.value ?? item?.sources ?? item?.mentions ?? 0),
      }))
      .filter((item) => item.country && Number.isFinite(item.value) && item.value > 0)
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }, [dashboardData]);
  const countryCoverageEmpty = countryCoverageData.length === 0;

  const refreshStatusText = useMemo(() => {
    if (!dashboardData) return '';
    const parts: string[] = [];
    const refreshedAt = dashboardData?.refreshed_at || dashboardData?.updated_at || dashboardData?.last_updated;
    if (refreshedAt) {
      parts.push(`刷新于 ${new Date(refreshedAt).toLocaleString('zh-CN')}`);
    }
    const refreshCount = dashboardData?.refresh_count || dashboardData?.refreshCount;
    if (refreshCount !== undefined && refreshCount !== null) {
      parts.push(`刷新 ${refreshCount} 次`);
    }
    const sourceCount = dashboardData?.source_count || dashboardData?.sourceCount;
    if (sourceCount !== undefined && sourceCount !== null) {
      parts.push(`来源 ${sourceCount}`);
    }
    return parts.join(' · ');
  }, [dashboardData]);

  if (!topic) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 100 }}>
        <Spin size="large" tip="加载话题..." />
      </div>
    );
  }

  return (
    <div>
      <Card style={{ marginBottom: 16, borderRadius: 12 }} bodyStyle={{ padding: '16px 20px' }}>
        <div>
          <Title level={3} style={{ marginBottom: 4 }}>
            {topic.icon} {topic.name}
          </Title>
          <Text type="secondary">{topic.description}</Text>

          {isCustom && (
            <div style={{ marginTop: 12 }}>
              <Text strong style={{ display: 'block', marginBottom: 6 }}>
                输入报告标题 *
              </Text>
              <TextArea
                value={customTitle}
                onChange={(e) => setCustomTitle(e.target.value)}
                placeholder="例如：小米SU7上市舆情分析、特斯拉FSD入华影响评估、蔚来换电模式争议..."
                rows={2}
                maxLength={200}
                showCount
                style={{ fontSize: 14 }}
              />
              <Text type="secondary" style={{ display: 'block', marginTop: 4, fontSize: 12 }}>
                标题将作为分析主题，系统会结合 Grok + 搜索工具 + 外部数据联合分析生成专业报告
              </Text>
            </div>
          )}

          <div
            style={{
              marginTop: 14,
              padding: '10px 12px',
              borderRadius: 10,
              background: 'rgba(24, 144, 255, 0.06)',
              border: '1px solid rgba(24, 144, 255, 0.18)',
            }}
          >
            <Space wrap align="center" size={[8, 8]}>
              <Text strong style={{ fontSize: 13 }}>分析控制台</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>模型</Text>
              <Select
                size="small"
                value={selectedModel}
                onChange={setSelectedModel}
                style={{ width: 260 }}
                placeholder="选择模型"
                options={models.map((m) => ({
                  value: m.id,
                  label: `${m.name} - ${m.description}`,
                }))}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>社媒</Text>
              <Select
                size="small"
                value={socialUpdatesLimit}
                onChange={setSocialUpdatesLimit}
                style={{ width: 130 }}
                options={socialLimitOptions.map((count) => ({ value: count, label: `${count} 条` }))}
              />
              <Upload
                beforeUpload={handleFileUpload}
                multiple
                showUploadList={false}
                accept=".jpg,.jpeg,.png,.pdf,.doc,.docx,.txt,.csv,.xls,.xlsx,.json"
              >
                <Button size="small" icon={<UploadOutlined />}>上载参考文件</Button>
              </Upload>
              <Button size="small" icon={<EditOutlined />} onClick={() => setPromptEditorOpen(true)}>
                编辑提示词
              </Button>
              <Button type="primary" size="small" icon={<PlayCircleOutlined />} onClick={() => handleAnalyze(false)} loading={analyzing}>
                开始分析
              </Button>
              <Button size="small" danger icon={<ReloadOutlined />} onClick={() => handleAnalyze(true)} loading={analyzing}>
                重新分析
              </Button>
              {refreshStatusText ? (
                <Tag color="geekblue" style={{ marginRight: 0 }}>
                  {refreshStatusText}
                </Tag>
              ) : null}
              {uploadedFiles.length > 0 && <Tag color="processing">参考文件 {uploadedFiles.length}</Tag>}
            </Space>
          </div>
        </div>
      </Card>

      {uploadedFiles.length > 0 && (
        <Card title="参考素材" style={{ marginBottom: 24, borderRadius: 12 }}>
          <List
            dataSource={uploadedFiles}
            renderItem={(item) => (
              <List.Item
                actions={[
                  (item.content_type || '').startsWith('image/') ? (
                    <Button type="link" onClick={() => setPreviewFile(item)}>预览图片</Button>
                  ) : null,
                  <Button type="link" danger icon={<DeleteOutlined />} onClick={() => removeUploadedFile(item.uid)}>
                    删除
                  </Button>,
                ].filter(Boolean)}
              >
                <List.Item.Meta
                  title={<Space wrap><span>{item.name}</span>{item.local ? <Tag color="green">本地</Tag> : null}</Space>}
                  description={
                    <Space direction="vertical" size={2}>
                      <Text type="secondary">{item.content_type || '未知类型'}{item.size ? ` · ${(item.size / 1024).toFixed(1)} KB` : ''}</Text>
                      {item.url ? <a href={item.url} target="_blank" rel="noreferrer">打开链接</a> : null}
                      {item.storage_path ? <Text type="secondary">{item.storage_path}</Text> : null}
                      {item.resize_meta ? <Text type="secondary">压缩：{JSON.stringify(item.resize_meta)}</Text> : null}
                      {item.note ? <Text type="warning">{item.note}</Text> : null}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      )}

      {previewFile && (
        <Card
          title={`图片预览：${previewFile.name}`}
          style={{ marginBottom: 24, borderRadius: 12 }}
          extra={<Button onClick={() => setPreviewFile(null)}>关闭预览</Button>}
        >
          <img
            src={previewFile.url}
            alt={previewFile.name}
            style={{ maxWidth: '100%', maxHeight: 480, display: 'block', borderRadius: 8 }}
          />
          <Divider />
          <Space direction="vertical" size={4}>
            <Text type="secondary">{previewFile.storage_path}</Text>
            {previewFile.resize_meta ? <Text type="secondary">预压缩：{JSON.stringify(previewFile.resize_meta)}</Text> : null}
          </Space>
        </Card>
      )}

      <SourceDetailDrawer
        open={sourceDrawerOpen}
        onClose={() => setSourceDrawerOpen(false)}
        loading={loadingSourceDetail}
        source={sourceDetailContent || selectedSource}
      />

      <Tabs
        defaultActiveKey="analysis"
        items={[
          {
            key: 'analysis',
            label: '分析结果',
            children: (
              <div>
                {analyzing && (
                  <Card style={{ marginBottom: 24, borderRadius: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                      <Spin size="small" />
                      <Text>正在分析中，内容将实时展示在下方...</Text>
                    </div>
                    <StreamingContent content={streamContent} />
                  </Card>
                )}
                {analysisResult && !analyzing && (
                  <>
                    <Card style={{ marginBottom: 24, borderRadius: 12 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
                        <Space wrap>
                          <Tag color="blue">{analysisResult.model}</Tag>
                          <Tag color="purple">社交媒体最新信息 {socialUpdatesLimit} 条</Tag>
                          <Text type="secondary">
                            分析时间: {analysisResult.created_at ? new Date(analysisResult.created_at).toLocaleString('zh-CN') : new Date().toLocaleString('zh-CN')}
                          </Text>
                        </Space>
                        <Space wrap>
                          <Button icon={<FilePdfOutlined />} onClick={handleGenerateReport}>导出 PDF</Button>
                        </Space>
                      </div>
                    </Card>

                    <div style={{ marginBottom: 24 }}>
                      <MentionsReachTrendChart data={dashboardTrendData} loading={loadingDashboard} />
                    </div>

                    <Collapse
                      style={{ marginBottom: 24, borderRadius: 12 }}
                      defaultActiveKey={["structured-insights", "report-full"]}
                      items={[
                        {
                          key: 'structured-insights',
                          label: (
                            <Space>
                              <Text strong>结构化洞察</Text>
                              {analysisResult.sentiment ? <Tag color="blue">情绪分布</Tag> : null}
                              <Tag color="purple">社交媒体 {socialUpdates.length > 0 ? `${socialUpdates.length} 条` : '暂无'}</Tag>
                              <Tag color="cyan">国家覆盖</Tag>
                            </Space>
                          ),
                          children: (
                            <Space direction="vertical" size={16} style={{ width: '100%' }}>
                              {analysisResult.sentiment ? <SentimentChart sentiment={analysisResult.sentiment} /> : null}
                              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 0.8fr)', gap: 12, alignItems: 'stretch' }}>
                                <div style={{ minWidth: 0 }}>
                                  <CountryCoverageChart
                                    title="Countries with Most Coverage"
                                    subtitle="Top countries by coverage volume"
                                    data={countryCoverageData}
                                    loading={loadingDashboard}
                                  />
                                  {countryCoverageEmpty && dashboardData?.country_coverage ? (
                                    <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                                      后端返回了国家覆盖，但未能提取出有效数值；请检查国家覆盖章节是否包含国家名与热度计数。
                                    </Text>
                                  ) : null}
                                </div>
                                <Card size="small" style={{ borderRadius: 12, overflow: 'hidden', height: '100%' }} bodyStyle={{ padding: 12, height: '100%', display: 'flex', flexDirection: 'column' }}>
                                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 10 }}>
                                    <div style={{ minWidth: 0 }}>
                                      <Text strong style={{ display: 'block', fontSize: 13, lineHeight: 1.2 }}>社交媒体最新信息</Text>
                                      <Text type="secondary" style={{ fontSize: 11 }}>
                                        {socialUpdates.length > 0 ? `${socialUpdates.length} 条动态` : '暂无实时动态，显示说明占位'}
                                      </Text>
                                    </div>
                                    <Tag color="purple">Social</Tag>
                                  </div>
                                  <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
                                    <Collapse
                                      defaultActiveKey={['social-list']}
                                      items={[
                                        {
                                          key: 'social-list',
                                          label: `最新动态 ${socialUpdates.length > 0 ? `${socialUpdates.length} 条` : '占位预览'}`,
                                          children: socialUpdates.length > 0 ? (
                                            <List
                                              size="small"
                                              dataSource={socialUpdates}
                                              renderItem={(item) => {
                                                const text = String(item || '').trim();
                                                const urlMatch = text.match(/https?:\/\/[^\s)\]}]+/i);
                                                if (!urlMatch) return null;
                                                const url = urlMatch[0].replace(/[.,，。；;:]+$/, '');
                                                const lowered = url.toLowerCase();
                                                if (/\b(example|placeholder|dummy|fake|tiktok.com\/[^\s]*\/example)\b/i.test(url)) return null;
                                                if (/x\.com\/BYDGlobal\/status\/1808123456789123456/i.test(url)) return null;
                                                if (/facebook\.com\/groups\/evowners\/posts\/abc123/i.test(url)) return null;
                                                if (/tiktok\.com\/@techinsiderev\/video\/1234567890/i.test(url)) return null;
                                                if (/(123456|234567|345678|456789|567890|678901|789012|890123)/.test(lowered)) return null;
                                                const label = text.replace(urlMatch[0], '').replace(/^[-•*\s]+/, '').trim() || url;
                                                return (
                                                  <List.Item>
                                                    <a href={url} target="_blank" rel="noreferrer">{label}</a>
                                                  </List.Item>
                                                );
                                              }}
                                            />
                                          ) : (
                                            <Paragraph style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}>
                                              {(() => {
                                                const content = analysisResult?.content || '';
                                                const marker = '【社交媒体最新信息】';
                                                const idx = content.indexOf(marker);
                                                if (idx === -1) return '报告中未找到【社交媒体最新信息】章节。';
                                                return content.slice(idx + marker.length).trim() || '该章节为空。';
                                              })()}
                                            </Paragraph>
                                          ),
                                        },
                                      ]}
                                    />
                                  </div>
                                </Card>
                              </div>
                            </Space>
                          ),
                        },
                        {
                          key: 'report-full',
                          label: <Text strong>分析报告全文</Text>,
                          children: <StreamingContent content={analysisResult.content} />,
                        },
                      ]}
                    />
                  </>
                )}
                {!analyzing && !analysisResult && (
                  <Card style={{ borderRadius: 12, textAlign: 'center', padding: '60px 0' }}>
                    <Empty
                      description={
                        <Text type="secondary" style={{ fontSize: 16 }}>
                          {isCustom
                            ? '输入标题后点击"开始分析"，系统将基于 Grok + 搜索工具 + 外部数据联合分析生成专业报告'
                            : '点击"开始分析"按钮，系统将通过 Grok + 搜索工具 + 外部数据联合分析进行深度舆情分析'}
                        </Text>
                      }
                    >
                      <Button type="primary" size="large" icon={<PlayCircleOutlined />} onClick={() => handleAnalyze(false)}>开始分析</Button>
                    </Empty>
                  </Card>
                )
              }
            </div>
          ),
          },
          {
            key: 'reports',
            label: (
              <Space>
                <FilePdfOutlined />
                历史报告
                {reports.length > 0 && <Tag>{reports.length}</Tag>}
              </Space>
            ),
            children: <ReportList reports={reports} loading={loadingReports} onRefresh={loadReports} />,
          },
        ]}
      />
      <PromptEditor
        open={promptEditorOpen}
        topicId={topicId || ''}
        currentPrompt={topic.prompt}
        onClose={() => setPromptEditorOpen(false)}
        onSaved={handlePromptSaved}
      />
    </div>
  );
};

export default TopicPage;
