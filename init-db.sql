-- =============================================
-- Init script: Tạo các databases cần thiết
-- PostgreSQL chạy file này tự động khi khởi tạo
-- =============================================

-- auth_db đã được tạo bởi POSTGRES_DB env var
-- Tạo thêm user_service_db và notification_db

CREATE DATABASE user_service_db;
CREATE DATABASE notification_db;
