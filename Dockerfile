FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install OS dependencies
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy backend files
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY database/ ./database/
COPY .env.example ./
COPY backend/requirements.txt ./requirements.txt

# Install Python deps
RUN pip install --upgrade pip && pip install -r requirements.txt

# Set envs
ENV PYTHONUNBUFFERED=1
ENV MODEL_NAME=tiiuae/falcon-rw-1b
ENV DATABASE_URL=postgresql://brainz:synthpass@db:5432/brainz_db
ENV DEBUG=true
 
# Start server
CMD ["bash", "scripts/run_server.sh"]