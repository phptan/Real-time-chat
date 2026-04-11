FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends curl ca-certificates postgresql-client tar gzip \
	&& curl -fsSL https://fastdl.mongodb.org/tools/db/mongodb-database-tools-debian12-x86_64-100.9.4.tgz -o /tmp/mongodb-tools.tgz \
	&& tar -xzf /tmp/mongodb-tools.tgz -C /tmp \
	&& cp /tmp/mongodb-database-tools-*/bin/mongodump /usr/local/bin/mongodump \
	&& chmod +x /usr/local/bin/mongodump \
	&& rm -rf /var/lib/apt/lists/* /tmp/mongodb-tools.tgz /tmp/mongodb-database-tools-*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
