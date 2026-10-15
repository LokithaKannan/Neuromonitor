import client from './client';

export const signup = (data) => client.post('/api/auth/signup', data);
export const login = (data) => client.post('/api/auth/login', data);
export const logout = () => client.post('/api/auth/logout');
export const getMe = () => client.get('/api/auth/me');
