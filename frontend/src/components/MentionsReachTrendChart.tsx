import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { Card, Empty, Space, Tag, Typography } from 'antd';
import { RiseOutlined, LineChartOutlined } from '@ant-design/icons';
import { useTranslation } from '../i18n/LanguageContext';

const { Text } = Typography;

export interface TrendPoint {
  date?: string;
  label?: string;
  mentions?: number | string | null;
  reach?: number | string | null;
}

export interface MentionsReachTrendChartProps {
  title?: string;
  data?: TrendPoint[] | null;
  loading?: boolean;
}

const formatNumber = (value: unknown) => {
  const num = Number(value);
  if (!Number.isFinite(num)) return 0;
  return num;
};

const compactLabel = (value?: string) => {
  if (!value) return '';
  const text = String(value).trim();
  if (!text) return '';
  if (text.length <= 10) return text;
  return `${text.slice(5, 10) || text.slice(0, 10)}`;
};

const MentionsReachTrendChart: React.FC<MentionsReachTrendChartProps> = ({
  title,
  data,
  loading = false,
}) => {
  const { t } = useTranslation();

  const normalized = useMemo(() => {
    if (!Array.isArray(data) || data.length === 0) return [];
    return data
      .map((item, index) => ({
        date: item?.date || item?.label || `P${index + 1}`,
        mentions: formatNumber(item?.mentions ?? item?.count ?? item?.value ?? item?.sources),
        reach: formatNumber(item?.reach ?? item?.views ?? item?.impressions ?? item?.engagement),
      }))
      .filter((item) => item.date);
  }, [data]);

  const hasData = normalized.length > 0;
  const chartData = normalized;
  const allZero = normalized.every((item) => Number(item.mentions) === 0 && Number(item.reach) === 0);

  const option = useMemo(() => ({
    grid: { left: 6, right: 10, top: 28, bottom: 20, containLabel: true },
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'line' as const },
    },
    legend: {
      top: 0,
      left: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { fontSize: 11 },
    },
    xAxis: {
      type: 'category' as const,
      boundaryGap: false,
      axisLabel: {
        color: '#64748b',
        fontSize: 10,
        interval: 0,
        formatter: compactLabel,
      },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisTick: { show: false },
      data: chartData.map((item) => item.date),
    },
    yAxis: [
      {
        type: 'value' as const,
        name: t('chart.mentions'),
        nameTextStyle: { fontSize: 10, color: '#64748b' },
        axisLabel: { color: '#64748b', fontSize: 10 },
        splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' as const } },
      },
      {
        type: 'value' as const,
        name: t('chart.reach'),
        nameTextStyle: { fontSize: 10, color: '#64748b' },
        axisLabel: { color: '#64748b', fontSize: 10 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: t('chart.mentions'),
        type: 'line' as const,
        smooth: true,
        symbolSize: 7,
        showSymbol: false,
        lineStyle: { width: 2, color: '#2563eb' },
        itemStyle: { color: '#2563eb' },
        areaStyle: { color: 'rgba(37, 99, 235, 0.08)' },
        data: chartData.map((item) => item.mentions),
      },
      {
        name: t('chart.reach'),
        type: 'line' as const,
        smooth: true,
        yAxisIndex: 1,
        symbolSize: 7,
        showSymbol: false,
        lineStyle: { width: 2, color: '#f97316' },
        itemStyle: { color: '#f97316' },
        areaStyle: { color: 'rgba(249, 115, 22, 0.08)' },
        data: chartData.map((item) => item.reach),
      },
    ],
  }), [normalized, t]);

  return (
    <Card
      size="small"
      loading={loading}
      style={{
        borderRadius: 12,
        border: '1px solid rgba(148, 163, 184, 0.18)',
        boxShadow: '0 1px 2px rgba(15, 23, 42, 0.04)',
      }}
      bodyStyle={{ padding: 12 }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 8 }}>
        <div style={{ minWidth: 0 }}>
          <Text strong style={{ display: 'block', fontSize: 13, lineHeight: 1.2 }}>
            {title || t('chart.mentionsReachTrend')}
          </Text>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {t('chart.verifiedFrom')}
          </Text>
        </div>
        <Space size={6} wrap>
          <Tag color="blue"><RiseOutlined /> {t('chart.mentions')}</Tag>
          <Tag color="orange">{t('chart.reach')}</Tag>
        </Space>
      </div>

      {hasData && !allZero ? (
        <ReactECharts option={option} style={{ height: 230 }} notMerge lazyUpdate />
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Space direction="vertical" size={4}>
              <Tag color="blue"><LineChartOutlined /> {t('chart.waitingData')}</Tag>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {t('chart.noTrendData')}
              </Text>
            </Space>
          }
        />
      )}

      <div style={{ marginTop: 8, padding: '8px 12px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
        <Text type="secondary" style={{ fontSize: 11, lineHeight: 1.6 }}>
          {t('chart.trendExplanation')}
        </Text>
      </div>
    </Card>
  );
};

export default MentionsReachTrendChart;
