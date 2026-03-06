import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { getStatus } from '../../api/linkedin';

export default function Sidebar() {
  const [linkedinName, setLinkedinName] = useState<string | null>(null);

  useEffect(() => {
    getStatus().then((s) => {
      if (s.connected) setLinkedinName(s.name);
    });
  }, []);

  const link =
    'block px-4 py-2 rounded-lg text-sm font-medium transition-colors';
  const active = 'bg-blue-100 text-blue-700';
  const inactive = 'text-gray-600 hover:bg-gray-100';

  return (
    <aside className="w-56 shrink-0 border-r border-gray-200 bg-white flex flex-col h-screen sticky top-0">
      <div className="px-4 py-5 border-b border-gray-200">
        <h1 className="text-lg font-bold text-gray-900">LinkedIn Automator</h1>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        <NavLink to="/" end className={({ isActive }) => `${link} ${isActive ? active : inactive}`}>
          🎙️ Entrevista
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => `${link} ${isActive ? active : inactive}`}>
          📋 Historial
        </NavLink>
      </nav>

      <div className="px-4 py-4 border-t border-gray-200">
        {linkedinName ? (
          <span className="text-xs text-green-700 font-medium">LinkedIn ✓ {linkedinName}</span>
        ) : (
          <a
            href="http://localhost:8000/api/linkedin/auth"
            className="text-xs text-blue-600 hover:underline font-medium"
          >
            Conectar LinkedIn
          </a>
        )}
      </div>
    </aside>
  );
}
