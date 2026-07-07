import React from 'react';
import { Select, Space, Typography } from 'antd';
import { GlobalOutlined } from '@ant-design/icons';
import { useLanguage, Language } from '../i18n/LanguageContext';

const { Text } = Typography;

const languageOptions = [
  { value: 'zh', label: '简体中文' },
  { value: 'en', label: 'English' },
];

interface LanguageSwitcherProps {
  size?: 'small' | 'middle' | 'large';
  showLabel?: boolean;
  style?: React.CSSProperties;
}

const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({
  size = 'small',
  showLabel = false,
  style,
}) => {
  const { language, setLanguage } = useLanguage();

  return (
    <Space size={4} style={style}>
      <GlobalOutlined style={{ color: 'rgba(255,255,255,0.72)', fontSize: 14 }} />
      <Select
        size={size}
        value={language}
        onChange={(value: Language) => setLanguage(value)}
        options={languageOptions}
        style={{ width: 110 }}
        bordered={false}
        popupMatchSelectWidth={false}
      />
    </Space>
  );
};

export default LanguageSwitcher;
