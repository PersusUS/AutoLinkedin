import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { listPosts, updatePostContent } from '../api/posts';
import { publishPost } from '../api/linkedin';
import type { Post, Lang } from '../types';

const LANGS: { key: Lang; label: string }[] = [
  { key: 'es', label: '🇪🇸 Español' },
  { key: 'en', label: '🇬🇧 English' },
  { key: 'zh', label: '🇨🇳 中文' },
];

function contentKey(lang: Lang): keyof Post {
  return `content_${lang}` as keyof Post;
}
function publishedIdKey(lang: Lang): keyof Post {
  return `linkedin_post_id_${lang}` as keyof Post;
}

export default function Review() {
  const { transcriptId } = useParams<{ transcriptId: string }>();
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);

  // Poll until posts appear
  useEffect(() => {
    if (!transcriptId) return;
    let cancelled = false;

    const poll = async () => {
      const result = await listPosts(transcriptId);
      if (cancelled) return;
      if (result.length > 0) {
        setPosts(result);
        setLoading(false);
        clearInterval(id);
      }
    };

    poll();
    const id = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [transcriptId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-32">
        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-gray-500 text-sm">Gemini está generando tus posts...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Review de Posts</h1>
      <p className="text-sm text-gray-500">{posts.length} post{posts.length !== 1 && 's'} generado{posts.length !== 1 && 's'}</p>
      {posts.map((post) => (
        <PostCard key={post.id} post={post} onUpdate={(updated) => {
          setPosts((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
        }} />
      ))}
    </div>
  );
}

function PostCard({ post, onUpdate }: { post: Post; onUpdate: (p: Post) => void }) {
  const [activeLang, setActiveLang] = useState<Lang>('es');
  const [content, setContent] = useState(post[contentKey(activeLang)] as string);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync content when switching tabs
  useEffect(() => {
    setContent(post[contentKey(activeLang)] as string);
  }, [activeLang, post]);

  const saveContent = useCallback(
    (value: string) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(async () => {
        setSaving(true);
        await updatePostContent(post.id, activeLang, value);
        onUpdate({ ...post, [contentKey(activeLang)]: value });
        setSaving(false);
      }, 1500);
    },
    [post, activeLang, onUpdate],
  );

  const handleChange = (value: string) => {
    setContent(value);
    saveContent(value);
  };

  const handlePublish = async () => {
    setShowConfirm(false);
    setPublishing(true);
    try {
      const result = await publishPost(post.id, activeLang);
      onUpdate({
        ...post,
        [publishedIdKey(activeLang)]: result.linkedin_post_id,
        [`published_at_${activeLang}`]: new Date().toISOString(),
      });
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Error al publicar');
    } finally {
      setPublishing(false);
    }
  };

  const isPublished = Boolean(post[publishedIdKey(activeLang)]);
  const charCount = content.length;
  const overLimit = charCount > 3000;

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100">
        <h3 className="font-semibold text-gray-900">{post.post_title}</h3>
        <p className="text-xs text-gray-500 mt-0.5">{post.topic}</p>
      </div>

      {/* Language tabs */}
      <div className="flex border-b border-gray-100">
        {LANGS.map(({ key, label }) => {
          const published = Boolean(post[publishedIdKey(key)]);
          return (
            <button
              key={key}
              onClick={() => setActiveLang(key)}
              className={`flex-1 py-2.5 text-sm font-medium transition-colors relative ${
                activeLang === key
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {label}
              {published && <span className="ml-1 text-green-500 text-xs">✓</span>}
            </button>
          );
        })}
      </div>

      {/* Content area */}
      <div className="p-5">
        <textarea
          value={content}
          onChange={(e) => handleChange(e.target.value)}
          rows={10}
          className="w-full border border-gray-200 rounded-lg p-3 text-sm text-gray-800 resize-y focus:outline-none focus:ring-2 focus:ring-blue-300"
        />

        {/* Footer: char count + actions */}
        <div className="flex items-center justify-between mt-3">
          <div className="flex items-center gap-3">
            <span className={`text-xs ${overLimit ? 'text-red-600 font-semibold' : 'text-gray-400'}`}>
              {charCount}/3000
            </span>
            {saving && <span className="text-xs text-gray-400">Guardando...</span>}
          </div>

          <div className="flex items-center gap-2">
            {isPublished ? (
              <span className="text-xs text-green-600 font-medium">Publicado ✓</span>
            ) : (
              <button
                onClick={() => setShowConfirm(true)}
                disabled={publishing || overLimit}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {publishing ? 'Publicando...' : 'Publicar'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Confirm modal */}
      {showConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-sm mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">¿Publicar en LinkedIn?</h3>
            <p className="text-gray-600 text-sm mb-4">
              Se publicará la versión en {LANGS.find((l) => l.key === activeLang)?.label}.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowConfirm(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 text-sm font-medium"
              >
                Cancelar
              </button>
              <button
                onClick={handlePublish}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
              >
                Sí, publicar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
