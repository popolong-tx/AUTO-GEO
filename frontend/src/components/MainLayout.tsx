import React, { useState } from 'react';
import { Layout, Menu, Typography, Space, Tag, Button, message } from 'antd';
import {
  DashboardOutlined,
  ThunderboltOutlined,
  BarChartOutlined,
  BugOutlined,
  SafetyOutlined,
  FileTextOutlined,
  SettingOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { logout as apiLogout } from '../services/api';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '概览' },
  { key: '/topic/goodwood-festival', icon: <RocketOutlined />, label: 'Goodwood 活动' },
  { key: '/topic/flash-charge-launch', icon: <ThunderboltOutlined />, label: '闪充发布会' },
  { key: '/topic/q1-financial-report', icon: <BarChartOutlined />, label: 'Q1财报' },
  { key: '/topic/smart-chip-launch', icon: <BugOutlined />, label: '智驾芯片' },
  { key: '/topic/dod-1260h-list', icon: <SafetyOutlined />, label: '1260h清单' },
  { key: '/topic/custom-report', icon: <FileTextOutlined />, label: '通用报告' },
  { key: '/settings', icon: <SettingOutlined />, label: '配置中心' },
];

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const activeKey = location.pathname.startsWith('/topic/') || location.pathname === '/settings'
    ? location.pathname
    : '/';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          height: 76,
          lineHeight: '76px',
          background: 'linear-gradient(135deg, #081225 0%, #10284a 45%, #153766 100%)',
          boxShadow: '0 10px 24px rgba(8, 18, 37, 0.25)',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          overflow: 'hidden',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, minWidth: 0, flex: 1 }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 12,
              background: 'linear-gradient(135deg, #38bdf8 0%, #2563eb 55%, #1d4ed8 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontWeight: 'bold',
              fontSize: 14,
              boxShadow: '0 10px 22px rgba(37, 99, 235, 0.35)',
            }}
          >
            GEO
          </div>
          <div style={{ minWidth: 0, lineHeight: 1.25 }}>
            <Title
              level={4}
              style={{
                margin: 0,
                color: 'white',
                lineHeight: 1.2,
                fontSize: 22,
                whiteSpace: 'nowrap',
              }}
            >
              BYD 舆情分析系统
            </Title>
            <Text style={{ color: 'rgba(255,255,255,0.72)', fontSize: 12, whiteSpace: 'nowrap' }}>
              实时搜索 · 社交媒体 · 管理层洞察看板
            </Text>
          </div>
        </div>
        <Space wrap style={{ marginLeft: 16, flexShrink: 0 }}>
          <Tag color="blue">实时分析</Tag>
          <Tag color="cyan">Grok + Search</Tag>
          <Button size="small" onClick={async () => { localStorage.removeItem('bydgeo_token'); await apiLogout().catch(() => {}); message.success('已退出登录'); navigate('/login'); }}>退出登录</Button>
        </Space>
      </Header>
      <Layout>
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          width={236}
          style={{
            background: 'linear-gradient(180deg, #0d1b33 0%, #122745 100%)',
            borderRight: '1px solid rgba(255,255,255,0.08)',
            boxShadow: 'inset -1px 0 0 rgba(255,255,255,0.04)',
          }}
        >
          <div
            style={{
              padding: collapsed ? '12px 8px' : '16px 16px 8px',
            }}
          >
            {!collapsed && (
              <div
                style={{
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 14,
                  padding: '12px 14px',
                  color: 'rgba(255,255,255,0.86)',
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>分析导航</div>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.62)', lineHeight: 1.6 }}>
                  在专题、财报、风险、通用报告与配置中心间快速切换
                </div>
              </div>
            )}
          </div>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[activeKey]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{
              borderRight: 0,
              paddingTop: 8,
              background: 'transparent',
            }}
          />
        </Sider>
        <Content
          style={{
            padding: 28,
            background: 'transparent',
            minHeight: 'calc(100vh - 64px)',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
