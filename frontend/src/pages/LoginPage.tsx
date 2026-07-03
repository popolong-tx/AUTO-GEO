import React, { useEffect, useState } from 'react';
import { Card, Form, Input, Button, Typography, message, Space, Tag } from 'antd';
import { useNavigate } from 'react-router-dom';
import { login, getAuthConfig } from '../services/api';

const { Title, Text } = Typography;

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [usernameHint, setUsernameHint] = useState('');

  useEffect(() => {
    getAuthConfig().then((res) => setUsernameHint(res.data.username || '')).catch(() => {});
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('bydgeo_token');
    if (token) {
      navigate('/', { replace: true });
    }
  }, [navigate]);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const resp = await login(values.username, values.password);
      localStorage.setItem('bydgeo_token', resp.data.token);
      message.success('登录成功');
      navigate('/');
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #081225 0%, #10284a 45%, #153766 100%)', padding: 24 }}>
      <Card style={{ width: 420, borderRadius: 18, boxShadow: '0 18px 48px rgba(0,0,0,0.28)' }}>
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Tag color="blue" style={{ width: 'fit-content' }}>BYD GEO 登录</Tag>
          <Title level={3} style={{ margin: 0 }}>舆情分析系统</Title>
          <Text type="secondary">请输入账号密码以继续访问分析看板</Text>
          {usernameHint ? <Text type="secondary">默认账号：{usernameHint}</Text> : null}
          <Form layout="vertical" onFinish={onFinish}>
            <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
              <Input placeholder="用户名" />
            </Form.Item>
            <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password placeholder="密码" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block size="large">登录</Button>
          </Form>
        </Space>
      </Card>
    </div>
  );
};

export default LoginPage;
