/**
 * API Configuration
 * 
 * REST API: Gọi qua Vite proxy (cùng origin, prefix /api/...)
 * Socket.io: Browser kết nối trực tiếp tới chat-service qua port mapping
 */

export const API = {
  AUTH: {
    REGISTER: '/api/auth/register',
    LOGIN: '/api/auth/login',
    VERIFY: '/api/auth/verify-token',
    LOGOUT: '/api/auth/logout',
    USERS: '/api/auth/users/all',
  },
  CHAT: {
    ROOMS: '/api/chat/rooms',
    ROOMS_USER: (userId) => `/api/chat/rooms/user/${userId}`,
    MESSAGES: (roomId) => `/api/chat/rooms/${roomId}/messages`,
    SEND: '/api/chat/messages',
  },
  USER: {
    ME: '/api/users/me',
    PROFILE: (id) => `/api/users/${id}`,
    STATUS: '/api/users/status',
  },
  // Socket.io: browser kết nối trực tiếp tới host machine port 3002
  // Vì WebSocket không đi qua Vite proxy được ổn định
  SOCKET_URL: `${window.location.protocol}//${window.location.hostname}:3002`,
};

export default API;
