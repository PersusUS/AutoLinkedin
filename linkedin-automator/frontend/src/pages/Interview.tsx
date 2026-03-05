import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useInterview } from '../hooks/useInterview';
import type { InterviewStatus } from '../types';

const STATUS_CONFIG: Record<InterviewStatus, { label: string; color: string; bg: string }> = {
  idle: { label: 'Listo para empezar', color: 'text-gray-500', bg: 'bg-gray-200' },
  connecting: { label: 'Conectando...', color: 'text-yellow-600', bg: 'bg-yellow-200' },
  active: { label: 'Entrevista en curso', color: 'text-green-600', bg: 'bg-green-200' },
  ending: { label: 'Finalizando...', color: 'text-blue-600', bg: 'bg-blue-200' },
  done: { label: 'Completada', color: 'text-gray-600', bg: 'bg-gray-200' },
};

export default function Interview() {
  const navigate = useNavigate();
  const { start, end, transcript, isSpeaking, status, transcriptId } = useInterview();
  const [showConfirm, setShowConfirm] = useState(false);

  const cfg = STATUS_CONFIG[status];
  const hasTurns = transcript.length > 0;

  // Navigate to review when session ends
  if (status === 'done' && transcriptId) {
    navigate(`/review/${transcriptId}`);
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Entrevista de Voz</h1>

      {/* Status indicator */}
      <div className="flex items-center gap-3 mb-6">
        <span className={`inline-block w-3 h-3 rounded-full ${cfg.bg}`} />
        <span className={`text-sm font-medium ${cfg.color}`}>{cfg.label}</span>
      </div>

      {/* AI speaking pulse */}
      {status === 'active' && (
        <div className="flex justify-center mb-6">
          <div
            className={`w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 ${
              isSpeaking
                ? 'bg-green-400 animate-pulse shadow-lg shadow-green-300'
                : 'bg-gray-200'
            }`}
          >
            <span className="text-3xl">{isSpeaking ? '🎙️' : '⏸️'}</span>
          </div>
        </div>
      )}

      {/* Transcript */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6 min-h-[300px] max-h-[500px] overflow-y-auto space-y-3">
        {transcript.length === 0 && (
          <p className="text-gray-400 text-sm text-center mt-8">
            {status === 'idle'
              ? 'Inicia la entrevista para comenzar'
              : 'Esperando transcripción...'}
          </p>
        )}
        {transcript.map((entry, i) => (
          <div
            key={i}
            className={`flex ${entry.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] px-4 py-2 rounded-2xl text-sm ${
                entry.role === 'user'
                  ? 'bg-blue-500 text-white rounded-br-sm'
                  : 'bg-gray-100 text-gray-800 rounded-bl-sm'
              }`}
            >
              {entry.text}
            </div>
          </div>
        ))}
      </div>

      {/* Action buttons */}
      <div className="flex gap-4">
        {(status === 'idle' || status === 'done') && (
          <button
            onClick={start}
            className="px-6 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition-colors"
          >
            Iniciar entrevista
          </button>
        )}

        {status === 'active' && (
          <button
            onClick={() => setShowConfirm(true)}
            disabled={!hasTurns}
            className="px-6 py-3 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Finalizar
          </button>
        )}
      </div>

      {/* Confirmation modal */}
      {showConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-sm mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">¿Finalizar entrevista?</h3>
            <p className="text-gray-600 text-sm mb-4">
              Se guardará el transcript y se generarán los posts.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowConfirm(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 text-sm font-medium"
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  setShowConfirm(false);
                  end();
                }}
                className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700"
              >
                Sí, finalizar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
