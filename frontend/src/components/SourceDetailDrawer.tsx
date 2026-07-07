import React, { useMemo } from 'react';
import { Drawer, Descriptions, Empty, Space, Tag, Typography, Spin, Alert } from 'antd';
import { LinkOutlined, WarningOutlined } from '@ant-design/icons';
import { useTranslation } from '../i18n/LanguageContext';

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
  const { t } = useTranslation();

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

  const title = source?.title?.trim() || source?.media_name?.trim() || source?.mediaName?.trim() || t('sourceDetail.title');
  const publishedTime = source?.published_time || source?.publishedTime;
  const mediaName = source?.media_name || source?.mediaName;
  const urlUnavailable = !source?.url || String(source?.summary || '').includes('URL unavailable');
  const placeholderUrl = Boolean(source?.url) && /(?:example|placeholder|dummy|fake)/i.test(String(source?.url || ''));
  const inaccessibleReason = source?.access_note || source?.accessNote || source?.note || (urlUnavailable || placeholderUrl ? t('sourceDetail.inaccessibleReason') : '');

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
        <Empty description={t('sourceDetail.title')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          {inaccessibleReason ? (
            <Alert
              type="warning"
              showIcon
              icon={<WarningOutlined />}
              message={t('sourceDetail.inaccessible')}
              description={inaccessibleReason}
            />
          ) : null}

          <div>
            <Text type="secondary" style={{ display: 'block', marginBottom: 6 }}>
              {t('sourceDetail.url')}
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
            <Descriptions.Item label={t('sourceDetail.mediaName')}>{formatValue(mediaName || source?.title)}</Descriptions.Item>
            <Descriptions.Item label={t('sourceDetail.publishTime')}>{formatValue(publishedTime)}</Descriptions.Item>
            <Descriptions.Item label={t('sourceDetail.country')}>{formatValue(source?.country)}</Descriptions.Item>
            <Descriptions.Item label={t('sourceDetail.language')}>{formatValue(source?.language)}</Descriptions.Item>
            <Descriptions.Item label={t('sourceDetail.author')}>{formatValue(source?.author)}</Descriptions.Item>
            <Descriptions.Item label={t('sourceDetail.reach')}>{formatValue(source?.reach)}</Descriptions.Item>
            <Descriptions.Item label={t('sourceDetail.ave')}>{formatValue(source?.ave)}</Descriptions.Item>
            <Descriptions.Item label={t('sourceDetail.sentiment')}>{formatValue(source?.sentiment)}</Descriptions.Item>
            <Descriptions.Item label={t('sourceDetail.summary')}>
              {source?.summary ? <Paragraph style={{ marginBottom: 0 }}>{source.summary}</Paragraph> : '-'}
            </Descriptions.Item>
            <Descriptions.Item label={t('sourceDetail.keywords')}>
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
