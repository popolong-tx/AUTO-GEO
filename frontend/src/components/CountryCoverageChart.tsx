import React, { useMemo } from 'react';
import { Card, Empty, Space, Tag, Typography } from 'antd';
import { GlobalOutlined } from '@ant-design/icons';
import { useTranslation } from '../i18n/LanguageContext';

const { Text } = Typography;

export interface CountryCoverageItem {
  country?: string;
  name?: string;
  label?: string;
  coverage?: number | string | null;
  count?: number | string | null;
  value?: number | string | null;
  sources?: number | string | null;
  mentions?: number | string | null;
}

export interface CountryCoverageChartProps {
  title?: string;
  subtitle?: string;
  data?: CountryCoverageItem[] | null;
  loading?: boolean;
}

const toNumber = (value: unknown) => {
  const num = Number(value);
  return Number.isFinite(num) ? num : 0;
};

const CountryCoverageChart: React.FC<CountryCoverageChartProps> = ({
  title,
  subtitle,
  data,
  loading = false,
}) => {
  const { t } = useTranslation();

  const normalized = useMemo(() => {
    if (!Array.isArray(data) || data.length === 0) return [];
    return data
      .map((item, index) => ({
        country: String(item?.country || item?.name || item?.label || `Country ${index + 1}`),
        value: toNumber(item?.coverage ?? item?.count ?? item?.value ?? item?.sources ?? item?.mentions),
      }))
      .filter((item) => item.country && item.value >= 0)
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }, [data]);

  const hasData = normalized.length > 0;

  return (
    <Card
      size="small"
      loading={loading}
      style={{
        borderRadius: 12,
        border: '1px solid rgba(148, 163, 184, 0.18)',
        boxShadow: '0 1px 2px rgba(15, 23, 42, 0.04)',
        overflow: 'hidden',
        height: '100%',
      }}
      bodyStyle={{ padding: 12, height: '100%', display: 'flex', flexDirection: 'column' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 10 }}>
        <div style={{ minWidth: 0 }}>
          <Text strong style={{ display: 'block', fontSize: 13, lineHeight: 1.2 }}>
            {title || t('countryCoverage.titleEn')}
          </Text>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {subtitle || t('countryCoverage.subtitleEn')}
          </Text>
        </div>
        <Space size={6} wrap>
          <Tag color="blue"><GlobalOutlined /> X / web-search</Tag>
        </Space>
      </div>

      <div style={{ flex: 1, minHeight: 0, borderRadius: 10, overflow: 'hidden', border: '1px solid rgba(148, 163, 184, 0.12)', background: 'linear-gradient(180deg, rgba(14,165,233,0.10) 0%, rgba(15,23,42,0.02) 100%)', marginBottom: 12, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: 12 }}>
        {hasData ? (
          <div style={{ width: '100%', display: 'grid', gridTemplateColumns: '1fr', gap: 10 }}>
            {normalized.map((item) => {
              const maxValue = Math.max(...normalized.map((d) => d.value), 1);
              const percent = Math.max(6, Math.round((item.value / maxValue) * 100));
              return (
                <div key={item.country} style={{ display: 'grid', gridTemplateColumns: '76px 1fr 44px', gap: 8, alignItems: 'center' }}>
                  <Text ellipsis style={{ fontSize: 12, color: '#334155' }} title={item.country}>
                    {item.country}
                  </Text>
                  <div style={{ height: 10, borderRadius: 999, background: '#e2e8f0', overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${percent}%`,
                        height: '100%',
                        borderRadius: 999,
                        background: 'linear-gradient(90deg, #2563eb 0%, #60a5fa 100%)',
                      }}
                    />
                  </div>
                  <Text style={{ fontSize: 12, textAlign: 'right', color: '#475569' }}>{item.value}</Text>
                </div>
              );
            })}
          </div>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('countryCoverage.noDataEn')} />
        )}
      </div>
    </Card>
  );
};

export default CountryCoverageChart;
