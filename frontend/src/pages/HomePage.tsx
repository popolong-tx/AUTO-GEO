import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Typography, Spin, Space, Tag, Statistic } from 'antd';
import {
  ThunderboltOutlined,
  BarChartOutlined,
  BugOutlined,
  SafetyOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  RadarChartOutlined,
  GlobalOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { getTopics } from '../services/api';

const { Title, Text, Paragraph } = Typography;

const TOPIC_ICONS: Record<string, React.ReactNode> = {
  'goodwood-festival': <RocketOutlined style={{ fontSize: 34, color: '#fff' }} />,
  'flash-charge-launch': <ThunderboltOutlined style={{ fontSize: 34, color: '#fff' }} />,
  'q1-financial-report': <BarChartOutlined style={{ fontSize: 34, color: '#fff' }} />,
  'smart-chip-launch': <BugOutlined style={{ fontSize: 34, color: '#fff' }} />,
  'dod-1260h-list': <SafetyOutlined style={{ fontSize: 34, color: '#fff' }} />,
  'custom-report': <FileTextOutlined style={{ fontSize: 34, color: '#fff' }} />,
};

const TOPIC_GRADIENTS: Record<string, string> = {
  'goodwood-festival': 'linear-gradient(135deg, #0f172a 0%, #1d4ed8 55%, #38bdf8 100%)',
  'flash-charge-launch': 'linear-gradient(135deg, #f59e0b 0%, #facc15 100%)',
  'q1-financial-report': 'linear-gradient(135deg, #10b981 0%, #34d399 100%)',
  'smart-chip-launch': 'linear-gradient(135deg, #2563eb 0%, #60a5fa 100%)',
  'dod-1260h-list': 'linear-gradient(135deg, #ef4444 0%, #fb7185 100%)',
  'custom-report': 'linear-gradient(135deg, #7c3aed 0%, #a78bfa 100%)',
};

const HomePage: React.FC = () => {
  const [topics, setTopics] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    getTopics()
      .then((res) => setTopics(res.data.topics))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div>
      <Card style={{ marginBottom: 28, borderRadius: 18, overflow: 'hidden' }} bodyStyle={{ padding: 0 }}>
        <div
          style={{
            padding: '28px 30px',
            background: 'linear-gradient(135deg, rgba(15,23,42,0.96) 0%, rgba(23,55,102,0.92) 55%, rgba(31,111,235,0.82) 100%)',
            color: '#fff',
          }}
        >
          <Space direction="vertical" size={10} style={{ width: '100%' }}>
            <Space wrap>
              <Tag color="blue">实时舆情</Tag>
              <Tag color="cyan">X / Web Search</Tag>
              <Tag color="purple">管理层看板</Tag>
            </Space>
            <Title level={2} style={{ margin: 0, color: '#fff' }}>
              舆情分析概览
            </Title>
            <Text style={{ color: 'rgba(255,255,255,0.78)', fontSize: 14 }}>
              选择话题开始分析，系统将基于 Grok + 搜索工具 + 外部数据联合分析提供深度舆情洞察。
            </Text>
          </Space>
        </div>
      </Card>

      <Row gutter={[18, 18]} style={{ marginBottom: 28 }}>
        <Col xs={24} md={8}>
          <Card style={{ borderRadius: 16 }}>
            <Statistic title="分析专题数" value={topics.length} prefix={<RadarChartOutlined style={{ color: '#2563eb' }} />} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card style={{ borderRadius: 16 }}>
            <Statistic title="支持模型" value={2} prefix={<FileTextOutlined style={{ color: '#7c3aed' }} />} suffix="个" />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card style={{ borderRadius: 16 }}>
            <Statistic title="搜索覆盖" value="Web + X" prefix={<GlobalOutlined style={{ color: '#0ea5e9' }} />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[24, 24]}>
        {topics.map((topic) => (
          <Col xs={24} sm={12} lg={8} xl={6} key={topic.id}>
            <Card
              className="topic-card"
              hoverable
              onClick={() => navigate(`/topic/${topic.id}`)}
              style={{ height: '100%', borderRadius: 16, overflow: 'hidden' }}
              bodyStyle={{ padding: 18 }}
              cover={
                <div
                  style={{
                    height: 110,
                    background: TOPIC_GRADIENTS[topic.id] || 'linear-gradient(135deg, #94a3b8, #64748b)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    position: 'relative',
                  }}
                >
                  <div
                    style={{
                      width: 60,
                      height: 60,
                      borderRadius: 18,
                      background: 'rgba(255,255,255,0.16)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backdropFilter: 'blur(6px)',
                      boxShadow: '0 10px 20px rgba(0,0,0,0.12)',
                    }}
                  >
                    {TOPIC_ICONS[topic.id] || <span style={{ fontSize: 32 }}>📊</span>}
                  </div>
                </div>
              }
            >
              <Space direction="vertical" size={8} style={{ width: '100%' }}>
                <Space wrap>
                  <Tag color="blue">专题分析</Tag>
                  {topic.id === 'custom-report' ? <Tag color="purple">自定义</Tag> : <Tag color="cyan">预置</Tag>}
                </Space>
                <Title level={5} style={{ margin: 0 }}>
                  {topic.name}
                </Title>
                <Paragraph
                  type="secondary"
                  ellipsis={{ rows: 2 }}
                  style={{ fontSize: 13, marginBottom: 0 }}
                >
                  {topic.description}
                </Paragraph>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      <Card style={{ marginTop: 32, borderRadius: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <ClockCircleOutlined style={{ color: '#64748b' }} />
          <Text type="secondary">
            支持模型：xai.grok-4.20-multi-agent-0309 / xai.grok-4.3；支持 Web 搜索、X 社交媒体最新数据、参考文件上传与引用输出。
          </Text>
        </div>
      </Card>
    </div>
  );
};

export default HomePage;
