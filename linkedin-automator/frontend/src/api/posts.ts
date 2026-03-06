import axios from 'axios';
import type { Post, Lang } from '../types';

const api = axios.create({ baseURL: 'http://localhost:8000/api' });

export async function generatePosts(
  transcriptId: string,
  transcriptText: string,
): Promise<Post[]> {
  const { data } = await api.post<{ posts: Post[] }>('/posts/generate', {
    transcript_id: transcriptId,
    transcript_text: transcriptText,
  });
  return data.posts;
}

export async function listPosts(transcriptId?: string): Promise<Post[]> {
  const params: Record<string, string> = {};
  if (transcriptId) params.transcript_id = transcriptId;
  const { data } = await api.get<Post[]>('/posts', { params });
  return data;
}

export async function getPost(id: string): Promise<Post> {
  const { data } = await api.get<Post>(`/posts/${id}`);
  return data;
}

export async function updatePostContent(
  id: string,
  lang: Lang,
  content: string,
): Promise<void> {
  await api.patch(`/posts/${id}`, { lang, content });
}
