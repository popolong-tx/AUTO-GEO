import React, { useState } from 'react';
import {
  Card, Typography, Input, Button, Space, Tag, Spin, Empty, List, message, Select, Collapse,
} from 'antd';
import {
  SearchOutlined, FilePdfOutlined, GlobalOutlined,
  LinkOutlined, ClockCircleOutlined, LikeOutlined, RetweetOutlined,
  EyeOutlined, MessageOutlined, FireOutlined,
} from '@ant-design/icons';
import { useTranslation } from '../i18n/LanguageContext';
import { collectLatestInfo, exportLatestInfoPdf } from '../services/api';
import MentionsReachTrendChart from '../components/MentionsReachTrendChart';
import CountryCoverageChart from '../components/CountryCoverageChart';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const LatestInfoPage: React.FC = () => {
  const { t, language } = useTranslation();
  const [topic, setTopic] = useState('');
  const [socialLimit, setSocialLimit] = useState(10);
  const [selectedModel, setSelectedModel] = useState('xai.grok-4.20-multi-agent-0309');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [exporting, setExporting] = useState(false);

  const is_en = language === 'en';

  const handleCollect = async () => {
    if (!topic.trim()) {
      message.warning(is_en ? 'Please enter a topic' : '请输入主题');
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const res = await collectLatestInfo({
        topic: topic.trim(),
        social_updates_limit: socialLimit,
        model: selectedModel,
        language: language,
      });

      if (res.data.success) {
        setResult(res.data);
        message.success(is_en ? 'Data collection complete' : '数据采集完成');
      } else {
        message.error(is_en ? 'Collection failed' : '采集失败');
      }
    } catch (error: any) {
      message.error(error?.response?.data?.detail || (is_en ? 'Collection failed' : '采集失败'));
    } finally {
      setLoading(false);
    }
  };

  const handleExportPdf = async () => {
    if (!result?.data) return;

    setExporting(true);
    try {
      const res = await exportLatestInfoPdf({
        topic: topic.trim(),
        data: result.data,
        language: language,
      });

      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `LatestInfo_${topic.replace(/\s+/g, '_')}_${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      message.success(is_en ? 'PDF exported successfully' : 'PDF导出成功');
    } catch (error) {
      message.error(is_en ? 'PDF export failed' : 'PDF导出失败');
    } finally {
      setExporting(false);
    }
  };

  // Prepare trend data for chart
  const trendData = result?.data?.trend?.map((item: any) => ({
    date: item.date,
    mentions: item.mentions,
    reach: item.reach,
  })) || [];

  // Prepare country coverage data for chart
  const countryData = result?.data?.country_coverage?.map((item: any) => ({
    country: item.country,
    value: item.coverage,
  })) || [];

  const summary = result?.data?.collection_summary || {};
  const socialUpdates = result?.data?.social_updates || [];
  const countryCoverage = result?.data?.country_coverage || [];
  const references = result?.data?.references || [];

  // Format engagement number
  const formatEngagement = (num: number | undefined) => {
    if (!num) return '-';
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  return (
    <div>
      {/* Header Card - Similar to TopicPage style */}
      <Card style={{ marginBottom: 16, borderRadius: 12 }} bodyStyle={{ padding: '16px 20px' }}>
        <div>
          <Title level={3} style={{ marginBottom: 4 }}>
            <SearchOutlined style={{ marginRight: 8, color: '#2563eb' }} />
            {is_en ? 'Get Latest Information' : '获取最新信息'}
          </Title>
          <Text type="secondary">
            {is_en
              ? 'Fetch real-time social media data using x_search and web_search'
              : '使用 x_search 和 web_search 获取实时社交媒体数据'}
          </Text>

          {/* Input Form - Similar to TopicPage console style */}
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
              <Text strong style={{ fontSize: 13 }}>{is_en ? 'Topic' : '主题'}</Text>
              <Input
                size="small"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder={is_en ? 'e.g., BYD Q1 2026' : '例如：小米汽车'}
                style={{ width: 200 }}
                onPressEnter={handleCollect}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>{is_en ? 'Limit' : '数量'}</Text>
              <Select
                size="small"
                value={socialLimit}
                onChange={setSocialLimit}
                style={{ width: 80 }}
                options={[
                  { value: 5, label: '5' },
                  { value: 10, label: '10' },
                  { value: 20, label: '20' },
                  { value: 30, label: '30' },
                ]}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>{is_en ? 'Model' : '模型'}</Text>
              <Select
                size="small"
                value={selectedModel}
                onChange={setSelectedModel}
                style={{ width: 260 }}
                options={[
                  { value: 'xai.grok-4.20-multi-agent-0309', label: `Grok 4.20 - ${is_en ? 'Deep Analysis / Default' : '复杂分析 / 默认'}` },
                  { value: 'xai.grok-4.3', label: `Grok 4.3 - ${is_en ? 'Faster / General Analysis' : '更快 / 通用分析'}` },
                ]}
              />
              <Button type="primary" size="small" icon={<SearchOutlined />} onClick={handleCollect} loading={loading}>
                {is_en ? 'Fetch Data' : '获取数据'}
              </Button>
              {result && (
                <Button size="small" icon={<FilePdfOutlined />} onClick={handleExportPdf} loading={exporting}>
                  {is_en ? 'Export PDF' : '导出PDF'}
                </Button>
              )}
            </Space>
          </div>
        </div>
      </Card>

      {/* Loading State */}
      {loading && (
        <Card style={{ marginBottom: 24, borderRadius: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
            <Spin size="small" />
            <Text>{is_en ? 'Fetching data using x_search and web_search...' : '正在使用 x_search 和 web_search 获取数据...'}</Text>
          </div>
        </Card>
      )}

      {/* Results */}
      {result && !loading && (
        <>
          {/* Data Overview Card */}
          <Card style={{ marginBottom: 24, borderRadius: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
              <Space wrap>
                <Tag color="blue">{selectedModel}</Tag>
                <Tag color="purple">{is_en ? 'Social Updates' : '社交更新'} {socialLimit}</Tag>
                <Text type="secondary">
                  {is_en ? 'Collected at' : '采集时间'}: {new Date().toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US')}
                </Text>
              </Space>
              <Space wrap>
                <Tag color="green"><FireOutlined /> {summary.verified_social_updates || 0} {is_en ? 'verified' : '条验证'}</Tag>
                <Tag color="cyan"><GlobalOutlined /> {countryCoverage.length} {is_en ? 'countries' : '个国家'}</Tag>
              </Space>
            </div>
          </Card>

          {/* Charts Row */}
          <div style={{ marginBottom: 24 }}>
            <MentionsReachTrendChart data={trendData} />
          </div>

          {/* Structured Insights Collapse */}
          <Collapse
            style={{ marginBottom: 24, borderRadius: 12 }}
            defaultActiveKey={['social-updates', 'country-coverage', 'references']}
            items={[
              {
                key: 'social-updates',
                label: (
                  <Space>
                    <Text strong>{is_en ? 'Social Media Updates' : '社交媒体最新信息'}</Text>
                    <Tag color="purple">{socialUpdates.length} {is_en ? 'items' : '条'}</Tag>
                  </Space>
                ),
                children: (
                  <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 0.8fr)', gap: 12, alignItems: 'start' }}>
                    {/* Social Updates List */}
                    <div style={{ minWidth: 0 }}>
                      {socialUpdates.length > 0 ? (
                        <List
                          size="small"
                          dataSource={socialUpdates}
                          renderItem={(item: any) => (
                            <List.Item style={{ padding: '12px 0', borderBottom: '1px solid #f0f0f0' }}>
                              <div style={{ width: '100%' }}>
                                {/* Header: Time + Platform + Country */}
                                <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
                                  {item.time && (
                                    <Tag icon={<ClockCircleOutlined />} color="default" style={{ margin: 0 }}>
                                      {item.time}
                                    </Tag>
                                  )}
                                  {item.platform && (
                                    <Tag color="blue" style={{ margin: 0 }}>{item.platform}</Tag>
                                  )}
                                  {item.country && (
                                    <Tag color="green" style={{ margin: 0 }}>{item.country}</Tag>
                                  )}
                                </div>

                                {/* Account */}
                                {item.account && (
                                  <Text strong style={{ display: 'block', marginBottom: 4, fontSize: 13 }}>
                                    {item.account}
                                  </Text>
                                )}

                                {/* Summary */}
                                {item.summary && (
                                  <Paragraph style={{ marginBottom: 8, fontSize: 12, color: '#4a5568' }} ellipsis={{ rows: 2 }}>
                                    {item.summary}
                                  </Paragraph>
                                )}

                                {/* Engagement Metrics */}
                                <div style={{ display: 'flex', gap: 16, marginBottom: 8, flexWrap: 'wrap' }}>
                                  {item.likes !== undefined && (
                                    <Space size={4}>
                                      <LikeOutlined style={{ color: '#eb2f96' }} />
                                      <Text type="secondary" style={{ fontSize: 12 }}>{formatEngagement(item.likes)}</Text>
                                    </Space>
                                  )}
                                  {item.retweets !== undefined && (
                                    <Space size={4}>
                                      <RetweetOutlined style={{ color: '#52c41a' }} />
                                      <Text type="secondary" style={{ fontSize: 12 }}>{formatEngagement(item.retweets)}</Text>
                                    </Space>
                                  )}
                                  {item.replies !== undefined && (
                                    <Space size={4}>
                                      <MessageOutlined style={{ color: '#1890ff' }} />
                                      <Text type="secondary" style={{ fontSize: 12 }}>{formatEngagement(item.replies)}</Text>
                                    </Space>
                                  )}
                                  {item.views !== undefined && (
                                    <Space size={4}>
                                      <EyeOutlined style={{ color: '#722ed1' }} />
                                      <Text type="secondary" style={{ fontSize: 12 }}>{formatEngagement(item.views)}</Text>
                                    </Space>
                                  )}
                                  {item.engagement !== undefined && (
                                    <Space size={4}>
                                      <FireOutlined style={{ color: '#fa8c16' }} />
                                      <Text type="secondary" style={{ fontSize: 12 }}>{formatEngagement(item.engagement)}</Text>
                                    </Space>
                                  )}
                                </div>

                                {/* URL */}
                                {item.url && (
                                  <a href={item.url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>
                                    <LinkOutlined /> {is_en ? 'View Source' : '查看原文'}
                                  </a>
                                )}
                              </div>
                            </List.Item>
                          )}
                        />
                      ) : (
                        <Empty description={is_en ? 'No social updates' : '暂无社交更新'} />
                      )}
                    </div>

                    {/* Country Coverage Chart */}
                    <div style={{ minWidth: 0 }}>
                      <CountryCoverageChart
                        title={is_en ? 'Country Coverage' : '国家覆盖'}
                        subtitle={is_en ? 'By verified URLs' : '按验证URL统计'}
                        data={countryData}
                      />
                    </div>
                  </div>
                ),
              },
              {
                key: 'country-coverage',
                label: (
                  <Space>
                    <Text strong>{is_en ? 'Country Coverage Details' : '国家覆盖详情'}</Text>
                    <Tag color="cyan">{countryCoverage.length} {is_en ? 'countries' : '个国家'}</Tag>
                  </Space>
                ),
                children: countryCoverage.length > 0 ? (
                  <List
                    size="small"
                    dataSource={countryCoverage}
                    renderItem={(item: any) => (
                      <List.Item>
                        <div style={{ width: '100%' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                            <Space>
                              <GlobalOutlined style={{ color: '#2563eb' }} />
                              <Text strong>{item.country}</Text>
                            </Space>
                            <Tag color="blue">{item.coverage} {is_en ? 'items' : '条'}</Tag>
                          </div>
                          {item.platforms && item.platforms.length > 0 && (
                            <div style={{ marginBottom: 4 }}>
                              {item.platforms.map((p: string, idx: number) => (
                                <Tag key={idx} color="default" style={{ margin: '0 4px 4px 0' }}>{p}</Tag>
                              ))}
                            </div>
                          )}
                          {item.summary && (
                            <Text type="secondary" style={{ fontSize: 12 }}>{item.summary}</Text>
                          )}
                        </div>
                      </List.Item>
                    )}
                  />
                ) : (
                  <Empty description={is_en ? 'No country coverage data' : '暂无国家覆盖数据'} />
                ),
              },
              {
                key: 'references',
                label: (
                  <Space>
                    <Text strong>{is_en ? 'References' : '参考文献'}</Text>
                    <Tag color="purple">{references.length} {is_en ? 'sources' : '条来源'}</Tag>
                  </Space>
                ),
                children: references.length > 0 ? (
                  <List
                    size="small"
                    dataSource={references}
                    renderItem={(item: any) => (
                      <List.Item>
                        <div style={{ width: '100%' }}>
                          {item.source && <Tag color="purple" style={{ marginBottom: 4 }}>{item.source}</Tag>}
                          {item.title && (
                            <Text strong style={{ display: 'block', marginBottom: 4 }}>{item.title}</Text>
                          )}
                          {item.summary && (
                            <Paragraph type="secondary" style={{ marginBottom: 4, fontSize: 12 }} ellipsis={{ rows: 2 }}>
                              {item.summary}
                            </Paragraph>
                          )}
                          {item.url && (
                            <a href={item.url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>
                              <LinkOutlined /> {item.url}
                            </a>
                          )}
                        </div>
                      </List.Item>
                    )}
                  />
                ) : (
                  <Empty description={is_en ? 'No references' : '暂无参考文献'} />
                ),
              },
            ]}
          />
        </>
      )}

      {/* Empty State */}
      {!result && !loading && (
        <Card style={{ borderRadius: 12, textAlign: 'center', padding: '60px 0' }}>
          <Empty
            description={
              <Text type="secondary" style={{ fontSize: 16 }}>
                {is_en
                  ? 'Enter a topic and click "Fetch Data" to get started'
                  : '输入主题并点击"获取数据"开始'}
              </Text>
            }
          />
        </Card>
      )}
    </div>
  );
};

export default LatestInfoPage;
