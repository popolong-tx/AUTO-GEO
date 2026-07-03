import React from 'react';
import ReactECharts from 'echarts-for-react';
import { Typography, Space, Tag } from 'antd';

const { Text } = Typography;

interface SentimentChartProps {
  sentiment: {
    positive: number;
    neutral: number;
    negative: number;
  };
}

const SentimentChart: React.FC<SentimentChartProps> = ({ sentiment }) => {
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
        name: '情绪分布',
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
          { value: pos, name: '正面', itemStyle: { color: '#48bb78' } },
          { value: neu, name: '中性', itemStyle: { color: '#ecc94b' } },
          { value: neg, name: '负面', itemStyle: { color: '#f56565' } },
        ],
      },
    ],
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Tag color="green">正面 {pos}%</Tag>
        <Tag color="gold">中性 {neu}%</Tag>
        <Tag color="red">负面 {neg}%</Tag>
      </Space>
      <ReactECharts option={option} style={{ height: 300 }} />
    </div>
  );
};

export default SentimentChart;
