import client from './client';

export const getProfile = () => client.get('/api/profile');
export const updateProfile = (data) => client.patch('/api/profile', data);
