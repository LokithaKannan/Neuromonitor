import { useState, useRef, useCallback, useEffect } from 'react';

// During dev, Vite proxies /ws → ws://localhost:8000
// In production set VITE_WS_URL explicitly
const WS_BASE = import.meta.env.VITE_WS_URL
  ? import.meta.env.VITE_WS_URL.replace(/\/$/, '')
  : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`;

export function useMonitoringWS({ sessionId, modules, onResult, onSummary, onError }) {
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);

  // Keep callbacks in refs so the WS message handler always has current versions
  const onResultRef  = useRef(onResult);
  const onSummaryRef = useRef(onSummary);
  const onErrorRef   = useRef(onError);
  useEffect(() => { onResultRef.current  = onResult;  }, [onResult]);
  useEffect(() => { onSummaryRef.current = onSummary; }, [onSummary]);
  useEffect(() => { onErrorRef.current   = onError;   }, [onError]);

  const connect = useCallback(() => {
    const token = localStorage.getItem('access_token');
    if (!token || !sessionId) {
      onErrorRef.current?.('No auth token or session ID');
      return;
    }

    // Close any existing connection first
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConnecting(true);
    setConnected(false);

    // Build module string — do NOT encode commas so backend can split on ","
    const moduleStr = Array.isArray(modules) ? modules.join(',') : (modules || '');

    // Use plain string concatenation — avoid encodeURIComponent on the modules param
    // token must be encoded since it contains dots and other chars
    const url = `${WS_BASE}/ws/monitoring/${sessionId}?token=${encodeURIComponent(token)}&modules=${moduleStr}`;

    console.log('[WS] Connecting to:', url.replace(/token=[^&]+/, 'token=***'));

    let ws;
    try {
      ws = new WebSocket(url);
    } catch (err) {
      setConnecting(false);
      onErrorRef.current?.(`Failed to create WebSocket: ${err.message}`);
      return;
    }

    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WS] Connected');
      setConnected(true);
      setConnecting(false);
    };

    ws.onclose = (evt) => {
      console.log('[WS] Closed', evt.code, evt.reason);
      setConnected(false);
      setConnecting(false);
      if (evt.code === 4001) {
        onErrorRef.current?.('Authentication failed. Please sign in again.');
      }
    };

    ws.onerror = (evt) => {
      console.error('[WS] Error', evt);
      setConnected(false);
      setConnecting(false);
      onErrorRef.current?.('WebSocket connection failed. Make sure the backend is running on port 8000.');
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'result')  onResultRef.current?.(msg);
        else if (msg.type === 'summary') onSummaryRef.current?.(msg.data);
        else if (msg.type === 'error')   onErrorRef.current?.(msg.message);
        else if (msg.type === 'pong')    { /* heartbeat ok */ }
      } catch (e) {
        console.warn('[WS] Could not parse message', e);
      }
    };
  }, [sessionId, modules]); // stable — callbacks handled via refs

  const sendFrame = useCallback((base64Frame, requestedModules) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return false;
    wsRef.current.send(JSON.stringify({
      type: 'frame',
      data: base64Frame,
      modules: requestedModules,
    }));
    return true;
  }, []);

  const sendStop = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'stop' }));
    }
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
    setConnecting(false);
  }, []);

  useEffect(() => () => disconnect(), [disconnect]);

  return { connect, disconnect, sendFrame, sendStop, connected, connecting };
}
