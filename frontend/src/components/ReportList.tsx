import React from 'react';
import { Table, Button, Space, Typography, Tag, Empty, Popconfirm, message } from 'antd';
import { DownloadOutlined, DeleteOutlined, FilePdfOutlined, ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from '../i18n/LanguageContext';

const { Text } = Typography;

interface ReportListProps {
  reports: any[];
  loading: boolean;
  onRefresh: () => void;
}

const ReportList: React.FC<ReportListProps> = ({ reports, loading, onRefresh }) => {
  const { t, language } = useTranslation();

  const handleDelete = async (topicId: string, reportId: string) => {
    try {
      const resp = await fetch(`/api/reports/${topicId}/${reportId}`, { method: 'DELETE' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      message.success(t('reports.deleted'));
      onRefresh();
    } catch {
      message.error(t('reports.deleteFailed'));
    }
  };

  const handleDownload = (report: any) => {
    fetch(`/api/reports/download/${report.topic_id}/${report.id}`)
      .then((res) => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.blob(); })
      .then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = report.filename || `AUTO_GEO_report_${Date.now()}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      })
      .catch(() => message.error(t('reports.downloadFailed')));
  };

  if (!loading && reports.length === 0) {
    return (
      <Empty
        description={t('reports.noReports')}
        style={{ padding: '24px 0' }}
      >
        <Button icon={<ReloadOutlined />} onClick={onRefresh}>
          {t('app.refresh')}
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
          <Text strong>{t('reports.title')}</Text>
          <Button icon={<ReloadOutlined />} size="small" onClick={onRefresh}>
            {t('app.refresh')}
          </Button>
        </Space>
      )}
      columns={[
        {
          title: t('reports.filename'),
          dataIndex: 'filename',
          key: 'filename',
          render: (_: any, item: any) => (
            <Space align="start">
              <FilePdfOutlined style={{ fontSize: 18, color: '#f56565', marginTop: 4 }} />
              <Space direction="vertical" size={0}>
                <Text>{item.filename || item.name?.split('/').pop() || t('reports.title')}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {item.created_at ? new Date(item.created_at).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US') : ''}
                  {item.topic_name ? ` · ${item.topic_name}` : ''}
                </Text>
              </Space>
            </Space>
          ),
        },
        {
          title: t('reports.size'),
          dataIndex: 'size',
          key: 'size',
          width: 100,
          render: (value: any) => <Tag>{value ? `${(Number(value) / 1024).toFixed(0)} KB` : '-'}</Tag>,
        },
        {
          title: t('reports.model'),
          dataIndex: 'model',
          key: 'model',
          width: 140,
          render: (value: any) => (value ? <Tag color="blue">{value}</Tag> : '-'),
        },
        {
          title: t('reports.actions'),
          key: 'actions',
          width: 150,
          render: (_: any, item: any) => (
            <Space size={0}>
              <Button type="link" icon={<DownloadOutlined />} onClick={() => handleDownload(item)}>
                {t('app.download')}
              </Button>
              <Popconfirm
                title={t('reports.deleteConfirm')}
                onConfirm={() => handleDelete(item.topic_id, item.id)}
              >
                <Button type="link" danger icon={<DeleteOutlined />}>
                  {t('app.delete')}
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
