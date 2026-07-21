FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY ai-engine /packages/ai-engine
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir /packages/ai-engine

COPY ml-engine /app
RUN pip install --no-cache-dir --no-deps .

EXPOSE 8001

CMD ["uvicorn", "src.serving.main:app", "--host", "0.0.0.0", "--port", "8001"]
