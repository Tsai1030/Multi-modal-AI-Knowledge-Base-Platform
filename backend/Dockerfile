FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libreoffice \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Override CPU torch with CUDA 12.1 build for GPU embedding support
RUN uv pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cu121

COPY . .

RUN mkdir -p /app/data /app/uploads /app/rag_storage

EXPOSE 8000

CMD ["sh", "/app/scripts/start_backend.sh"]
