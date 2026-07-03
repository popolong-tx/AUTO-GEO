import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { me } from '../services/api';

const RequireAuth: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const [ok, setOk] = useState<boolean | null>(null);
  const location = useLocation();

  useEffect(() => {
    const token = localStorage.getItem('bydgeo_token');
    if (!token) {
      setOk(false);
      return;
    }
    me().then(() => setOk(true)).catch(() => {
      localStorage.removeItem('bydgeo_token');
      setOk(false);
    });
  }, []);

  if (ok === null) return <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Spin size="large" /></div>;
  if (!ok) return <Navigate to="/login" replace state={{ from: location }} />;
  return children;
};

export default RequireAuth;
