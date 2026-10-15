import client from './client';

export const generateReport = (sessionId) =>
  client.post(`/api/reports/${sessionId}`, {}, { responseType: 'blob' });
