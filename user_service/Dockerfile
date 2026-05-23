FROM python:3.11-slim

WORKDIR /app

# Copy danh sách thư viện và cài đặt trước để tận dụng cache của Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ source code backend vào container
COPY . .

# Khởi chạy User Service ở port 3003 theo đúng đặc tả kiến trúc của nhóm
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3003"]