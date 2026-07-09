import React, { useEffect, useState } from 'react';
import { Card, Typography, Switch, Input, Button, Space, message, Alert, Divider, Checkbox, List, Collapse, Tag } from 'antd';
import { useTranslation } from '../i18n/LanguageContext';
import { getSettings, updateSettings, testWebhook } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const SettingsPage: React.FC = () => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResults, setTestResults] = useState<any[]>([]);
  const [form, setForm] = useState<any>({
    general_webhook_enabled: false,
    general_webhook_url: '',
    general_webhook_secret: '',
    general_webhook_note: '',
    events: {
      analysis_completed: true,
      report_generated: false,
      upload_completed: false,
      error_alert: false,
    },
    targets: [
      { name: t('settings.tags.autoPush'), enabled: false, url: '', secret: '', description: t('settings.tags.autoPush') },
    ],
  });

  useEffect(() => {
    getSettings()
      .then((res) => setForm(res.data))
      .catch((err) => message.error(`${t('settings.saveFailed')}: ${err.message}`))
      .finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const res = await updateSettings(form);
      setForm(res.data);
      message.success(t('settings.configSaved'));
    } catch (err: any) {
      message.error(`${t('settings.saveFailed')}: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const test = async () => {
    setTesting(true);
    try {
      const res = await testWebhook(form);
      setTestResults(res.data.results || []);
      message.success(`${t('settings.testCompleted')}，${t('settings.successCount')} ${res.data.success_count || 0}，${t('settings.failureCount')} ${res.data.failure_count || 0}`);
    } catch (err: any) {
      setTestResults([]);
      message.error(`${t('settings.testFailed')}: ${err.response?.data?.detail || err.message}`);
    } finally {
      setTesting(false);
    }
  };

  const updateTarget = (index: number, patch: any) => {
    setForm((prev: any) => ({
      ...prev,
      targets: prev.targets.map((target: any, idx: number) => (idx === index ? { ...target, ...patch } : target)),
    }));
  };

  const addTarget = () => {
    setForm((prev: any) => ({
      ...prev,
      targets: [
        ...prev.targets,
        { name: `${t('settings.targetName')} ${prev.targets.length + 1}`, enabled: false, url: '', secret: '', description: '' },
      ],
    }));
  };

  return (
    <div>
      <Card style={{ marginBottom: 24, borderRadius: 20, background: 'linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%)', color: 'white', border: 'none', boxShadow: '0 16px 40px rgba(15,23,42,0.22)' }}>
        <Title level={3} style={{ marginBottom: 8, color: 'white' }}>{t('settings.title')}</Title>
        <Text style={{ color: 'rgba(255,255,255,0.8)' }}>{t('settings.subtitle')}</Text>
        <div style={{ marginTop: 14, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          <Tag color="blue">{t('settings.tags.autoPush')}</Tag>
          <Tag color="cyan">{t('settings.tags.multiTarget')}</Tag>
          <Tag color="geekblue">{t('settings.tags.errorAlert')}</Tag>
        </div>
      </Card>

      <Card loading={loading} title={t('settings.title')} style={{ borderRadius: 20, boxShadow: '0 10px 28px rgba(15,23,42,0.08)' }}>
        <Space direction="vertical" size={18} style={{ width: '100%' }}>
          <Alert
            type="info"
            showIcon
            message={t('settings.title')}
            description={
              <div>
                <Paragraph style={{ marginBottom: 8 }}>1. {t('settings.webhookEnabled')}。</Paragraph>
                <Paragraph style={{ marginBottom: 8 }}>2. {t('settings.targets')}。</Paragraph>
                <Paragraph style={{ marginBottom: 8 }}>3. {t('settings.events')}。</Paragraph>
                <Paragraph style={{ marginBottom: 8 }}>4. {t('settings.saveConfig')}，{t('settings.testWebhook')}。</Paragraph>
                <Paragraph style={{ marginBottom: 0 }}>5. {t('settings.subtitle')}</Paragraph>
              </div>
            }
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, padding: '14px 16px', borderRadius: 16, background: '#f8fbff', border: '1px solid #e5eefc' }}>
            <div>
              <Text strong>{t('settings.webhookEnabled')}</Text>
              <br />
              <Text type="secondary">{t('settings.webhookEnabledHint')}</Text>
            </div>
            <Switch checked={form.general_webhook_enabled} onChange={(checked) => setForm((prev: any) => ({ ...prev, general_webhook_enabled: checked }))} />
          </div>

          <div style={{ display: 'grid', gap: 12 }}>
            <div>
              <Text strong>{t('settings.webhookUrl')}</Text>
              <Input value={form.general_webhook_url} onChange={(e) => setForm((prev: any) => ({ ...prev, general_webhook_url: e.target.value }))} placeholder={t('settings.webhookUrlPlaceholder')} style={{ marginTop: 6 }} />
            </div>
            <div>
              <Text strong>{t('settings.webhookSecret')}</Text>
              <Input.Password value={form.general_webhook_secret} onChange={(e) => setForm((prev: any) => ({ ...prev, general_webhook_secret: e.target.value }))} placeholder={t('settings.webhookSecretPlaceholder')} style={{ marginTop: 6 }} />
            </div>
          </div>

          <div>
            <Text strong>{t('settings.events')}</Text>
            <div style={{ marginTop: 10, padding: '12px 16px', borderRadius: 16, background: '#fbfdff', border: '1px solid #eef2f7' }}>
              <Space direction="vertical">
                <Checkbox checked={form.events.analysis_completed} onChange={(e) => setForm((prev: any) => ({ ...prev, events: { ...prev.events, analysis_completed: e.target.checked } }))}>{t('settings.events.analysisCompleted')}</Checkbox>
                <Checkbox checked={form.events.report_generated} onChange={(e) => setForm((prev: any) => ({ ...prev, events: { ...prev.events, report_generated: e.target.checked } }))}>{t('settings.events.reportGenerated')}</Checkbox>
                <Checkbox checked={form.events.upload_completed} onChange={(e) => setForm((prev: any) => ({ ...prev, events: { ...prev.events, upload_completed: e.target.checked } }))}>{t('settings.events.uploadCompleted')}</Checkbox>
                <Checkbox checked={form.events.error_alert} onChange={(e) => setForm((prev: any) => ({ ...prev, events: { ...prev.events, error_alert: e.target.checked } }))}>{t('settings.events.errorAlert')}</Checkbox>
              </Space>
            </div>
          </div>

          <Divider orientation="left">{t('settings.targets')}</Divider>

          <List
            dataSource={form.targets}
            renderItem={(target: any, index: number) => (
              <List.Item style={{ padding: 0, marginBottom: 12, border: 'none' }}>
                <Card size="small" style={{ width: '100%', borderRadius: 16, border: '1px solid #e8eef7', boxShadow: '0 8px 20px rgba(15,23,42,0.05)' }}>
                  <Space direction="vertical" size={10} style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text strong>{target.name || `Webhook ${index + 1}`}</Text>
                      <Switch checked={target.enabled} onChange={(checked) => updateTarget(index, { enabled: checked })} />
                    </div>
                    <Input value={target.name} placeholder={t('settings.targetName')} onChange={(e) => updateTarget(index, { name: e.target.value })} />
                    <Input value={target.url} placeholder={t('settings.targetUrl')} onChange={(e) => updateTarget(index, { url: e.target.value })} />
                    <Input.Password value={target.secret} placeholder={t('settings.targetSecret')} onChange={(e) => updateTarget(index, { secret: e.target.value })} />
                    <TextArea rows={2} value={target.description} placeholder={t('settings.targetDescription')} onChange={(e) => updateTarget(index, { description: e.target.value })} />
                  </Space>
                </Card>
              </List.Item>
            )}
          />

          <Button onClick={addTarget}>{t('settings.addTarget')}</Button>

          <div>
            <Text strong>{t('settings.notes')}</Text>
            <TextArea rows={4} value={form.general_webhook_note} onChange={(e) => setForm((prev: any) => ({ ...prev, general_webhook_note: e.target.value }))} style={{ marginTop: 6 }} />
          </div>

          <Space wrap>
            <Button type="primary" onClick={save} loading={saving}>{t('settings.saveConfig')}</Button>
            <Button onClick={test} loading={testing}>{t('settings.testWebhook')}</Button>
          </Space>

          {testResults.length > 0 && (
            <Card size="small" title={t('settings.testResult')} style={{ borderRadius: 16, background: '#fbfdff' }}>
              <List
                size="small"
                dataSource={testResults}
                renderItem={(item: any) => (
                  <List.Item>
                    <Space direction="vertical" size={2} style={{ width: '100%' }}>
                      <Space wrap>
                        <Text strong>{item.target}</Text>
                        {item.ok ? <Text type="success">{t('settings.testResult.success')}</Text> : <Text type="danger">{t('settings.testResult.failed')}</Text>}
                        {item.status ? <Text type="secondary">{t('settings.testResult.statusCode')}: {item.status}</Text> : null}
                      </Space>
                      {item.detail ? <Text type="secondary">{t('settings.testResult.errorDetail')}: {item.detail}</Text> : null}
                      {item.response_preview ? <Text type="secondary">{t('settings.testResult.responsePreview')}: {item.response_preview}</Text> : null}
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          )}

          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            {t('settings.subtitle')}
          </Paragraph>
        </Space>
      </Card>
    </div>
  );
};

export default SettingsPage;
