import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 180000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('bydgeo_token');
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Topics
export const getTopics = () => api.get('/topics');
export const getTopic = (id: string) => api.get(`/topics/${id}`);
export const updatePrompt = (topicId: string, content: string) =>
  api.put(`/topics/${topicId}/prompt`, { content });
export const resetPrompt = (topicId: string) =>
  api.post(`/topics/${topicId}/prompt/reset`);
export const getPromptHistory = (topicId: string) =>
  api.get(`/topics/${topicId}/prompt/history`);
export const rollbackPrompt = (topicId: string, version: number) =>
  api.post(`/topics/${topicId}/prompt/rollback/${version}`);
export const updateDataSource = (topicId: string, path: string) =>
  api.put(`/topics/${topicId}/data-source`, null, { params: { path } });

// Analysis
export const runAnalysis = (topicId: string, model?: string, uploadedFiles: any[] = [], customTitle?: string, socialUpdatesLimit: number = 10) =>
  api.post('/analyze', { topic_id: topicId, model, uploaded_files: uploadedFiles, custom_title: customTitle, social_updates_limit: socialUpdatesLimit });
export const getAnalysisHistory = (topicId: string) =>
  api.get(`/analyze/history/${topicId}`);
export const getAnalysisResult = (id: string) =>
  api.get(`/analyze/result/${id}`);

// SSE stream
export const streamAnalysis = (
  topicId: string,
  model: string | undefined,
  onChunk: (text: string) => void,
  onDone: (data: any) => void,
  onError: (error: string) => void,
  customTitle?: string,
  socialUpdatesLimit: number = 10,
  forceRefresh: boolean = false,
) => {
  const controller = new AbortController();

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const token = localStorage.getItem('bydgeo_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  fetch(`${API_BASE}/analyze/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ topic_id: topicId, model, custom_title: customTitle, social_updates_limit: socialUpdatesLimit, force_refresh: forceRefresh }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      let currentEvent = 'message';
      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const raw = line.slice(6);
            try {
              const data = JSON.parse(raw);
              if (currentEvent === 'chunk') {
                onChunk(data.text || '');
              } else if (currentEvent === 'done') {
                onDone(data);
              } else if (currentEvent === 'error') {
                onError(data.error || 'Unknown error');
              }
            } catch {}
            currentEvent = 'message';
          } else if (line.trim() === '') {
            currentEvent = 'message';
          }
        }
      }
    })
    .catch((err) => onError(err.message));

  return controller;
};

// Reports - returns PDF binary
export const generateReport = (analysisId: string) =>
  api.post(`/reports/generate/${analysisId}`, null, { responseType: 'blob' });
export const listReports = (topicId: string) =>
  api.get(`/reports/list/${topicId}`);
export const deleteReport = (objectName: string) =>
  api.delete(`/reports/${objectName}`);

// Dashboard
export const getDashboard = (topicId: string) =>
  api.get(`/dashboard/${topicId}`);
export const getDashboardSources = (topicId: string) =>
  api.get(`/dashboard/${topicId}/sources`);
export const getDashboardSource = (topicId: string, sourceId: string) =>
  api.get(`/dashboard/${topicId}/sources/${sourceId}`);

// Models
export const getModels = () => api.get('/models');

// Settings
export const getSettings = () => api.get('/settings');
export const updateSettings = (payload: any) => api.put('/settings', payload);
export const testWebhook = (payload: any) => api.post('/settings/test-webhook', payload);

export default api;

export const uploadReferenceFile = async (topicId: string, file: File) => {
  const formData = new FormData();
  formData.append('topic_id', topicId);
  formData.append('file', file);
  const resp = await fetch('/api/analyze/upload-reference-local', { method: 'POST', body: formData });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
};


// Auth
export const login = (username: string, password: string) => api.post('/auth/login', { username, password });
export const logout = () => api.post('/auth/logout');
export const me = () => api.get('/auth/me');
export const getAuthConfig = () => api.get('/auth/config');
