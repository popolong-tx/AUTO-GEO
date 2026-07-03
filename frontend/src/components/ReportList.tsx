import React from 'react';
import { Table, Button, Space, Typography, Tag, Empty, Popconfirm, message } from 'antd';
import { DownloadOutlined, DeleteOutlined, FilePdfOutlined, ReloadOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface ReportListProps {
  reports: any[];
  loading: boolean;
  onRefresh: () => void;
}

const ReportList: React.FC<ReportListProps> = ({ reports, loading, onRefresh }) => {
  const handleDelete = async (topicId: string, reportId: string) => {
    try {
      const resp = await fetch(`/api/reports/${topicId}/${reportId}`, { method: 'DELETE' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      message.success('报告已删除');
      onRefresh();
    } catch {
      message.error('删除失败');
    }
  };

  const handleDownload = (report: any) => {
    fetch(`/api/reports/download/${report.topic_id}/${report.id}`)
      .then((res) => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.blob(); })
      .then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = report.filename || `BYD_report_${Date.now()}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      })
      .catch(() => message.error('下载失败'));
  };

  if (!loading && reports.length === 0) {
    return (
      <Empty
        description="暂无报告，完成分析后可导出 PDF 报告"
        style={{ padding: '24px 0' }}
      >
        <Button icon={<ReloadOutlined />} onClick={onRefresh}>
          刷新
        </Button>
      </Empty>
    );
  }

  return (
    <Table
      size="small"
      loading={loading}
      pagination={false}
      rowKey={(record: any) => `${record.topic_id || 'topic'}-${record.id || record.name || record.filename}`}
      title={() => (
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Text strong>历史报告</Text>
          <Button icon={<ReloadOutlined />} size="small" onClick={onRefresh}>
            刷新
          </Button>
        </Space>
      )}
      columns={[
        {
          title: '报告',
          dataIndex: 'filename',
          key: 'filename',
          render: (_: any, item: any) => (
            <Space align="start">
              <FilePdfOutlined style={{ fontSize: 18, color: '#f56565', marginTop: 4 }} />
              <Space direction="vertical" size={0}>
                <Text>{item.filename || item.name?.split('/').pop() || '报告'}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {item.created_at ? new Date(item.created_at).toLocaleString('zh-CN') : ''}
                  {item.topic_name ? ` · ${item.topic_name}` : ''}
                </Text>
              </Space>
            </Space>
          ),
        },
        {
          title: '大小',
          dataIndex: 'size',
          key: 'size',
          width: 100,
          render: (value: any) => <Tag>{value ? `${(Number(value) / 1024).toFixed(0)} KB` : '-'}</Tag>,
        },
        {
          title: '模型',
          dataIndex: 'model',
          key: 'model',
          width: 140,
          render: (value: any) => (value ? <Tag color="blue">{value}</Tag> : '-'),
        },
        {
          title: '操作',
          key: 'actions',
          width: 150,
          render: (_: any, item: any) => (
            <Space size={0}>
              <Button type="link" icon={<DownloadOutlined />} onClick={() => handleDownload(item)}>
                下载
              </Button>
              <Popconfirm
                title="确认删除此报告？"
                onConfirm={() => handleDelete(item.topic_id, item.id)}
              >
                <Button type="link" danger icon={<DeleteOutlined />}>
                  删除
                </Button>
              </Popconfirm>
            </Space>
          ),
        },
      ]}
      dataSource={reports}
    />
  );
};

export default ReportList;
