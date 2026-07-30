FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY apps /app/apps
COPY packages /app/packages
COPY services /app/services

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
