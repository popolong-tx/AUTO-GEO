import React, { useState, useEffect } from 'react';
import {
  Modal, Input, Button, Space, Typography, List, Tag, Popconfirm, message,
} from 'antd';
import { ReloadOutlined, HistoryOutlined, RollbackOutlined } from '@ant-design/icons';
import { useTranslation } from '../i18n/LanguageContext';
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
  const { t, language } = useTranslation();
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
      message.error(t('promptEditor.saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    try {
      const res = await resetPrompt(topicId);
      setContent(res.data.prompt);
      message.success(t('promptEditor.resetSuccess'));
    } catch {
      message.error(t('promptEditor.resetFailed'));
    }
  };

  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await getPromptHistory(topicId);
      setHistory(res.data.versions);
      setShowHistory(true);
    } catch {
      message.error(t('promptEditor.historyFailed'));
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleRollback = async (version: number) => {
    try {
      const res = await rollbackPrompt(topicId, version);
      setContent(res.data.content);
      message.success(`${t('promptEditor.rollbackSuccess')} ${version}`);
      setShowHistory(false);
    } catch {
      message.error(t('promptEditor.rollbackFailed'));
    }
  };

  return (
    <Modal
      title={t('promptEditor.title')}
      open={open}
      onCancel={onClose}
      width={800}
      footer={
        <Space>
          <Button onClick={onClose}>{t('promptEditor.cancel')}</Button>
          <Popconfirm title={t('promptEditor.resetConfirm')} onConfirm={handleReset}>
            <Button icon={<ReloadOutlined />}>{t('promptEditor.reset')}</Button>
          </Popconfirm>
          <Button icon={<HistoryOutlined />} onClick={loadHistory} loading={loadingHistory}>
            {t('promptEditor.history')}
          </Button>
          <Button type="primary" onClick={handleSave} loading={saving}>
            {t('promptEditor.save')}
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
        {t('promptEditor.hint')}
      </Text>

      {showHistory && (
        <div style={{ marginTop: 16 }}>
          <Text strong>{t('promptEditor.history')}</Text>
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
                    {t('promptEditor.restore')}
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Text>{t('promptEditor.version')} {item.version}</Text>
                      {item.is_current && <Tag color="blue">{t('promptEditor.current')}</Tag>}
                    </Space>
                  }
                  description={
                    <Text type="secondary" ellipsis style={{ maxWidth: 400 }}>
                      {new Date(item.created_at).toLocaleString(language === 'zh' ? 'zh-CN' : 'en-US')} - {item.content.substring(0, 80)}...
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
