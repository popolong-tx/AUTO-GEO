import React from 'react';
import ReactECharts from 'echarts-for-react';
import { Typography, Space, Tag } from 'antd';
import { useTranslation } from '../i18n/LanguageContext';

const { Text } = Typography;

interface SentimentChartProps {
  sentiment: {
    positive: number;
    neutral: number;
    negative: number;
  };
}

const SentimentChart: React.FC<SentimentChartProps> = ({ sentiment }) => {
  const { t } = useTranslation();

  const rawPos = Number(sentiment.positive || 0);
  const rawNeu = Number(sentiment.neutral || 0);
  const rawNeg = Number(sentiment.negative || 0);
  const total = rawPos + rawNeu + rawNeg || 1;
  const pos = Math.round((rawPos / total) * 1000) / 10;
  const neu = Math.round((rawNeu / total) * 1000) / 10;
  const neg = Math.round((rawNeg / total) * 1000) / 10;

  const option = {
    tooltip: {
      trigger: 'item' as const,
      formatter: '{b}: {c}%',
    },
    legend: {
      bottom: '0%',
      left: 'center' as const,
    },
    series: [
      {
        name: t('sentiment.distribution'),
        type: 'pie' as const,
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: true,
          formatter: '{b}\n{d}%',
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold' as const,
          },
        },
        data: [
          { value: pos, name: t('sentiment.positive'), itemStyle: { color: '#48bb78' } },
          { value: neu, name: t('sentiment.neutral'), itemStyle: { color: '#ecc94b' } },
          { value: neg, name: t('sentiment.negative'), itemStyle: { color: '#f56565' } },
        ],
      },
    ],
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Tag color="green">{t('sentiment.positive')} {pos}%</Tag>
        <Tag color="gold">{t('sentiment.neutral')} {neu}%</Tag>
        <Tag color="red">{t('sentiment.negative')} {neg}%</Tag>
      </Space>
      <ReactECharts option={option} style={{ height: 300 }} />
    </div>
  );
};

export default SentimentChart;
