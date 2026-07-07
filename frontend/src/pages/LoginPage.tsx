import React, { useEffect, useState } from 'react';
import { Card, Form, Input, Button, Typography, message, Space, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from '../i18n/LanguageContext';
import { login, getAuthConfig } from '../services/api';
import LanguageSwitcher from '../components/LanguageSwitcher';

const { Title, Text } = Typography;

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [usernameHint, setUsernameHint] = useState('');

  useEffect(() => {
    getAuthConfig().then((res) => setUsernameHint(res.data.username || '')).catch(() => {});
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('autogeo_token');
    if (token) {
      navigate('/', { replace: true });
    }
  }, [navigate]);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const resp = await login(values.username, values.password);
      localStorage.setItem('autogeo_token', resp.data.token);
      message.success(t('login.success'));
      navigate('/');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || t('login.failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #081225 0%, #10284a 45%, #153766 100%)', padding: 24 }}>
      <Card style={{ width: 420, borderRadius: 18, boxShadow: '0 18px 48px rgba(0,0,0,0.28)' }}>
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Tag color="blue">AUTO GEO</Tag>
            <LanguageSwitcher size="small" />
          </div>
          <Title level={3} style={{ margin: 0 }}>{t('login.title')}</Title>
          <Text type="secondary">{t('login.subtitle')}</Text>
          {usernameHint ? <Text type="secondary">{t('login.defaultAccount')}：{usernameHint}</Text> : null}
          <Form layout="vertical" onFinish={onFinish}>
            <Form.Item name="username" label={t('login.username')} rules={[{ required: true, message: t('login.usernamePlaceholder') }]}>
              <Input placeholder={t('login.usernamePlaceholder')} />
            </Form.Item>
            <Form.Item name="password" label={t('login.password')} rules={[{ required: true, message: t('login.passwordPlaceholder') }]}>
              <Input.Password placeholder={t('login.passwordPlaceholder')} />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block size="large">{t('login.submit')}</Button>
          </Form>
        </Space>
      </Card>
    </div>
  );
};

export default LoginPage;
