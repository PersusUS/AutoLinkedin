import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Interview from './pages/Interview';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<Interview />} />
          <Route path="/review/:transcriptId" element={<div>Review (M4)</div>} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
