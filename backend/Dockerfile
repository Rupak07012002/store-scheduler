FROM python:3.12-slim

# OR-Tools and psycopg2 both need build tools + libpq at image-build time;
# keeping this in the base image (not a separate builder stage) trades a
# larger image for a simpler v1 Dockerfile — revisit as a multi-stage build
# once image size/startup time actually matters (see docs/scaling-guide.md).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
