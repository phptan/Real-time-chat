import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { io } from 'socket.io-client';
import API from '../config/api.js';
import './ChatPage.css';

/**
 * ChatPage — Trang chat chính
 * Layout: Sidebar (users list) + Chat Area (messages)
 * Realtime: Socket.io-client cho tin nhắn tức thì
 */
function ChatPage({ auth, onLogout, showToast }) {
  // === STATE ===
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [currentRoom, setCurrentRoom] = useState(null);
  const [messages, setMessages] = useState([]);
  const [messageInput, setMessageInput] = useState('');
  const [socket, setSocket] = useState(null);
  const [typingUsers, setTypingUsers] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loadingMessages, setLoadingMessages] = useState(false);

  const messagesEndRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  // === SOCKET.IO CONNECTION ===
  useEffect(() => {
    const newSocket = io(API.SOCKET_URL, {
      auth: { token: auth.access_token },
      transports: ['websocket', 'polling'],
    });

    newSocket.on('connect', () => {
      console.log('🔌 Socket connected:', newSocket.id);
    });

    newSocket.on('new_message', (msg) => {
      setMessages((prev) => {
        // Tránh duplicate
        if (prev.find((m) => m._id === msg._id)) return prev;
        return [...prev, msg];
      });
    });

    newSocket.on('message_deleted', (messageId) => {
      setMessages((prev) => prev.filter((m) => m._id !== messageId));
    });

    newSocket.on('user_typing', (data) => {
      setTypingUsers((prev) => {
        if (prev.find((u) => u.userId === data.userId)) return prev;
        return [...prev, data];
      });
    });

    newSocket.on('user_stop_typing', (data) => {
      setTypingUsers((prev) => prev.filter((u) => u.userId !== data.userId));
    });

    newSocket.on('error_msg', (errMsg) => {
      showToast(errMsg, 'error');
    });

    setSocket(newSocket);

    return () => {
      newSocket.disconnect();
    };
  }, [auth.access_token, showToast]);

  // === LOAD USERS LIST ===
  const loadUsers = useCallback(async () => {
    try {
      const res = await axios.get(API.AUTH.USERS);
      if (res.data.success) {
        // Lọc bỏ user hiện tại
        const otherUsers = res.data.data.users.filter(
          (u) => u.id !== auth.user_id
        );
        setUsers(otherUsers);
      }
    } catch (err) {
      console.error('Failed to load users:', err);
    }
  }, [auth.user_id]);

  useEffect(() => {
    loadUsers();
    // Refresh users list every 10s (for online status)
    const interval = setInterval(loadUsers, 10000);
    return () => clearInterval(interval);
  }, [loadUsers]);

  // === SELECT USER & LOAD/CREATE ROOM ===
  const handleSelectUser = useCallback(
    async (user) => {
      setSelectedUser(user);
      setMessages([]);
      setLoadingMessages(true);

      try {
        // Tạo hoặc lấy room direct
        const roomRes = await axios.post(API.CHAT.ROOMS, {
          type: 'direct',
          memberIds: [user.id],
          senderId: auth.user_id,
        });

        if (roomRes.data.success) {
          const room = roomRes.data.data;
          setCurrentRoom(room);

          // Join socket room
          if (socket) {
            socket.emit('join_room', room._id);
          }

          // Load message history
          const msgRes = await axios.get(API.CHAT.MESSAGES(room._id));
          if (msgRes.data.success) {
            setMessages(msgRes.data.data);
          }
        }
      } catch (err) {
        showToast('Không thể tải phòng chat.', 'error');
        console.error(err);
      } finally {
        setLoadingMessages(false);
      }
    },
    [auth.user_id, socket, showToast]
  );

  // === SEND MESSAGE ===
  const handleSendMessage = useCallback(
    async (e) => {
      e.preventDefault();
      if (!messageInput.trim() || !currentRoom) return;

      const msgData = {
        senderId: auth.user_id,
        senderName: auth.username,
        roomId: currentRoom._id,
        text: messageInput.trim(),
      };

      // Gửi qua Socket.io (realtime)
      if (socket) {
        socket.emit('send_message', msgData);
        socket.emit('stop_typing', {
          roomId: currentRoom._id,
          userId: auth.user_id,
        });
      }

      setMessageInput('');
    },
    [messageInput, currentRoom, auth, socket]
  );

  // === TYPING INDICATOR ===
  const handleTyping = useCallback(() => {
    if (!socket || !currentRoom) return;

    socket.emit('typing', {
      roomId: currentRoom._id,
      userId: auth.user_id,
      username: auth.username,
    });

    // Clear previous timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Stop typing after 2 seconds
    typingTimeoutRef.current = setTimeout(() => {
      socket.emit('stop_typing', {
        roomId: currentRoom._id,
        userId: auth.user_id,
      });
    }, 2000);
  }, [socket, currentRoom, auth]);

  // === AUTO SCROLL ===
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // === FILTER USERS ===
  const filteredUsers = users.filter((u) =>
    u.username.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // === FORMAT TIME ===
  const formatTime = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('vi-VN', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    const today = new Date();
    if (date.toDateString() === today.toDateString()) return 'Hôm nay';
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date.toDateString() === yesterday.toDateString()) return 'Hôm qua';
    return date.toLocaleDateString('vi-VN');
  };

  // Group messages by date
  const groupedMessages = messages.reduce((groups, msg) => {
    const date = formatDate(msg.createdAt);
    if (!groups[date]) groups[date] = [];
    groups[date].push(msg);
    return groups;
  }, {});

  // === HANDLE LOGOUT ===
  const handleLogout = async () => {
    try {
      await axios.post(API.AUTH.LOGOUT, { token: auth.access_token });
    } catch {
      // Logout anyway
    }
    if (socket) socket.disconnect();
    onLogout();
  };

  // === RENDER ===
  return (
    <div className="chat-page">
      {/* ====== SIDEBAR ====== */}
      <aside className="chat-sidebar">
        <div className="sidebar-header">
          <div className="sidebar-user-info">
            <div className="sidebar-avatar">
              {auth.username.charAt(0).toUpperCase()}
            </div>
            <div className="sidebar-user-meta">
              <span className="sidebar-username">{auth.username}</span>
              <span className="sidebar-status">
                <span className="status-dot online" /> Online
              </span>
            </div>
          </div>
          <button className="btn-icon" onClick={handleLogout} title="Đăng xuất">
            🚪
          </button>
        </div>

        {/* Search */}
        <div className="sidebar-search">
          <input
            type="text"
            className="input sidebar-search-input"
            placeholder="🔍 Tìm kiếm người dùng..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {/* Users list */}
        <div className="sidebar-users">
          <div className="sidebar-section-title">
            Người dùng ({filteredUsers.length})
          </div>
          {filteredUsers.length === 0 ? (
            <div className="sidebar-empty">
              Không tìm thấy người dùng nào
            </div>
          ) : (
            filteredUsers.map((user) => (
              <div
                key={user.id}
                className={`sidebar-user-item ${
                  selectedUser?.id === user.id ? 'active' : ''
                }`}
                onClick={() => handleSelectUser(user)}
              >
                <div className="user-item-avatar">
                  {user.username.charAt(0).toUpperCase()}
                  <span
                    className={`user-item-status ${
                      user.is_online ? 'online' : 'offline'
                    }`}
                  />
                </div>
                <div className="user-item-info">
                  <span className="user-item-name">{user.username}</span>
                  <span className="user-item-state">
                    {user.is_online ? 'Đang hoạt động' : 'Offline'}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* ====== CHAT AREA ====== */}
      <main className="chat-main">
        {selectedUser ? (
          <>
            {/* Chat Header */}
            <div className="chat-header">
              <div className="chat-header-user">
                <div className="chat-header-avatar">
                  {selectedUser.username.charAt(0).toUpperCase()}
                  <span
                    className={`chat-header-status ${
                      selectedUser.is_online ? 'online' : 'offline'
                    }`}
                  />
                </div>
                <div className="chat-header-meta">
                  <span className="chat-header-name">
                    {selectedUser.username}
                  </span>
                  <span className="chat-header-state">
                    {selectedUser.is_online ? '🟢 Đang hoạt động' : '⚫ Offline'}
                  </span>
                </div>
              </div>
            </div>

            {/* Messages Area */}
            <div className="chat-messages">
              {loadingMessages ? (
                <div className="chat-loading">
                  <div className="loading-dots">
                    <span /><span /><span />
                  </div>
                  <p>Đang tải tin nhắn...</p>
                </div>
              ) : messages.length === 0 ? (
                <div className="chat-empty">
                  <div className="chat-empty-icon">👋</div>
                  <h3>Bắt đầu trò chuyện!</h3>
                  <p>
                    Gửi tin nhắn đầu tiên cho{' '}
                    <strong>{selectedUser.username}</strong>
                  </p>
                </div>
              ) : (
                Object.entries(groupedMessages).map(([date, msgs]) => (
                  <div key={date} className="message-date-group">
                    <div className="message-date-divider">
                      <span>{date}</span>
                    </div>
                    {msgs.map((msg, idx) => {
                      const isMe = msg.senderId === auth.user_id;
                      return (
                        <div
                          key={msg._id || idx}
                          className={`message-row ${isMe ? 'me' : 'other'} animate-fade-in`}
                        >
                          {!isMe && (
                            <div className="message-avatar">
                              {(msg.senderName || '?').charAt(0).toUpperCase()}
                            </div>
                          )}
                          <div className={`message-bubble ${isMe ? 'me' : 'other'}`}>
                            {!isMe && (
                              <span className="message-sender">
                                {msg.senderName || 'Unknown'}
                              </span>
                            )}
                            <p className="message-text">{msg.text}</p>
                            <span className="message-time">
                              {formatTime(msg.createdAt)}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))
              )}

              {/* Typing indicator */}
              {typingUsers.length > 0 && (
                <div className="typing-indicator animate-fade-in">
                  <div className="typing-dots">
                    <span /><span /><span />
                  </div>
                  <span className="typing-text">
                    {typingUsers.map((u) => u.username).join(', ')} đang nhập...
                  </span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Message Input */}
            <form className="chat-input-area" onSubmit={handleSendMessage}>
              <input
                type="text"
                className="input chat-input"
                placeholder="Nhập tin nhắn..."
                value={messageInput}
                onChange={(e) => {
                  setMessageInput(e.target.value);
                  handleTyping();
                }}
                autoFocus
              />
              <button
                type="submit"
                className="btn btn-primary chat-send-btn"
                disabled={!messageInput.trim()}
              >
                <span className="send-icon">➤</span>
              </button>
            </form>
          </>
        ) : (
          /* Empty state — No user selected */
          <div className="chat-welcome">
            <div className="chat-welcome-icon">💬</div>
            <h2>Real-time Chat</h2>
            <p>Chọn một người dùng từ danh sách bên trái để bắt đầu trò chuyện</p>
            <div className="chat-welcome-features">
              <div className="welcome-feature">
                <span>🟢</span> Xem ai đang online
              </div>
              <div className="welcome-feature">
                <span>⚡</span> Tin nhắn tức thì
              </div>
              <div className="welcome-feature">
                <span>📜</span> Lịch sử trò chuyện
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default ChatPage;
