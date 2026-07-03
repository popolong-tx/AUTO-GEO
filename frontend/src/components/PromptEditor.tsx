import React, { useState, useEffect } from 'react';
import {
  Modal, Input, Button, Space, Typography, List, Tag, Popconfirm, message,
} from 'antd';
import { ReloadOutlined, HistoryOutlined, RollbackOutlined } from '@ant-design/icons';
import { updatePrompt, resetPrompt, getPromptHistory, rollbackPrompt } from '../services/api';

const { TextArea } = Input;
const { Text } = Typography;

interface PromptEditorProps {
  open: boolean;
  topicId: string;
  currentPrompt: string;
  onClose: () => void;
  onSaved: (newPrompt: string) => void;
}

const PromptEditor: React.FC<PromptEditorProps> = ({
  open, topicId, currentPrompt, onClose, onSaved,
}) => {
  const [content, setContent] = useState(currentPrompt);
  const [saving, setSaving] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    setContent(currentPrompt);
  }, [currentPrompt]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updatePrompt(topicId, content);
      onSaved(content);
    } catch {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    try {
      const res = await resetPrompt(topicId);
      setContent(res.data.prompt);
      message.success('已恢复默认提示词');
    } catch {
      message.error('重置失败');
    }
  };

  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await getPromptHistory(topicId);
      setHistory(res.data.versions);
      setShowHistory(true);
    } catch {
      message.error('加载历史失败');
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleRollback = async (version: number) => {
    try {
      const res = await rollbackPrompt(topicId, version);
      setContent(res.data.content);
      message.success(`已回滚到版本 ${version}`);
      setShowHistory(false);
    } catch {
      message.error('回滚失败');
    }
  };

  return (
    <Modal
      title="编辑分析提示词"
      open={open}
      onCancel={onClose}
      width={800}
      footer={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Popconfirm title="确认恢复默认提示词？" onConfirm={handleReset}>
            <Button icon={<ReloadOutlined />}>恢复默认</Button>
          </Popconfirm>
          <Button icon={<HistoryOutlined />} onClick={loadHistory} loading={loadingHistory}>
            历史版本
          </Button>
          <Button type="primary" onClick={handleSave} loading={saving}>
            保存
          </Button>
        </Space>
      }
    >
      <TextArea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={15}
        style={{ fontFamily: 'monospace', fontSize: 13 }}
        showCount
        maxLength={5000}
      />
      <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
        提示词将用于指导 Grok 模型的分析方向和输出结构
      </Text>

      {showHistory && (
        <div style={{ marginTop: 16 }}>
          <Text strong>历史版本</Text>
          <List
            size="small"
            dataSource={history}
            style={{ maxHeight: 200, overflow: 'auto', marginTop: 8 }}
            renderItem={(item: any) => (
              <List.Item
                actions={[
                  <Button
                    size="small"
                    icon={<RollbackOutlined />}
                    onClick={() => handleRollback(item.version)}
                  >
                    恢复
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Text>版本 {item.version}</Text>
                      {item.is_current && <Tag color="blue">当前</Tag>}
                    </Space>
                  }
                  description={
                    <Text type="secondary" ellipsis style={{ maxWidth: 400 }}>
                      {new Date(item.created_at).toLocaleString('zh-CN')} - {item.content.substring(0, 80)}...
                    </Text>
                  }
                />
              </List.Item>
            )}
          />
        </div>
      )}
    </Modal>
  );
};

export default PromptEditor;
