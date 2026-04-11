import { useState, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage.jsx';
import ChatPage from './pages/ChatPage.jsx';

/**
 * App — Root Component
 * Quản lý authentication state & routing.
 */
function App() {
  const [auth, setAuth] = useState(() => {
    // Khôi phục session từ localStorage
    const saved = localStorage.getItem('chat_auth');
    return saved ? JSON.parse(saved) : null;
  });

  const [toast, setToast] = useState(null);

  const showToast = useCallback((message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  const handleLogin = useCallback((authData) => {
    setAuth(authData);
    localStorage.setItem('chat_auth', JSON.stringify(authData));
    showToast('Đăng nhập thành công!');
  }, [showToast]);

  const handleLogout = useCallback(() => {
    setAuth(null);
    localStorage.removeItem('chat_auth');
    showToast('Đã đăng xuất.', 'success');
  }, [showToast]);

  return (
    <BrowserRouter>
      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.message}
        </div>
      )}
      <Routes>
        <Route
          path="/"
          element={
            auth
              ? <Navigate to="/chat" replace />
              : <LoginPage onLogin={handleLogin} showToast={showToast} />
          }
        />
        <Route
          path="/chat"
          element={
            auth
              ? <ChatPage auth={auth} onLogout={handleLogout} showToast={showToast} />
              : <Navigate to="/" replace />
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
