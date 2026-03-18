FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates/ templates/

# Hugging Face Spaces runs containers as a non-root user (uid 1000).
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

ENV PORT=7860

EXPOSE 7860

CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "2", "--threads", "2", "app:app"]
