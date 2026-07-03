import React, { useEffect, useState } from 'react';
import { Card, Typography, Switch, Input, Button, Space, message, Alert, Divider, Checkbox, List, Collapse, Tag, Typography as AntTypography } from 'antd';
import { getSettings, updateSettings, testWebhook } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const SettingsPage: React.FC = () => {
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
      { name: '默认Webhook', enabled: false, url: '', secret: '', description: '默认通用通知目标' },
    ],
  });

  useEffect(() => {
    getSettings()
      .then((res) => setForm(res.data))
      .catch((err) => message.error(`加载配置失败: ${err.message}`))
      .finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const res = await updateSettings(form);
      setForm(res.data);
      message.success('配置已保存');
    } catch (err: any) {
      message.error(`保存失败: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const test = async () => {
    setTesting(true);
    try {
      const res = await testWebhook(form);
      setTestResults(res.data.results || []);
      message.success(`Webhook 测试完成，成功 ${res.data.success_count || 0} 个目标，失败 ${res.data.failure_count || 0} 个目标`);
    } catch (err: any) {
      setTestResults([]);
      message.error(`Webhook 测试失败: ${err.response?.data?.detail || err.message}`);
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
        { name: `Webhook ${prev.targets.length + 1}`, enabled: false, url: '', secret: '', description: '' },
      ],
    }));
  };

  return (
    <div>
      <Card style={{ marginBottom: 24, borderRadius: 20, background: 'linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%)', color: 'white', border: 'none', boxShadow: '0 16px 40px rgba(15,23,42,0.22)' }}>
        <Title level={3} style={{ marginBottom: 8, color: 'white' }}>配置中心</Title>
        <Text style={{ color: 'rgba(255,255,255,0.8)' }}>开放通用信息 Webhook，支持通知其他系统，或被龙虾及其他平台回调/调用。</Text>
        <div style={{ marginTop: 14, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          <Tag color="blue">自动推送</Tag>
          <Tag color="cyan">多目标</Tag>
          <Tag color="geekblue">失败告警</Tag>
        </div>
      </Card>

      <Card loading={loading} title="通用集成配置中心" style={{ borderRadius: 20, boxShadow: '0 10px 28px rgba(15,23,42,0.08)' }}>
        <Space direction="vertical" size={18} style={{ width: '100%' }}>
          <Alert
            type="info"
            showIcon
            message="使用方法"
            description={
              <div>
                <Paragraph style={{ marginBottom: 8 }}>1. 先开启“通用信息 Webhook”。</Paragraph>
                <Paragraph style={{ marginBottom: 8 }}>2. 在下方配置一个或多个目标系统（名称 / URL / Secret / 描述）。</Paragraph>
                <Paragraph style={{ marginBottom: 8 }}>3. 选择希望通知的事件类型，如“分析完成”“报告导出”“上传完成”“失败告警”。</Paragraph>
                <Paragraph style={{ marginBottom: 8 }}>4. 点击“保存配置”，再点击“测试 Webhook”验证目标系统是否能收到请求。</Paragraph>
                <Paragraph style={{ marginBottom: 8 }}>5. 外部系统（例如龙虾）可将其作为统一入口，接收来自 BYDGEO 的标准 JSON 通知。</Paragraph>
                <Paragraph style={{ marginBottom: 8 }}>6. 当前已接入“分析完成自动推送”：当分析结束后，若已启用目标系统且“分析完成”事件已勾选，系统会自动向目标 Webhook 推送摘要、模型、情绪分布与内容预览。</Paragraph>
                <Paragraph style={{ marginBottom: 0 }}>7. 当前已接入“错误告警自动推送”：若分析失败、超时或流式分析异常，且“失败告警”已勾选，系统会自动推送错误类型、主题、标题与错误信息到目标 Webhook。</Paragraph>
              </div>
            }
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, padding: '14px 16px', borderRadius: 16, background: '#f8fbff', border: '1px solid #e5eefc' }}>
            <div>
              <Text strong>启用通用信息 Webhook</Text>
              <br />
              <Text type="secondary">开启后支持统一对外通知与外部系统联动。</Text>
            </div>
            <Switch checked={form.general_webhook_enabled} onChange={(checked) => setForm((prev: any) => ({ ...prev, general_webhook_enabled: checked }))} />
          </div>

          <div style={{ display: 'grid', gap: 12 }}>
            <div>
              <Text strong>默认 Webhook URL（兼容旧模式）</Text>
              <Input value={form.general_webhook_url} onChange={(e) => setForm((prev: any) => ({ ...prev, general_webhook_url: e.target.value }))} placeholder="例如：https://your-system.example.com/webhook/bydgeo" style={{ marginTop: 6 }} />
            </div>
            <div>
              <Text strong>默认 Webhook Secret（兼容旧模式）</Text>
              <Input.Password value={form.general_webhook_secret} onChange={(e) => setForm((prev: any) => ({ ...prev, general_webhook_secret: e.target.value }))} placeholder="用于请求头 X-BYDGEO-Webhook-Secret" style={{ marginTop: 6 }} />
            </div>
          </div>

          <div>
            <Text strong>事件开关</Text>
            <div style={{ marginTop: 10, padding: '12px 16px', borderRadius: 16, background: '#fbfdff', border: '1px solid #eef2f7' }}>
              <Space direction="vertical">
                <Checkbox checked={form.events.analysis_completed} onChange={(e) => setForm((prev: any) => ({ ...prev, events: { ...prev.events, analysis_completed: e.target.checked } }))}>分析完成</Checkbox>
                <Checkbox checked={form.events.report_generated} onChange={(e) => setForm((prev: any) => ({ ...prev, events: { ...prev.events, report_generated: e.target.checked } }))}>报告导出</Checkbox>
                <Checkbox checked={form.events.upload_completed} onChange={(e) => setForm((prev: any) => ({ ...prev, events: { ...prev.events, upload_completed: e.target.checked } }))}>上传完成</Checkbox>
                <Checkbox checked={form.events.error_alert} onChange={(e) => setForm((prev: any) => ({ ...prev, events: { ...prev.events, error_alert: e.target.checked } }))}>失败告警</Checkbox>
              </Space>
            </div>
          </div>

          <Divider orientation="left">目标系统列表</Divider>

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
                    <Input value={target.name} placeholder="目标名称" onChange={(e) => updateTarget(index, { name: e.target.value })} />
                    <Input value={target.url} placeholder="目标 URL" onChange={(e) => updateTarget(index, { url: e.target.value })} />
                    <Input.Password value={target.secret} placeholder="目标 Secret" onChange={(e) => updateTarget(index, { secret: e.target.value })} />
                    <TextArea rows={2} value={target.description} placeholder="目标说明（例如：龙虾通知入口 / BI 平台 / 审批系统）" onChange={(e) => updateTarget(index, { description: e.target.value })} />
                  </Space>
                </Card>
              </List.Item>
            )}
          />

          <Button onClick={addTarget}>新增目标系统</Button>

          <div>
            <Text strong>备注</Text>
            <TextArea rows={4} value={form.general_webhook_note} onChange={(e) => setForm((prev: any) => ({ ...prev, general_webhook_note: e.target.value }))} style={{ marginTop: 6 }} />
          </div>

          <Space wrap>
            <Button type="primary" onClick={save} loading={saving}>保存配置</Button>
            <Button onClick={test} loading={testing}>测试 Webhook</Button>
          </Space>

          {testResults.length > 0 && (
            <Card size="small" title="测试结果" style={{ borderRadius: 16, background: '#fbfdff' }}>
              <List
                size="small"
                dataSource={testResults}
                renderItem={(item: any) => (
                  <List.Item>
                    <Space direction="vertical" size={2} style={{ width: '100%' }}>
                      <Space wrap>
                        <Text strong>{item.target}</Text>
                        {item.ok ? <Text type="success">成功</Text> : <Text type="danger">失败</Text>}
                        {item.status ? <Text type="secondary">状态码: {item.status}</Text> : null}
                      </Space>
                      {item.detail ? <Text type="secondary">错误详情: {item.detail}</Text> : null}
                      {item.response_preview ? <Text type="secondary">返回预览: {item.response_preview}</Text> : null}
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          )}

          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            当前约定：系统测试请求会向目标地址发送 JSON，并携带请求头 <Text code>X-BYDGEO-Webhook-Secret</Text>。后续若接入自动推送事件，可直接复用这套配置。
          </Paragraph>
        </Space>
      </Card>
    </div>
  );
};

export default SettingsPage;
