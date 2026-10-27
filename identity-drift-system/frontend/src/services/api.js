import axios from 'axios';

export const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api', timeout: 6000 });

api.interceptors.response.use(
  (r) => r,
  (e) => {
    e.friendly = e.response?.data?.detail
      ? typeof e.response.data.detail === 'string' ? e.response.data.detail : 'Validation error'
      : e.request ? 'Backend unreachable — is uvicorn running on :8000?' : e.message;
    return Promise.reject(e);
  }
);

export const getData = async (path, fallback) => {
  try { return { data: (await api.get(path)).data, error: null }; }
  catch (e) { return { data: fallback, error: e.friendly }; }
};
export const post = (path, body) => api.post(path, body).then((r) => r.data);
export const ts = (s) => new Date(s.endsWith('Z') ? s : s + 'Z').toLocaleTimeString();
export const patch = (path, body) => api.patch(path, body).then((r) => r.data);
export const download = async (path, filename) => {
  const r = await api.get(path, { responseType: 'blob' });
  const url = URL.createObjectURL(r.data);
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url);
};
