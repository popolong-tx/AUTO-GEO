import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import enUS from 'antd/locale/en_US';
import { LanguageProvider, useLanguage } from './i18n/LanguageContext';
import MainLayout from './components/MainLayout';
import HomePage from './pages/HomePage';
import TopicPage from './pages/TopicPage';
import SettingsPage from './pages/SettingsPage';
import LoginPage from './pages/LoginPage';
import RequireAuth from './components/RequireAuth';
import { theme } from './styles/theme';
import './styles/global.css';

const AppRoutes: React.FC = () => {
  const { language } = useLanguage();
  const antdLocale = language === 'zh' ? zhCN : enUS;

  return (
    <ConfigProvider theme={theme} locale={antdLocale}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireAuth><MainLayout /></RequireAuth>}>
            <Route path="/" element={<HomePage />} />
            <Route path="/topic/:topicId" element={<TopicPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

const App: React.FC = () => {
  return (
    <LanguageProvider>
      <AppRoutes />
    </LanguageProvider>
  );
};

export default App;
