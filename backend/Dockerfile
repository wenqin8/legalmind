FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app/backend
COPY backend/requirements.txt ./requirements.txt
COPY backend/constraints.txt ./constraints.txt
# The configured embedding device is CPU; do not pull unused CUDA packages.
RUN pip install --no-cache-dir "pip>=26.2.0" "setuptools>=83.0.0"
RUN pip install --no-cache-dir torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY backend/scripts ./scripts
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./alembic.ini
COPY backend/data/demo ./data/demo
COPY backend/data/legal ./data/legal
RUN useradd --create-home --uid 10001 appuser && mkdir -p /var/lib/legalmind/chroma /var/lib/legalmind/models && chown -R appuser:appuser /var/lib/legalmind /app/backend
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers"]
