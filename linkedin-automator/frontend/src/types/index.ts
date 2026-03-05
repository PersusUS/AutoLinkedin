export interface Post {
  id: string;
  created_at: string;
  transcript_id: string;
  post_title: string;
  topic: string;
  content_es: string;
  content_en: string;
  content_zh: string;
  status: string;
  linkedin_post_id_es?: string;
  linkedin_post_id_en?: string;
  linkedin_post_id_zh?: string;
  published_at_es?: string;
  published_at_en?: string;
  published_at_zh?: string;
}

export type InterviewStatus = 'idle' | 'connecting' | 'active' | 'ending' | 'done';
export type Lang = 'es' | 'en' | 'zh';

export interface TranscriptEntry {
  role: 'user' | 'ai';
  text: string;
}

export interface WsMessage {
  type: 'audio' | 'user_transcript' | 'ai_transcript' | 'turn_complete' | 'session_ended' | 'error';
  data: string | null;
  transcript_id?: string;
  transcript?: string;
}
