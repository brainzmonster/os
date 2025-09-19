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

no corporate bs. no vendor lock.  
**brainz is the llm os for builders who want to own their stack.**  
live fine-tuning, vector memory, self-training agents – all local, all modular, all yours.

---

## why brainz?

other llms: closed apis, no memory, no self-learning.  
brainz:  
- **learns while it runs** (auto-training from real prompts)  
- **remembers what matters** (semantic vector memory)  
- **fixes itself** (agents rewrite, retrain, optimize)  
- **ships with full stack** – fastapi, react, cli, docker.  
- **privacy-first** – no telemetry, no cloud calls, zero keys.

this isn’t "an ai chatbot". this is infrastructure. degen style.

---

## features

- real-time training from user input or logs  
- memory engine with semantic vector search (postgres + sentence-transformers)  
- self-optimizing agents (autotrainer, feedback loop, prompt optimizer)  
- full api + cli + web ui  
- live logs, analytics, memory traces  
- 100% self-hosted, docker-native

---

## tech stack

**backend**: fastapi, sqlalchemy, postgresql, transformers, sentence-transformers  
**frontend**: react, vite, tailwind css  
**infra**: uvicorn, gunicorn, docker, dotenv, bash scripts

---

## directory

```
brainz/
├── backend/
│   ├── api/            # rest routes + middleware
│   ├── core/           # config, engine, registry
│   ├── models/         # inference, trainer, adapter
│   ├── data/           # tokenizer, dataset, vectorizer
│   ├── agents/         # autotrainer, feedback, optimizers
│   ├── services/       # memory, analytics, user logic
│   ├── db/             # schema + queries
│   ├── utils/          # metrics, evals, crypto
│   ├── tests/          # pytest suite
│   ├── gunicorn.conf.py
│   └── requirements.txt
│
├── web/
│   ├── public/         # index.html
│   ├── src/            # api clients, components, hooks, pages
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── package.json
│
├── database/
│   ├── migrations/     # sql migration files
│   ├── seed/           # seed data for users, prompts
│   └── db_init.py
│
├── scripts/            # shell + Python utility scripts
├── .env.example
├── README.md
├── LICENSE
├── setup.py
└── requirements.txt
```

## installation

```bash
# backend
cd backend
pip install -r requirements.txt

# frontend
cd ../web
npm install
```

optional (editable install for entry points):

```bash
# from repo root
pip install -e .

# now you can use:
brainz-server   # starts the api
brainz-train    # cli train entry point
```

## usage

start the backend server:

```bash
bash scripts/run_server.sh
```

server flags (new):

- prod – production mode (disables auto-reload)
- no-reload – disable hot-reload in dev
- log=logs/api.out – tee uvicorn output to file
- host=0.0.0.0 – bind host (default: 0.0.0.0)
- port=8000 – base port (default: 8000)
- auto-port – auto-pick free port if base is busy

start the frontend:

```bash
cd web
npm run dev
```

initialize database:

```bash
python database/db_init.py
```

## quickstart

```bash
git clone https://github.com/brainzmonster/os.git
cd os
cp .env.example .env
docker-compose up --build
```

then open: http://localhost

## docker setup

brainz was built for containers. no dependency hell. one command boot.

1. make sure docker and docker compose are installed on your system.
2. clone the repository and navigate to the root directory.
3. copy the environment file:
   
```bash
cp .env.example .env
```

4. build and start all services:

```bash
docker-compose up --build
```

5. open your browser and navigate to:

```bash
http://localhost
```

the backend will be available on port 8000, the frontend on port 3000, and the proxy on port 80.

if you want to stop all containers:

```bash
docker-compose down
```

## api

| Method | Endpoint         | Description                |
|--------|------------------|----------------------------|
| POST   | /api/llm/query   | query the model            |
| POST   | /api/llm/train   | train with user input      |
| POST   | /api/user/create | register new user          |
| GET    | /api/system/logs | stream live logs           |

## environment configuration

create `.env` from `.env.example` and update:

```
MODEL_NAME=tiiuae/falcon-rw-1b
DATABASE_URL=postgresql://user:pass@localhost:5432/brainz
DEBUG=true
```

## db init extras
```bash
# seeding control
SKIP_DB_SEEDING=false
ADMIN_USER=admin
ADMIN_KEY=root-dev-key
ADMIN_KEY_AUTO=false                 # if true → auto-generate secure key

# optional bulk user seeding (json or jsonl)
BRAINS_SEED_USERS_FILE=./database/seed/users.jsonl

# optional one-shot admin key rotation
ROTATE_ADMIN_KEY=false
ROTATE_ADMIN_KEY_VALUE=              # optional explicit value
```

## testing

```bash
pytest backend/tests
```

## license

MIT. no strings attached.
fork it, break it, rebuild it.
this isn’t ours – it’s yours.
