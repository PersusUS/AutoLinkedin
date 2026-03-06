import axios from 'axios';
import type { Lang } from '../types';

const api = axios.create({ baseURL: 'http://localhost:8000/api' });

export async function getStatus(): Promise<{ connected: boolean; name: string | null }> {
  const { data } = await api.get<{ connected: boolean; name: string | null }>('/linkedin/status');
  return data;
}

export function startOAuth(): void {
  window.location.href = 'http://localhost:8000/api/linkedin/auth';
}

export async function publishPost(
  postId: string,
  lang: Lang,
): Promise<{ ok: boolean; linkedin_post_id: string; lang: string }> {
  const { data } = await api.post<{ ok: boolean; linkedin_post_id: string; lang: string }>(
    '/linkedin/publish',
    { post_id: postId, lang },
  );
  return data;
}
