import React from 'react';
import { Card, Typography } from 'antd';

const { Text } = Typography;

export interface KpiCardProps {
  title: string;
  value?: React.ReactNode;
  prefix?: React.ReactNode;
  suffix?: React.ReactNode;
  hint?: React.ReactNode;
  accentColor?: string;
  loading?: boolean;
}

const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  prefix,
  suffix,
  hint,
  accentColor = '#2563eb',
  loading = false,
}) => {
  const displayValue = value === null || value === undefined || value === '' ? '--' : value;

  return (
    <Card
      loading={loading}
      bodyStyle={{ padding: '12px 14px' }}
      style={{
        height: '100%',
        borderRadius: 12,
        border: '1px solid rgba(148, 163, 184, 0.18)',
        boxShadow: '0 1px 2px rgba(15, 23, 42, 0.04)',
        background: '#fff',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, minWidth: 0 }}>
        {prefix ? (
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 10,
              background: `linear-gradient(135deg, ${accentColor} 0%, ${accentColor}cc 100%)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              flexShrink: 0,
              marginTop: 1,
            }}
          >
            {prefix}
          </div>
        ) : null}

        <div style={{ minWidth: 0, flex: 1 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'baseline',
              justifyContent: 'space-between',
              gap: 8,
            }}
          >
            <Text type="secondary" style={{ fontSize: 12, lineHeight: 1.2 }}>
              {title}
            </Text>
            {suffix ? (
              <Text type="secondary" style={{ fontSize: 12, lineHeight: 1.2, flexShrink: 0 }}>
                {suffix}
              </Text>
            ) : null}
          </div>

          <div
            style={{
              marginTop: 6,
              fontSize: 22,
              lineHeight: 1.08,
              fontWeight: 700,
              color: '#0f172a',
              letterSpacing: '-0.02em',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
            title={typeof displayValue === 'string' ? displayValue : undefined}
          >
            {displayValue}
          </div>

          {hint ? (
            <Text type="secondary" style={{ display: 'block', marginTop: 4, fontSize: 12, lineHeight: 1.2 }}>
              {hint}
            </Text>
          ) : null}
        </div>
      </div>
    </Card>
  );
};

export default KpiCard;
