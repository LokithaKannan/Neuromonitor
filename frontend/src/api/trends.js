import client from './client';

export const getTrends = (metric, limit = 20) =>
  client.get('/api/trends', { params: { metric, limit } });
