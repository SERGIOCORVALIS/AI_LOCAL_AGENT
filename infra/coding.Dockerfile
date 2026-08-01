FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OLLAMA_HOST=http://host.docker.internal:11434 \
    npm_config_update_notifier=false

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g \
        @openai/codex@0.146.0 \
        opencode-ai@1.18.10 \
        droid@0.186.0 \
    && useradd --create-home --uid 10002 --shell /usr/sbin/nologin coding \
    && rm -rf /var/lib/apt/lists/* /root/.npm

COPY pyproject.toml README.md LICENSE VERSION /app/
COPY apps /app/apps
COPY packages /app/packages
COPY services /app/services

RUN pip install --no-cache-dir -e . \
    && mkdir -p /app/runtime /workspace \
    && chown -R coding:coding /app /workspace

USER coding

EXPOSE 8091

CMD ["uvicorn", "apps.coding.main:app", "--host", "0.0.0.0", "--port", "8091"]
