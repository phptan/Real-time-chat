import { useState } from 'react';
import axios from 'axios';
import API from '../config/api.js';
import './LoginPage.css';

/**
 * LoginPage — Trang đăng nhập / đăng ký
 * Giao diện glassmorphism premium với dual-panel form.
 */
function LoginPage({ onLogin, showToast }) {
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
  });

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isRegister) {
        // === ĐĂNG KÝ ===
        if (!form.username || !form.email || !form.password) {
          showToast('Vui lòng điền đầy đủ thông tin.', 'error');
          setLoading(false);
          return;
        }
        const res = await axios.post(API.AUTH.REGISTER, {
          username: form.username,
          email: form.email,
          password: form.password,
        });
        if (res.data.success) {
          onLogin(res.data.data);
        } else {
          showToast(res.data.message, 'error');
        }
      } else {
        // === ĐĂNG NHẬP ===
        if (!form.username || !form.password) {
          showToast('Vui lòng nhập tên đăng nhập và mật khẩu.', 'error');
          setLoading(false);
          return;
        }
        const res = await axios.post(API.AUTH.LOGIN, {
          username: form.username,
          password: form.password,
        });
        if (res.data.success) {
          onLogin(res.data.data);
        } else {
          showToast(res.data.message, 'error');
        }
      }
    } catch (err) {
      const msg = err.response?.data?.message || 'Lỗi kết nối server.';
      showToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      {/* Background decorations */}
      <div className="login-bg-orb login-bg-orb-1" />
      <div className="login-bg-orb login-bg-orb-2" />
      <div className="login-bg-orb login-bg-orb-3" />

      <div className="login-container animate-fade-in">
        {/* Left panel — Branding */}
        <div className="login-branding">
          <div className="login-logo">
            <span className="login-logo-icon">💬</span>
          </div>
          <h1 className="login-title">Real-time Chat</h1>
          <p className="login-subtitle">
            Hệ thống nhắn tin thời gian thực
            <br />
            được xây dựng trên kiến trúc Microservices
          </p>
          <div className="login-features">
            <div className="login-feature">
              <span className="login-feature-icon">🟢</span>
              <span>Trạng thái Online/Offline</span>
            </div>
            <div className="login-feature">
              <span className="login-feature-icon">⚡</span>
              <span>Tin nhắn thời gian thực</span>
            </div>
            <div className="login-feature">
              <span className="login-feature-icon">🔒</span>
              <span>Xác thực JWT bảo mật</span>
            </div>
          </div>
        </div>

        {/* Right panel — Form */}
        <div className="login-form-panel">
          <h2 className="login-form-title">
            {isRegister ? 'Tạo tài khoản' : 'Đăng nhập'}
          </h2>
          <p className="login-form-desc">
            {isRegister
              ? 'Điền thông tin để bắt đầu trò chuyện'
              : 'Chào mừng trở lại!'}
          </p>

          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label className="form-label">Tên đăng nhập</label>
              <input
                type="text"
                name="username"
                className="input"
                placeholder="Nhập username..."
                value={form.username}
                onChange={handleChange}
                autoComplete="username"
              />
            </div>

            {isRegister && (
              <div className="form-group animate-fade-in">
                <label className="form-label">Email</label>
                <input
                  type="email"
                  name="email"
                  className="input"
                  placeholder="your@email.com"
                  value={form.email}
                  onChange={handleChange}
                  autoComplete="email"
                />
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Mật khẩu</label>
              <input
                type="password"
                name="password"
                className="input"
                placeholder="••••••••"
                value={form.password}
                onChange={handleChange}
                autoComplete={isRegister ? 'new-password' : 'current-password'}
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary login-submit-btn"
              disabled={loading}
            >
              {loading ? (
                <span className="btn-loading">⏳ Đang xử lý...</span>
              ) : isRegister ? (
                '🚀 Đăng ký'
              ) : (
                '🔑 Đăng nhập'
              )}
            </button>
          </form>

          <div className="login-switch">
            <span className="login-switch-text">
              {isRegister ? 'Đã có tài khoản?' : 'Chưa có tài khoản?'}
            </span>
            <button
              type="button"
              className="login-switch-btn"
              onClick={() => {
                setIsRegister(!isRegister);
                setForm({ username: '', email: '', password: '' });
              }}
            >
              {isRegister ? 'Đăng nhập' : 'Đăng ký ngay'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
