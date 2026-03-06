import { useEffect, useState } from 'react';
import { listPosts } from '../api/posts';
import type { Post, Lang } from '../types';

const LANG_FLAGS: Record<Lang, string> = { es: '🇪🇸', en: '🇬🇧', zh: '🇨🇳' };

export default function History() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listPosts().then((data) => {
      setPosts(data);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (posts.length === 0) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Historial</h1>
        <p className="text-gray-500 text-sm">No hay posts todavía. Inicia una entrevista para generar contenido.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Historial</h1>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-left text-gray-500">
              <th className="px-5 py-3 font-medium">Fecha</th>
              <th className="px-5 py-3 font-medium">Tema</th>
              <th className="px-5 py-3 font-medium">Preview</th>
              <th className="px-5 py-3 font-medium text-center">Publicado</th>
            </tr>
          </thead>
          <tbody>
            {posts.map((post) => (
              <tr key={post.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                <td className="px-5 py-3 text-gray-600 whitespace-nowrap">
                  {new Date(post.created_at).toLocaleDateString()}
                </td>
                <td className="px-5 py-3 font-medium text-gray-800">{post.topic}</td>
                <td className="px-5 py-3 text-gray-500 max-w-xs truncate">
                  {post.content_es.slice(0, 150)}
                </td>
                <td className="px-5 py-3 text-center space-x-1">
                  {(['es', 'en', 'zh'] as Lang[]).map((lang) => {
                    const pid = post[`linkedin_post_id_${lang}` as keyof Post] as string | undefined;
                    return (
                      <span key={lang} title={lang.toUpperCase()}>
                        {pid ? (
                          <span className="text-green-500">{LANG_FLAGS[lang]}</span>
                        ) : (
                          <span className="opacity-30">{LANG_FLAGS[lang]}</span>
                        )}
                      </span>
                    );
                  })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
