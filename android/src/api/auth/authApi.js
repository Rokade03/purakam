import apiClient from '../client';

export const login = (email, password) =>
  apiClient.post('/auth/login', { email, password }).then((r) => r.data);

export const register = (payload) =>
  apiClient.post('/auth/register', payload).then((r) => r.data);

export const getMe = () => apiClient.get('/auth/me').then((r) => r.data);

export const googleLogin = (email, name) =>
  apiClient.post('/auth/google', { email, name }).then((r) => r.data);
