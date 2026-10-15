import { useState, useRef, useCallback, useEffect } from 'react';

export function useCamera() {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null);

  const startCamera = useCallback(async () => {
    setStatus('requesting');
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
        audio: false,
      });
      streamRef.current = stream;

      // Set status FIRST so the <video> element renders, then attach stream
      setStatus('active');

      // Use a tiny timeout to let React render the video element before srcObject assignment
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(() => {});
        }
      }, 50);

    } catch (err) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setStatus('denied');
        setError('Camera permission denied. Please allow camera access in your browser settings and reload.');
      } else if (err.name === 'NotFoundError') {
        setStatus('unavailable');
        setError('No camera device found. Please connect a webcam and try again.');
      } else {
        setStatus('error');
        setError(`Camera error: ${err.message}`);
      }
    }
  }, []);

  // When videoRef becomes available and we already have a stream, attach it
  // This handles the case where status='active' renders the video before srcObject is set
  const attachRef = useCallback((el) => {
    videoRef.current = el;
    if (el && streamRef.current) {
      el.srcObject = streamRef.current;
      el.play().catch(() => {});
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setStatus('idle');
  }, []);

  const captureFrame = useCallback((quality = 0.6) => {
    const video = videoRef.current;
    if (!video || !streamRef.current) return null;
    if (video.readyState < 2) return null; // HAVE_CURRENT_DATA
    const w = video.videoWidth || 640;
    const h = video.videoHeight || 480;
    if (w === 0 || h === 0) return null;
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    canvas.getContext('2d').drawImage(video, 0, 0);
    return canvas.toDataURL('image/jpeg', quality);
  }, []);

  useEffect(() => () => stopCamera(), [stopCamera]);

  return { videoRef, attachRef, status, error, startCamera, stopCamera, captureFrame };
}
