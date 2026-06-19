FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt requirements-dev.txt ./
ARG INSTALL_DEV=false
RUN pip install --upgrade pip && \
    if [ "$INSTALL_DEV" = "true" ]; then \
        pip install -r requirements-dev.txt; \
    else \
        pip install -r requirements.txt; \
    fi

COPY . .
RUN chmod +x scripts/start.sh

EXPOSE 8000
CMD ["./scripts/start.sh"]
