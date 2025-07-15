<p align="center">
  <img src="./img/logo.png">
</p>

<p align="center">
  <a href="https://brainz.monster/">🌐 Website</a> •
  <a href="https://x.com/brainzmonster">X (Twitter)</a> •
  <a href="https://brainz.gitbook.io/os">📚 Docs</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Built_with-FastAPI-green?style=flat-square">
  <img src="https://img.shields.io/badge/Frontend-React-blue?style=flat-square">
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square">
</p>

# brainz OS

brainz is a modular LLM Operating System focused on autonomous learning in the crypto and technology space. It includes training pipelines, inference API, a full web frontend, CLI tools, a database layer, analytics, and agent support.

## Table of Contents

- Features
- Tech Stack
- Directory Structure
- Installation
- Usage
- Quickstart
- Docker Setup
- API
- Environment Configuration
- Testing
- License

## Features

- Continual learning with user feedback and auto-training  
- Prompt optimization and semantic similarity  
- Full backend with FastAPI, PostgreSQL and SQLAlchemy  
- Web frontend with React, Tailwind and Vite  
- Live logs, metrics and vectorization  
- Integrated CLI tooling  
- Agent architecture for feedback, optimization and auto training  

## Tech Stack

Backend: FastAPI, SQLAlchemy, PostgreSQL, Transformers, SentenceTransformers  
Frontend: React, Vite, Tailwind CSS  
Infrastructure: Uvicorn, Gunicorn, dotenv, Bash scripts

## Directory Structure

```
brainz/
├── backend/
│   ├── api/            # FastAPI routes and middleware
│   ├── core/           # Config, engine, lifecycle, registry
│   ├── models/         # LLM loading, training, inference, adapter
│   ├── data/           # Dataset, tokenizer, parser, vectorizer
│   ├── agents/         # AutoTrainer, Optimizer, Feedback loop
│   ├── services/       # Training, user, memory, analytics
│   ├── db/             # Schema, models, queries, connection
│   ├── utils/          # Benchmarks, crypto, eval metrics
│   ├── tests/          # All test cases
│   ├── gunicorn.conf.py
│   └── requirements.txt
│
├── web/
│   ├── public/         # index.html
│   ├── src/            # API clients, components, hooks, pages
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── package.json
│
├── database/
│   ├── migrations/     # SQL migration files
│   ├── seed/           # Seed data for users, prompts
│   └── db_init.py
│
├── scripts/            # Shell + Python utility scripts
├── .env.example
├── README.md
├── LICENSE
├── setup.py
└── requirements.txt
```

## Installation

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../web
npm install
```

## Usage

Start the backend server:

```bash
bash scripts/run_server.sh
```

Start the frontend:

```bash
cd web
npm run dev
```

Initialize database:

```bash
python database/db_init.py
```

## Quickstart

```bash
git clone https://github.com/brainzmonster/os.git
cd os
cp .env.example .env
docker-compose up --build
```

Then open: http://localhost

## Docker Setup

You can run the full brainz stack using Docker and Docker Compose.

1. Make sure Docker and Docker Compose are installed on your system.
2. Clone the repository and nav
igate to the root directory.
3. Copy the environment file:
```bash
cp .env.example .env
```

4. Build and start all services:

```bash
docker-compose up --build
```

5. Open your browser and navigate to:

```bash
http://localhost
```

The backend will be available on port 8000, the frontend on port 3000, and the proxy on port 80.

If you want to stop all containers:

```bash
docker-compose down
```


## API

| Method | Endpoint         | Description                |
|--------|------------------|----------------------------|
| POST   | /api/llm/query   | Query the model            |
| POST   | /api/llm/train   | Train with user input      |
| POST   | /api/user/create | Register new user          |
| GET    | /api/system/logs | Stream live logs           |

## Environment Configuration

Create `.env` from `.env.example` and update:

```
MODEL_NAME=tiiuae/falcon-rw-1b
DATABASE_URL=postgresql://user:pass@localhost:5432/brainz
DEBUG=true
```

## Testing

```bash
pytest backend/tests
```

## License

MIT License