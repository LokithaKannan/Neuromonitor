import client from './client';

export const createSession = (data) => client.post('/api/sessions', data);
export const listSessions = (skip = 0, limit = 50) =>
  client.get('/api/sessions', { params: { skip, limit } });
export const getSession = (id) => client.get(`/api/sessions/${id}`);
export const completeSession = (id) => client.patch(`/api/sessions/${id}/complete`);

export const saveTremorResult = (sessionId, data) =>
  client.post(`/api/sessions/${sessionId}/results/tremor`, data);
export const saveBlinkResult = (sessionId, data) =>
  client.post(`/api/sessions/${sessionId}/results/blink`, data);
export const saveAsymmetryResult = (sessionId, data) =>
  client.post(`/api/sessions/${sessionId}/results/asymmetry`, data);
export const savePtosisResult = (sessionId, data) =>
  client.post(`/api/sessions/${sessionId}/results/ptosis`, data);
