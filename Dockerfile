FROM python:3.13-slim

WORKDIR /app

# Install deps first (cached layer) — no secrets needed here
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code — still no secrets
COPY . .

# No ARG/ENV for BOT_TOKEN, LLM_API_KEY, SUPABASE_KEY etc here.
# Railway injects them as real runtime environment variables into the
# container process at "docker run" time, not into the image itself.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
