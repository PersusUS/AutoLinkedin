import { useCallback, useRef, useState } from 'react';

const INPUT_SAMPLE_RATE = 16000;
const OUTPUT_SAMPLE_RATE = 24000;
const CHUNK_SIZE = 1024;

const WORKLET_CODE = `
class PCM16Processor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = new Float32Array(0);
  }
  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;
    const channel = input[0];
    const merged = new Float32Array(this._buffer.length + channel.length);
    merged.set(this._buffer);
    merged.set(channel, this._buffer.length);
    this._buffer = merged;
    while (this._buffer.length >= ${CHUNK_SIZE}) {
      const chunk = this._buffer.slice(0, ${CHUNK_SIZE});
      this._buffer = this._buffer.slice(${CHUNK_SIZE});
      const pcm16 = new Int16Array(chunk.length);
      for (let i = 0; i < chunk.length; i++) {
        const s = Math.max(-1, Math.min(1, chunk[i]));
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }
      const bytes = new Uint8Array(pcm16.buffer);
      this.port.postMessage(bytes);
    }
    return true;
  }
}
registerProcessor('pcm16-processor', PCM16Processor);
`;

interface UseAudioStreamOptions {
  onAudioChunk: (base64: string) => void;
}

interface UseAudioStreamReturn {
  isRecording: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  playAudio: (base64: string) => void;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export function useAudioStream({ onAudioChunk }: UseAudioStreamOptions): UseAudioStreamReturn {
  const [isRecording, setIsRecording] = useState(false);
  const streamRef = useRef<MediaStream | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const workletRef = useRef<AudioWorkletNode | null>(null);
  const playContextRef = useRef<AudioContext | null>(null);

  const startRecording = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;

    const audioCtx = new AudioContext({ sampleRate: INPUT_SAMPLE_RATE });
    contextRef.current = audioCtx;

    const blob = new Blob([WORKLET_CODE], { type: 'application/javascript' });
    const url = URL.createObjectURL(blob);
    await audioCtx.audioWorklet.addModule(url);
    URL.revokeObjectURL(url);

    const source = audioCtx.createMediaStreamSource(stream);
    const worklet = new AudioWorkletNode(audioCtx, 'pcm16-processor');
    workletRef.current = worklet;

    worklet.port.onmessage = (e: MessageEvent<Uint8Array>) => {
      const b64 = arrayBufferToBase64(e.data.buffer as ArrayBuffer);
      onAudioChunk(b64);
    };

    source.connect(worklet);
    worklet.connect(audioCtx.destination);
    setIsRecording(true);
  }, [onAudioChunk]);

  const stopRecording = useCallback(() => {
    workletRef.current?.disconnect();
    workletRef.current = null;

    contextRef.current?.close();
    contextRef.current = null;

    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;

    setIsRecording(false);
  }, []);

  const playAudio = useCallback((base64: string) => {
    if (!playContextRef.current || playContextRef.current.state === 'closed') {
      playContextRef.current = new AudioContext({ sampleRate: OUTPUT_SAMPLE_RATE });
    }
    const ctx = playContextRef.current;

    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }

    const pcm16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) {
      float32[i] = pcm16[i] / (pcm16[i] < 0 ? 0x8000 : 0x7FFF);
    }

    const buffer = ctx.createBuffer(1, float32.length, OUTPUT_SAMPLE_RATE);
    buffer.getChannelData(0).set(float32);

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.start();
  }, []);

  return { isRecording, startRecording, stopRecording, playAudio };
}
