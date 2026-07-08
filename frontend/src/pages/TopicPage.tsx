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
import { useTranslation } from '../i18n/LanguageContext';
import {
  getTopic, streamAnalysis, generateReport, listReports, uploadReferenceFile, getDashboard, getDashboardSources, getAnalysisHistory,
} from '../services/api';
import { TOPIC_I18N_KEYS, OVERSEAS_TOPICS } from '../constants/topicConfig';
import { isRealSocialUrl } from '../utils/urlValidator';
import { extractTrendFromContent, extractCountryCoverageFromContent } from '../utils/contentExtractors';

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
  const { t, language } = useTranslation();

  const reportLanguageOptions = [
    { value: 'zh', label: t('console.reportLanguage.zh') },
    { value: 'en', label: t('console.reportLanguage.en') },
  ];

  // 跟随界面语言自动切换报告语言
  useEffect(() => {
    setReportLanguage(language === 'en' ? 'en' : 'zh');
  }, [language]);

  const targetRegionOptions = [
    { value: 'global', label: t('console.targetRegion.global') },
    { value: 'europe', label: t('console.targetRegion.europe') },
    { value: 'northAmerica', label: t('console.targetRegion.northAmerica') },
    { value: 'middleEast', label: t('console.targetRegion.middleEast') },
    { value: 'southeastAsia', label: t('console.targetRegion.southeastAsia') },
    { value: 'latinAmerica', label: t('console.targetRegion.latinAmerica') },
    { value: 'oceania', label: t('console.targetRegion.oceania') },
  ];
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
  const [reportLanguage, setReportLanguage] = useState<string>('zh');
  const [targetRegion, setTargetRegion] = useState<string>('global');
  const streamRef = useRef<any>(null);
  const forceRefreshRef = useRef(false);

  const isCustom = topicId === 'custom-report';

  // Set default report language based on topic
  useEffect(() => {
    if (topicId) {
      //海外主题默认英文
      if (OVERSEAS_TOPICS.includes(topicId)) {
        setReportLanguage('en');
      } else {
        setReportLanguage('zh');
      }
    }
  }, [topicId]);

  useEffect(() => {
    if (!topicId) return;
    getTopic(topicId).then((res) => setTopic(res.data));
    setModels([
      { id: 'xai.grok-4.20-multi-agent-0309', name: 'Grok 4.20', description: language === 'zh' ? '复杂分析 / 默认' : 'Deep Analysis / Default' },
      { id: 'xai.grok-4.3', name: 'Grok 4.3', description: language === 'zh' ? '更快 / 通用分析' : 'Faster / General Analysis' },
    ]);
    setSelectedModel('xai.grok-4.20-multi-agent-0309');
    loadReports();
    loadDashboard();
    loadDashboardSources();
    loadLatestAnalysis();
    setCustomTitle('');
    setUploadedFiles([]);
    setStreamContent('');
    setPreviewFile(null);
    setSocialUpdatesLimit(10);
  }, [topicId, language]);

  const loadReports = () => {
    if (!topicId) return;
    setLoadingReports(true);
    listReports(topicId)
      .then((res) => setReports(res.data.reports))
      .catch(() => {})
      .finally(() => setLoadingReports(false));
  };

  const loadLatestAnalysis = () => {
    if (!topicId) return;
    getAnalysisHistory(topicId)
      .then((res) => {
        const results = res.data.results || [];
        if (results.length > 0) {
          // 获取最新的分析结果（按时间排序，第一个是最新的）
          const latest = results[0];
          setAnalysisResult(latest);
          // Use dashboard data from history response if available
          if (res.data.dashboard) {
            setDashboard(res.data.dashboard);
          }
        } else {
          setAnalysisResult(null);
        }
      })
      .catch(() => setAnalysisResult(null));
  };

  const loadDashboard = () => {
    if (!topicId) return;
    setLoadingDashboard(true);
    getDashboard(topicId)
      .then((res) => {
        const payload = res.data;
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
      message.warning(t('console.customTitleHint'));
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
        message.success(forceRefreshRef.current ? t('analysis.refreshed') : t('analysis.completed'));
      },
      (error) => {
        setAnalyzing(false);
        clearUploads();
        message.error(`${t('analysis.failed')}: ${error}`);
      },
      isCustom ? customTitle.trim() : undefined,
      socialUpdatesLimit,
      forceRefresh,
      reportLanguage,
      targetRegion,
    );
  };

  const handleGenerateReport = async () => {
    if (!analysisResult?.id) {
      message.warning(t('empty.startAnalysisButton'));
      return;
    }
    try {
      const res = await generateReport(analysisResult.id);
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `AUTO_GEO_${isCustom ? customTitle : topic?.name || 'report'}_${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      message.success(t('success.reportGenerated'));
    } catch {
      message.error(t('error.reportGenerationFailed'));
    }
  };

  const handlePromptSaved = (newPrompt: string) => {
    if (topic) setTopic({ ...topic, prompt: newPrompt });
    setPromptEditorOpen(false);
    message.success(t('success.promptUpdated'));
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
      message.success(`${t('reference.uploadSuccess')}：${file.name}`);
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
          note: t('reference.uploadFailed'),
        },
      ]);
      message.warning(t('reference.uploadFailedWarning'));
    }
    return false;
  };

  const removeUploadedFile = (uid: string) => {
    setUploadedFiles((prev) => prev.filter((item) => item.uid !== uid));
  };

  const dashboardData = analysisResult?.dashboard ?? dashboard;
  const dashboardKpis = dashboardData?.kpis || dashboardData?.cards || dashboardData?.metrics;
  const hasDashboardData = Boolean(
    dashboardData && (
      (Array.isArray(dashboardKpis) && dashboardKpis.length > 0) ||
      (dashboardKpis && typeof dashboardKpis === 'object' && Object.keys(dashboardKpis).length > 0)
    )
  );
  const showDashboardCard = hasDashboardData || loadingDashboard;

  const socialUpdates = useMemo(() => {
    const sourceCandidates = [
      dashboardData?.sources,
      dashboardData?.top_sources,
      dashboardData?.topSources,
      dashboardData?.source_list,
      dashboardSources,
    ];
    const dashboardSocialSources = sourceCandidates.find((candidate) => Array.isArray(candidate) && candidate.length > 0) || [];
    const fromDashboard = dashboardSocialSources
      .filter((item: any) => String(item?.source_type || item?.type || '').toLowerCase().includes('social'))
      .map((item: any) => {
        const url = String(item?.url || '').replace(/[.,，。；;:]+$/, '');
        const text = String(item?.summary || item?.title || url).trim();
        return url && isRealSocialUrl(url) ? `${text} ${url}` : '';
      })
      .filter(Boolean);
    if (fromDashboard.length > 0) return fromDashboard;

    const content = analysisResult?.content || '';
    // Support both Chinese and English markers
    const socialMarkers = ['【社交媒体最新信息】', '【Latest Social Updates】', '[Latest Social Updates]', '## Latest Social Updates'];
    const endMarkers = ['【国家覆盖】', '【引用备注】', '【参考文献】', '[Country Coverage]', '[Citation Notes]', '[References]', '## Country Coverage', '## Citation Notes', '## References'];

    let section = '';
    for (const marker of socialMarkers) {
      const idx = content.indexOf(marker);
      if (idx !== -1) {
        section = content.slice(idx + marker.length).trim();
        break;
      }
    }
    if (!section) return [];

    for (const m of endMarkers) {
      const pos = section.indexOf(m);
      if (pos !== -1) section = section.slice(0, pos).trim();
    }
    return section
      .split('\n')
      .map((line: string) => line.trim())
      .filter((line: string) => {
        if (!line) return false;
        const urlMatch = line.match(/https?:\/\/[^\s)\]}]+/i);
        if (!urlMatch) return false;
        return isRealSocialUrl(urlMatch[0].replace(/[.,，。；;:]+$/, ''));
      });
  }, [analysisResult, dashboardData, dashboardSources]);

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
  // Fallback: extract trend data from analysis content when dashboard data is empty
  const dashboardTrendData = useMemo(() => {
    const raw = dashboardData?.trend || dashboardData?.trends || dashboardData?.mentions_reach_trend || dashboardData?.mentionsReachTrend || dashboardData?.chart_data?.trend;
    const rows = Array.isArray(raw)
      ? raw
      : raw && typeof raw === 'object'
        ? Object.entries(raw as Record<string, any>).map(([date, value]) => (value && typeof value === 'object' ? { date, ...value } : { date, mentions: value }))
        : [];
    const fromDashboard = rows
      .map((item: any, index: number) => ({
        date: item?.date || item?.label || `P${index + 1}`,
        mentions: Number(item?.mentions ?? item?.count ?? item?.value ?? item?.sources ?? 0),
        reach: Number(item?.reach ?? item?.views ?? item?.impressions ?? item?.engagement ?? 0),
      }))
      .filter((item) => item.date && (Number.isFinite(item.mentions) || Number.isFinite(item.reach)));
    // Fallback: extract from analysis content if dashboard data is empty
    if (fromDashboard.length === 0 && analysisResult?.content) {
      return extractTrendFromContent(analysisResult.content);
    }
    return fromDashboard;
  }, [dashboardData, analysisResult]);
  const countryCoverageData = useMemo(() => {
    const raw = dashboardData?.country_coverage || dashboardData?.countryCoverage || dashboardData?.countries || dashboardData?.coverage_by_country || dashboardData?.top_countries || dashboardData?.country_count;
    const rows = Array.isArray(raw)
      ? raw
      : raw && typeof raw === 'object'
        ? Object.entries(raw as Record<string, any>).map(([country, value]) => (value && typeof value === 'object' ? { country, ...value } : { country, coverage: value }))
        : [];
    const fromDashboard = rows
      .map((item: any, index: number) => ({
        country: String(item?.country || item?.name || item?.label || `Country ${index + 1}`),
        value: Number(item?.coverage ?? item?.count ?? item?.value ?? item?.sources ?? item?.mentions ?? 0),
      }))
      .filter((item) => item.country && Number.isFinite(item.value) && item.value > 0)
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
    // Fallback: extract from analysis content if dashboard data is empty
    if (fromDashboard.length === 0 && analysisResult?.content) {
      return extractCountryCoverageFromContent(analysisResult.content);
    }
    return fromDashboard;
  }, [dashboardData, analysisResult]);
  const countryCoverageEmpty = countryCoverageData.length === 0;

  const reportOverview = useMemo(() => {
    const content = String(analysisResult?.content || '').trim();
    if (!content) return [];

    const cleanLine = (line: string) => line
      .replace(/^[-*•\d.、\s]+/, '')
      .replace(/[`*_>#]/g, '')
      .trim();

    const extractOverallSummary = () => {
      const lines = content.split('\n').map(cleanLine).filter(Boolean);
      const sectionCandidates = lines.filter((line) => {
        if (line.startsWith('【')) return true;
        if (/^#{1,3}\s+/.test(line)) return true;
        return false;
      });
      const startIndex = sectionCandidates.length > 0 ? lines.findIndex((line) => sectionCandidates.includes(line)) : -1;
      const head = startIndex > 0 ? lines.slice(0, startIndex) : lines.slice(0, Math.min(12, lines.length));
      const meaningful = head
        .filter((line) => line && !line.startsWith('{') && !line.startsWith('}') && !line.startsWith('```'))
        .filter((line) => !/^\"?(positive|neutral|negative)\"?\s*[:：]/i.test(line));
      const picked = meaningful.slice(0, 6).join('；');
      return picked || lines.slice(0, 6).join('；');
    };

    const summary = extractOverallSummary();
    return summary ? [{ title: t('report.overview'), summary }] : [];
  }, [analysisResult, t]);

  const refreshStatusText = useMemo(() => {
    if (!dashboardData) return '';
    const parts: string[] = [];
    const refreshedAt = dashboardData?.refreshed_at || dashboardData?.updated_at || dashboardData?.last_updated;
    if (refreshedAt) {
      parts.push(`${language === 'zh' ? '刷新于' : 'Refreshed at'} ${new Date(refreshedAt).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US')}`);
    }
    const refreshCount = dashboardData?.refresh_count || dashboardData?.refreshCount;
    if (refreshCount !== undefined && refreshCount !== null) {
      parts.push(`${language === 'zh' ? '刷新' : 'Refreshed'} ${refreshCount} ${language === 'zh' ? '次' : 'times'}`);
    }
    const sourceCount = dashboardData?.source_count || dashboardData?.sourceCount;
    if (sourceCount !== undefined && sourceCount !== null) {
      parts.push(`${language === 'zh' ? '来源' : 'Sources'} ${sourceCount}`);
    }
    return parts.join(' · ');
  }, [dashboardData, language]);

  if (!topic) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 100 }}>
        <Spin size="large" tip={t('app.loading')} />
      </div>
    );
  }

  return (
    <div>
      <Card style={{ marginBottom: 16, borderRadius: 12 }} bodyStyle={{ padding: '16px 20px' }}>
        <div>
          <Title level={3} style={{ marginBottom: 4 }}>
            {topic.icon} {TOPIC_I18N_KEYS[topicId || ''] ? t(TOPIC_I18N_KEYS[topicId || ''].name) : topic.name}
          </Title>
          <Text type="secondary">{TOPIC_I18N_KEYS[topicId || ''] ? t(TOPIC_I18N_KEYS[topicId || ''].description) : topic.description}</Text>

          {isCustom && (
            <div style={{ marginTop: 12 }}>
              <Text strong style={{ display: 'block', marginBottom: 6 }}>
                {t('console.customTitle')}
              </Text>
              <TextArea
                value={customTitle}
                onChange={(e) => setCustomTitle(e.target.value)}
                placeholder={t('console.customTitlePlaceholder')}
                rows={2}
                maxLength={200}
                showCount
                style={{ fontSize: 14 }}
              />
              <Text type="secondary" style={{ display: 'block', marginTop: 4, fontSize: 12 }}>
                {t('console.customTitleHint')}
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
              <Text strong style={{ fontSize: 13 }}>{t('console.title')}</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>{t('console.model')}</Text>
              <Select
                size="small"
                value={selectedModel}
                onChange={setSelectedModel}
                style={{ width: 260 }}
                placeholder={t('console.modelSelect')}
                options={models.map((m) => ({
                  value: m.id,
                  label: `${m.name} - ${m.description}`,
                }))}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>{t('console.socialLimit')}</Text>
              <Select
                size="small"
                value={socialUpdatesLimit}
                onChange={setSocialUpdatesLimit}
                style={{ width: 130 }}
                options={socialLimitOptions.map((count) => ({ value: count, label: `${count} ${t('console.socialLimitUnit')}` }))}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>{t('console.reportLanguage')}</Text>
              <Select
                size="small"
                value={reportLanguage}
                onChange={setReportLanguage}
                style={{ width: 140 }}
                options={reportLanguageOptions}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>{t('console.targetRegion')}</Text>
              <Select
                size="small"
                value={targetRegion}
                onChange={setTargetRegion}
                style={{ width: 120 }}
                options={targetRegionOptions}
              />
              <Upload
                beforeUpload={handleFileUpload}
                multiple
                showUploadList={false}
                accept=".jpg,.jpeg,.png,.pdf,.doc,.docx,.txt,.csv,.xls,.xlsx,.json"
              >
                <Button size="small" icon={<UploadOutlined />}>{t('console.uploadFile')}</Button>
              </Upload>
              <Button size="small" icon={<EditOutlined />} onClick={() => setPromptEditorOpen(true)}>
                {t('console.editPrompt')}
              </Button>
              <Button type="primary" size="small" icon={<PlayCircleOutlined />} onClick={() => handleAnalyze(false)} loading={analyzing}>
                {t('console.startAnalysis')}
              </Button>
              <Button size="small" danger icon={<ReloadOutlined />} onClick={() => handleAnalyze(true)} loading={analyzing}>
                {t('console.reAnalyze')}
              </Button>
              {refreshStatusText ? (
                <Tag color="geekblue" style={{ marginRight: 0 }}>
                  {refreshStatusText}
                </Tag>
              ) : null}
              {uploadedFiles.length > 0 && <Tag color="processing">{t('reference.title')} {uploadedFiles.length}</Tag>}
            </Space>
          </div>
        </div>
      </Card>

      {uploadedFiles.length > 0 && (
        <Card title={t('reference.title')} style={{ marginBottom: 24, borderRadius: 12 }}>
          <List
            dataSource={uploadedFiles}
            renderItem={(item) => (
              <List.Item
                actions={[
                  (item.content_type || '').startsWith('image/') ? (
                    <Button type="link" onClick={() => setPreviewFile(item)}>{t('reference.preview')}</Button>
                  ) : null,
                  <Button type="link" danger icon={<DeleteOutlined />} onClick={() => removeUploadedFile(item.uid)}>
                    {t('reference.delete')}
                  </Button>,
                ].filter(Boolean)}
              >
                <List.Item.Meta
                  title={<Space wrap><span>{item.name}</span>{item.local ? <Tag color="green">{t('reference.local')}</Tag> : null}</Space>}
                  description={
                    <Space direction="vertical" size={2}>
                      <Text type="secondary">{item.content_type || t('reference.unknownType')}{item.size ? ` · ${(item.size / 1024).toFixed(1)} KB` : ''}</Text>
                      {item.url ? <a href={item.url} target="_blank" rel="noreferrer">{t('reference.openLink')}</a> : null}
                      {item.storage_path ? <Text type="secondary">{item.storage_path}</Text> : null}
                      {item.resize_meta ? <Text type="secondary">{t('reference.compressed')}：{JSON.stringify(item.resize_meta)}</Text> : null}
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
          title={`${t('reference.preview')}：${previewFile.name}`}
          style={{ marginBottom: 24, borderRadius: 12 }}
          extra={<Button onClick={() => setPreviewFile(null)}>{t('app.close')}</Button>}
        >
          <img
            src={previewFile.url}
            alt={previewFile.name}
            style={{ maxWidth: '100%', maxHeight: 480, display: 'block', borderRadius: 8 }}
          />
          <Divider />
          <Space direction="vertical" size={4}>
            <Text type="secondary">{previewFile.storage_path}</Text>
            {previewFile.resize_meta ? <Text type="secondary">{t('reference.compressed')}：{JSON.stringify(previewFile.resize_meta)}</Text> : null}
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
            label: t('report.title'),
            children: (
              <div>
                {analyzing && (
                  <Card style={{ marginBottom: 24, borderRadius: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                      <Spin size="small" />
                      <Text>{t('analysis.analyzing')}</Text>
                    </div>
                    <StreamingContent content={streamContent} />
                  </Card>
                )}
                {(analysisResult || dashboardData) && !analyzing && (
                  <>
                    {analysisResult && (
                      <Card style={{ marginBottom: 24, borderRadius: 12 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
                          <Space wrap>
                            <Tag color="blue">{analysisResult.model}</Tag>
                            <Tag color="purple">{t('social.title')} {socialUpdatesLimit} {t('console.socialLimitUnit')}</Tag>
                            <Text type="secondary">
                              {t('analysis.time')}: {analysisResult.created_at ? new Date(analysisResult.created_at).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US') : new Date().toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US')}
                            </Text>
                          </Space>
                          <Space wrap>
                            <Button icon={<FilePdfOutlined />} onClick={handleGenerateReport}>{t('analysis.exportPdf')}</Button>
                          </Space>
                        </div>
                      </Card>
                    )}

                    <div style={{ marginBottom: 24 }}>
                      <MentionsReachTrendChart data={dashboardTrendData} loading={loadingDashboard} />
                    </div>

                    <Collapse
                      style={{ marginBottom: 24, borderRadius: 12 }}
                      defaultActiveKey={["structured-insights", "report-overview"]}
                      activeKey={undefined}
                      items={[
                        {
                          key: 'structured-insights',
                          label: (
                            <Space>
                              <Text strong>{t('report.structuredInsights')}</Text>
                              {analysisResult?.sentiment ? <Tag color="blue">{t('insights.sentiment')}</Tag> : null}
                              <Tag color="purple">{t('insights.socialUpdates')} {socialUpdates.length > 0 ? `${socialUpdates.length} ${t('console.socialLimitUnit')}` : t('insights.noData')}</Tag>
                              <Tag color="cyan">{t('insights.countryCoverage')}</Tag>
                            </Space>
                          ),
                          children: (
                            <Space direction="vertical" size={16} style={{ width: '100%' }}>
                              {analysisResult?.sentiment ? <SentimentChart sentiment={analysisResult.sentiment} /> : null}
                              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 0.8fr)', gap: 12, alignItems: 'stretch' }}>
                                <div style={{ minWidth: 0 }}>
                                  <CountryCoverageChart
                                    title={t('countryCoverage.titleEn')}
                                    subtitle={t('countryCoverage.subtitleEn')}
                                    data={countryCoverageData}
                                    loading={loadingDashboard}
                                  />
                                  {countryCoverageEmpty && dashboardData?.country_coverage ? (
                                    <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                                      {t('countryCoverage.noData')}
                                    </Text>
                                  ) : null}
                                </div>
                                <Card size="small" style={{ borderRadius: 12, overflow: 'hidden', height: '100%' }} bodyStyle={{ padding: 12, height: '100%', display: 'flex', flexDirection: 'column' }}>
                                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 10 }}>
                                    <div style={{ minWidth: 0 }}>
                                      <Text strong style={{ display: 'block', fontSize: 13, lineHeight: 1.2 }}>{t('social.title')}</Text>
                                      <Text type="secondary" style={{ fontSize: 11 }}>
                                        {socialUpdates.length > 0 ? `${socialUpdates.length} ${t('social.count')}` : t('social.noData')}
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
                                          label: `${t('social.latestUpdates')} ${socialUpdates.length > 0 ? `${socialUpdates.length} ${t('console.socialLimitUnit')}` : t('social.placeholder')}`,
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
                                                if (/x\.com\/[A-Za-z]+Global\/status\/1808123456789123456/i.test(url)) return null;
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
                                                // Support both Chinese and English markers
                                                const socialMarkers = ['【社交媒体最新信息】', '【Latest Social Updates】', '[Latest Social Updates]', '## Latest Social Updates'];
                                                for (const marker of socialMarkers) {
                                                  const idx = content.indexOf(marker);
                                                  if (idx !== -1) {
                                                    return content.slice(idx + marker.length).trim() || t('social.noData');
                                                  }
                                                }
                                                return t('social.noUpdates');
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
                          key: 'report-overview',
                          label: <Text strong>{t('report.overview')}</Text>,
                          children: reportOverview.length > 0 ? (
                            <List
                              size="small"
                              dataSource={reportOverview}
                              renderItem={(item) => (
                                <List.Item>
                                  <List.Item.Meta
                                    title={<Text strong>{item.title}</Text>}
                                    description={<Text type="secondary">{item.summary}</Text>}
                                  />
                                </List.Item>
                              )}
                            />
                          ) : (
                            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('report.noOverview')} />
                          ),
                        },
                        {
                          key: 'report-full',
                          label: <Text strong>{t('report.fullReport')}</Text>,
                          children: <StreamingContent content={analysisResult?.content || ''} />,
                        },
                      ]}
                    />
                  </>
                )}
                {!analyzing && !analysisResult && !dashboardData && (
                  <Card style={{ borderRadius: 12, textAlign: 'center', padding: '60px 0' }}>
                    <Empty
                      description={
                        <Text type="secondary" style={{ fontSize: 16 }}>
                          {isCustom ? t('empty.startAnalysisCustom') : t('empty.startAnalysis')}
                        </Text>
                      }
                    >
                      <Button type="primary" size="large" icon={<PlayCircleOutlined />} onClick={() => handleAnalyze(false)}>{t('empty.startAnalysisButton')}</Button>
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
                {t('reports.title')}
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
