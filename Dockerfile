FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

# The bridge must stay on loopback; use a host-network/tunnel strategy that preserves access to Zotero.
ENV BRIDGE_BIND_HOST=127.0.0.1
EXPOSE 8787
CMD ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8787"]
