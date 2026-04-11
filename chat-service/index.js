require("dotenv").config();
const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const mongoose = require("mongoose");
const cors = require("cors");
const path = require("path");
const jwt = require("jsonwebtoken");
const Redis = require("redis");

const app = express();
app.use(cors());
app.use(express.json({ limit: "10mb" }));
app.use(express.urlencoded({ limit: "10mb", extended: true }));

const server = http.createServer(app);
const io = new Server(server, { cors: { origin: "*" } });

// === CẤU HÌNH ===
const JWT_SECRET = process.env.JWT_SECRET || "SECRET_YOUR_TEAM_CHOSE";
const MONGODB_URI = process.env.MONGODB_URI || "mongodb://mongodb:27017/chatdb";
const REDIS_URL = process.env.REDIS_URL || "redis://redis:6379";
const PORT = process.env.PORT || 3002;

// === KẾT NỐI DATABASE ===
mongoose
  .connect(MONGODB_URI)
  .then(() => console.log("🍃 MongoDB Connected"))
  .catch((err) => console.error("❌ MongoDB Error:", err));

// === KẾT NỐI REDIS ===
let redisClient = null;
let redisPub = null;

async function connectRedis() {
  try {
    redisClient = Redis.createClient({ url: REDIS_URL });
    redisPub = redisClient.duplicate();

    redisClient.on("error", (err) => console.error("❌ Redis Error:", err));
    redisPub.on("error", (err) => console.error("❌ Redis Pub Error:", err));

    await redisClient.connect();
    await redisPub.connect();
    console.log("✅ Redis Connected");
  } catch (err) {
    console.error("❌ Redis Connection Failed:", err.message);
    setTimeout(connectRedis, 5000);
  }
}
connectRedis();

// === MONGODB MODELS ===
const Message = mongoose.model(
  "Message",
  new mongoose.Schema(
    {
      senderId: { type: String, required: true },
      senderName: { type: String, default: "Unknown" },
      roomId: { type: String, required: true },
      text: String,
      type: { type: String, default: "text" },
      deletedAt: { type: Date, default: null },
    },
    { timestamps: true }
  )
);

const Room = mongoose.model(
  "Room",
  new mongoose.Schema(
    {
      name: String,
      type: { type: String, enum: ["direct", "group"], default: "direct" },
      members: [String],
      lastMessage: {
        type: mongoose.Schema.Types.ObjectId,
        ref: "Message",
        default: null,
      },
    },
    { timestamps: true }
  )
);

// === HELPER: Verify JWT ===
function verifyToken(token) {
  try {
    return jwt.verify(token, JWT_SECRET);
  } catch {
    return null;
  }
}

// === REST API ROUTES ===

// Health check
app.get("/health", (req, res) => {
  res.json({ status: "ok", service: "chat-service" });
});

// Tạo hoặc lấy phòng chat direct giữa 2 users
app.post("/api/chat/rooms", async (req, res) => {
  try {
    const { type, name, memberIds, senderId } = req.body;

    if (type === "direct") {
      const sorted = [senderId, memberIds[0]].sort();
      // Tìm phòng direct đã tồn tại
      const exists = await Room.findOne({
        type: "direct",
        members: { $all: sorted, $size: 2 },
      });
      if (exists) {
        return res.json({ success: true, data: exists });
      }
      // Tạo phòng mới
      const room = await Room.create({
        type: "direct",
        members: sorted,
      });
      return res.status(201).json({ success: true, data: room });
    }

    // Group chat
    if (!name || name.trim() === "") {
      return res.status(400).json({
        success: false,
        error: "VALIDATION_ERROR",
        message: "Thiếu tên nhóm",
      });
    }
    const room = await Room.create({
      type: "group",
      name,
      members: [senderId, ...memberIds],
    });
    res.status(201).json({ success: true, data: room });
  } catch (err) {
    res.status(500).json({ success: false, error: "SERVER_ERROR", message: err.message });
  }
});

// Lấy danh sách phòng chat của 1 user
app.get("/api/chat/rooms/user/:userId", async (req, res) => {
  try {
    const rooms = await Room.find({ members: req.params.userId })
      .populate("lastMessage")
      .sort({ updatedAt: -1 });
    res.json({ success: true, data: rooms });
  } catch (err) {
    res.status(500).json({ success: false, error: "SERVER_ERROR", message: err.message });
  }
});

// Lấy lịch sử tin nhắn của 1 phòng (có pagination)
app.get("/api/chat/rooms/:roomId/messages", async (req, res) => {
  try {
    const { roomId } = req.params;
    const limit = parseInt(req.query.limit) || 50;
    const before = req.query.before; // cursor-based pagination

    let query = { roomId, deletedAt: null };
    if (before) {
      query.createdAt = { $lt: new Date(before) };
    }

    const messages = await Message.find(query)
      .sort({ createdAt: -1 })
      .limit(limit);

    // Trả về theo thứ tự thời gian (cũ → mới)
    res.json({ success: true, data: messages.reverse() });
  } catch (err) {
    res.status(500).json({ success: false, error: "SERVER_ERROR", message: err.message });
  }
});

// Gửi tin nhắn qua REST (alternative cho socket)
app.post("/api/chat/messages", async (req, res) => {
  try {
    const { senderId, senderName, roomId, text } = req.body;
    if (!text || !text.trim()) {
      return res.status(400).json({
        success: false,
        error: "CONTENT_EMPTY",
        message: "Tin nhắn không được để trống",
      });
    }

    const msg = await Message.create({ senderId, senderName, roomId, text });

    // Cập nhật lastMessage của room
    await Room.findByIdAndUpdate(roomId, { lastMessage: msg._id });

    // Broadcast qua Socket.io
    io.to(roomId).emit("new_message", msg);

    // Publish lên Redis (notification-service sẽ subscribe)
    if (redisPub) {
      const room = await Room.findById(roomId);
      const recipientIds = room
        ? room.members.filter((m) => m !== senderId)
        : [];
      await redisPub.publish(
        "new_message",
        JSON.stringify({
          sender_id: senderId,
          recipient_ids: recipientIds,
          room_id: roomId,
          title: `Tin nhắn mới từ ${senderName}`,
          body: text.substring(0, 100),
          message: text,
        })
      );
    }

    res.status(201).json({ success: true, data: msg });
  } catch (err) {
    res.status(500).json({ success: false, error: "SERVER_ERROR", message: err.message });
  }
});

// === SOCKET.IO — REAL-TIME MESSAGING ===
io.on("connection", (socket) => {
  console.log(`🔌 Socket connected: ${socket.id}`);

  // Xác thực JWT khi kết nối (optional, fallback cho anonymous)
  const token = socket.handshake.auth?.token;
  let userData = null;
  if (token) {
    userData = verifyToken(token);
  }

  // Tham gia phòng chat
  socket.on("join_room", (roomId) => {
    socket.join(roomId);
    console.log(`📌 Socket ${socket.id} joined room ${roomId}`);
  });

  // Rời phòng chat
  socket.on("leave_room", (roomId) => {
    socket.leave(roomId);
  });

  // Gửi tin nhắn realtime
  socket.on("send_message", async (data) => {
    try {
      const hasText = data.text && data.text.trim().length > 0;
      if (!hasText) {
        return socket.emit("error_msg", "[CONTENT_EMPTY] - Tin nhắn không được để trống");
      }

      const msg = await Message.create({
        senderId: data.senderId,
        senderName: data.senderName || "Unknown",
        roomId: data.roomId,
        text: data.text,
      });

      // Cập nhật lastMessage
      await Room.findByIdAndUpdate(data.roomId, { lastMessage: msg._id });

      // Broadcast tới tất cả trong phòng
      io.to(data.roomId).emit("new_message", msg);

      // Publish lên Redis
      if (redisPub) {
        const room = await Room.findById(data.roomId);
        const recipientIds = room
          ? room.members.filter((m) => m !== data.senderId)
          : [];
        await redisPub.publish(
          "new_message",
          JSON.stringify({
            sender_id: data.senderId,
            recipient_ids: recipientIds,
            room_id: data.roomId,
            title: `Tin nhắn mới từ ${data.senderName || "Someone"}`,
            body: data.text.substring(0, 100),
          })
        );
      }
    } catch (err) {
      socket.emit("error_msg", `[SERVER_ERROR] - ${err.message}`);
    }
  });

  // Xóa tin nhắn (soft delete)
  socket.on("delete_message", async ({ messageId, userId }) => {
    const msg = await Message.findById(messageId);
    if (msg && msg.senderId === userId) {
      msg.deletedAt = new Date();
      await msg.save();
      io.to(msg.roomId).emit("message_deleted", messageId);
    } else {
      socket.emit("error_msg", "[FORBIDDEN] - Bạn không có quyền xóa tin nhắn này");
    }
  });

  // Typing indicator
  socket.on("typing", (data) => {
    socket.to(data.roomId).emit("user_typing", {
      userId: data.userId,
      username: data.username,
    });
  });

  socket.on("stop_typing", (data) => {
    socket.to(data.roomId).emit("user_stop_typing", {
      userId: data.userId,
    });
  });

  socket.on("disconnect", () => {
    console.log(`🔌 Socket disconnected: ${socket.id}`);
  });
});

// === START SERVER ===
server.listen(PORT, () => {
  console.log(`🚀 Chat Service v8.0 Online on port ${PORT}`);
});
