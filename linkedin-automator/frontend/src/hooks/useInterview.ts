import { useCallback, useRef, useState } from 'react';
import { useAudioStream } from './useAudioStream';
import type { InterviewStatus, TranscriptEntry, WsMessage } from '../types';

const WS_URL = 'ws://localhost:8000/api/interview/session';

interface UseInterviewReturn {
  start: () => void;
  end: () => void;
  transcript: TranscriptEntry[];
  isActive: boolean;
  isSpeaking: boolean;
  status: InterviewStatus;
  transcriptId: string | null;
}

export function useInterview(): UseInterviewReturn {
  const [status, setStatus] = useState<InterviewStatus>('idle');
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [transcriptId, setTranscriptId] = useState<string | null>(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const onAudioChunk = useCallback((base64: string) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'audio', data: base64 }));
    }
  }, []);

  const { startRecording, stopRecording, playAudio } = useAudioStream({ onAudioChunk });

  const start = useCallback(() => {
    if (status !== 'idle' && status !== 'done') return;

    setStatus('connecting');
    setTranscript([]);
    setTranscriptId(null);

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('active');
      startRecording();
    };

    ws.onmessage = (event: MessageEvent) => {
      const msg: WsMessage = JSON.parse(event.data as string);

      switch (msg.type) {
        case 'audio':
          if (msg.data) {
            playAudio(msg.data);
            setIsSpeaking(true);
          }
          break;

        case 'user_transcript':
          if (msg.data) {
            setTranscript((prev) => [...prev, { role: 'user', text: msg.data as string }]);
          }
          break;

        case 'ai_transcript':
          if (msg.data) {
            setTranscript((prev) => [...prev, { role: 'ai', text: msg.data as string }]);
          }
          break;

        case 'turn_complete':
          setIsSpeaking(false);
          break;

        case 'session_ended':
          setTranscriptId(msg.transcript_id ?? null);
          setStatus('done');
          break;

        case 'error':
          setStatus('idle');
          break;
      }
    };

    ws.onerror = () => {
      setStatus('idle');
      stopRecording();
    };

    ws.onclose = () => {
      setStatus((prev) => (prev === 'active' || prev === 'connecting') ? 'idle' : prev);
    };
  }, [status, startRecording, stopRecording, playAudio]);

  const end = useCallback(() => {
    setStatus('ending');
    stopRecording();

    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'end_session' }));
    }
  }, [stopRecording]);

  return {
    start,
    end,
    transcript,
    isActive: status === 'active',
    isSpeaking,
    status,
    transcriptId,
  };
}
