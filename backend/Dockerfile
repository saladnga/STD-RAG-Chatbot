FROM python:3.12-slim

# No .pyc files in the image; logs go straight out instead of sitting in a buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first: this layer is cached until requirements.txt changes.
# Every package ships a prebuilt wheel, so no compiler is needed.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Run as an unprivileged user; it only owns the folder that PDF uploads are written to.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/data/pdf && chown app:app /app/data/pdf
COPY app/ .
USER app

# Cloud Run sets PORT (usually 8080); 8000 for local `docker run`.
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
