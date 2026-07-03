import React, { useMemo } from 'react';
import { Drawer, Descriptions, Empty, Space, Tag, Typography, Spin, Alert } from 'antd';
import { LinkOutlined, WarningOutlined } from '@ant-design/icons';

const { Text, Paragraph } = Typography;

export interface SourceDetail {
  id?: string;
  url?: string;
  media_name?: string;
  mediaName?: string;
  published_time?: string;
  publishedTime?: string;
  country?: string;
  language?: string;
  author?: string;
  reach?: string | number;
  ave?: string | number;
  sentiment?: string;
  summary?: string;
  keywords?: string[] | string;
  title?: string;
  sourceType?: string;
  [key: string]: any;
}

export interface SourceDetailDrawerProps {
  open: boolean;
  loading?: boolean;
  source?: SourceDetail | null;
  onClose: () => void;
}

const formatValue = (value: unknown) => {
  if (value === null || value === undefined || value === '') return '-';
  if (Array.isArray(value)) return value.length > 0 ? value.join(', ') : '-';
  return String(value);
};

const SourceDetailDrawer: React.FC<SourceDetailDrawerProps> = ({ open, loading = false, source, onClose }) => {
  const keywords = useMemo(() => {
    const raw = source?.keywords;
    if (Array.isArray(raw)) return raw.filter(Boolean).map(String);
    if (typeof raw === 'string') {
      return raw
        .split(/[;,，\n]/)
        .map((item) => item.trim())
        .filter(Boolean);
    }
    return [];
  }, [source?.keywords]);

  const title = source?.title?.trim() || source?.media_name?.trim() || source?.mediaName?.trim() || '来源详情';
  const publishedTime = source?.published_time || source?.publishedTime;
  const mediaName = source?.media_name || source?.mediaName;
  const urlUnavailable = !source?.url || String(source?.summary || '').includes('URL unavailable');
  const placeholderUrl = Boolean(source?.url) && /(?:example|placeholder|dummy|fake)/i.test(String(source?.url || ''));
  const inaccessibleReason = source?.access_note || source?.accessNote || source?.note || (urlUnavailable || placeholderUrl ? '该来源目前无法直接访问，可能是 URL 缺失、平台限制、权限限制、原始链接已失效，或原始数据里带有示例/占位链接。' : '');

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={680}
      title={title}
      destroyOnClose
      extra={source?.sourceType ? <Tag color="blue">{source.sourceType}</Tag> : null}
    >
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '32px 0' }}>
          <Spin />
        </div>
      ) : !source ? (
        <Empty description="暂无来源详情" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          {inaccessibleReason ? (
            <Alert
              type="warning"
              showIcon
              icon={<WarningOutlined />}
              message="该来源部分内容可能无法直接访问"
              description={inaccessibleReason}
            />
          ) : null}

          <div>
            <Text type="secondary" style={{ display: 'block', marginBottom: 6 }}>
              URL
            </Text>
            {source?.url ? (
              <Text copyable={{ text: source.url }}>
                <LinkOutlined style={{ marginRight: 6 }} />
                <a href={source.url} target="_blank" rel="noreferrer">
                  {source.url}
                </a>
              </Text>
            ) : (
              <Text type="secondary">-</Text>
            )}
          </div>

          <Descriptions bordered size="small" column={1} labelStyle={{ width: 180 }}>
            <Descriptions.Item label="媒体名称">{formatValue(mediaName || source?.title)}</Descriptions.Item>
            <Descriptions.Item label="发布时间">{formatValue(publishedTime)}</Descriptions.Item>
            <Descriptions.Item label="国家/地区">{formatValue(source?.country)}</Descriptions.Item>
            <Descriptions.Item label="语言">{formatValue(source?.language)}</Descriptions.Item>
            <Descriptions.Item label="作者">{formatValue(source?.author)}</Descriptions.Item>
            <Descriptions.Item label="Reach">{formatValue(source?.reach)}</Descriptions.Item>
            <Descriptions.Item label="AVE">{formatValue(source?.ave)}</Descriptions.Item>
            <Descriptions.Item label="情感">{formatValue(source?.sentiment)}</Descriptions.Item>
            <Descriptions.Item label="摘要">
              {source?.summary ? <Paragraph style={{ marginBottom: 0 }}>{source.summary}</Paragraph> : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="关键词">
              {keywords.length > 0 ? (
                <Space size={[4, 8]} wrap>
                  {keywords.map((keyword) => (
                    <Tag key={keyword}>{keyword}</Tag>
                  ))}
                </Space>
              ) : (
                '-'
              )}
            </Descriptions.Item>
          </Descriptions>
        </Space>
      )}
    </Drawer>
  );
};

export default SourceDetailDrawer;
