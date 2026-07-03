import React from 'react';
import { Empty, Tag, Typography } from 'antd';
import { LinkOutlined } from '@ant-design/icons';

const { Text, Paragraph } = Typography;

export interface SourceEvidenceItem {
  id: string;
  title?: string;
  url?: string;
  sourceType?: string;
  summary?: string;
}

export interface TopSourcesListProps {
  sources?: SourceEvidenceItem[];
  selectedId?: string;
  onSelect?: (source: SourceEvidenceItem) => void;
  loading?: boolean;
}

const TopSourcesList: React.FC<TopSourcesListProps> = ({
  sources = [],
  selectedId,
  onSelect,
  loading = false,
}) => {
  if (!loading && sources.length === 0) {
    return <Empty description="暂无来源证据" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  return (
    <div
      style={{
        display: 'grid',
        gap: 8,
      }}
    >
      {sources.map((source) => {
        const selected = source.id === selectedId;
        const title = source.title?.trim() || '未命名来源';
        const url = source.url?.trim() || '';
        const sourceType = source.sourceType?.trim();
        const summary = source.summary?.trim();

        return (
          <button
            key={source.id}
            type="button"
            onClick={() => onSelect?.(source)}
            style={{
              width: '100%',
              border: '1px solid ' + (selected ? 'rgba(37, 99, 235, 0.35)' : 'rgba(148, 163, 184, 0.18)'),
              background: selected ? 'rgba(37, 99, 235, 0.04)' : '#fff',
              borderRadius: 10,
              padding: '10px 12px',
              textAlign: 'left',
              cursor: onSelect ? 'pointer' : 'default',
              boxShadow: '0 1px 2px rgba(15, 23, 42, 0.04)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
              <div style={{ minWidth: 0, flex: 1 }}>
                <Text
                  strong
                  style={{ display: 'block', fontSize: 13, lineHeight: 1.25, color: '#0f172a' }}
                  ellipsis={{ tooltip: title }}
                >
                  {title}
                </Text>
                <div style={{ marginTop: 4, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                  {sourceType ? <Tag style={{ marginInlineEnd: 0 }}>{sourceType}</Tag> : null}
                  {url ? (
                    <Text type="secondary" style={{ fontSize: 12, minWidth: 0 }} ellipsis={{ tooltip: url }}>
                      <LinkOutlined style={{ marginRight: 4 }} />
                      {url}
                    </Text>
                  ) : null}
                </div>
              </div>
            </div>

            {summary ? (
              <Paragraph
                type="secondary"
                style={{ margin: '6px 0 0', fontSize: 12, lineHeight: 1.35 }}
                ellipsis={{ rows: 2, expandable: false, tooltip: summary }}
              >
                {summary}
              </Paragraph>
            ) : null}
          </button>
        );
      })}
    </div>
  );
};

export default TopSourcesList;
