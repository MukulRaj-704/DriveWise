# Deployment Guide (No Docker)

This guide covers running DriveWise directly with Python + Node — no containers. It targets an Oracle Cloud "Always Free" VM (genuinely free forever, always-on, no cold starts), but the steps apply to any plain Ubuntu VM.

## Environment strategy

| | Development | Production |
|---|---|---|
| LLM | `LLM_PROVIDER=ollama` | `LLM_PROVIDER=groq`, `LLM_FALLBACK_PROVIDERS=["gemini"]` |
| Embeddings | `EMBEDDING_PROVIDER=sentence_transformers` (local) | same — runs fine on a VM with a few GB RAM |
| Database | local Postgres or hosted (Neon) | hosted Postgres (Neon/Supabase) recommended, or Postgres on the same VM |
| Where it runs | your laptop | Oracle Cloud VM (or any VPS) |

Only `.env` changes between the two — no code changes, ever.

---

## Part 1 — Provision the VM

1. Create an Oracle Cloud "Always Free" account at [cloud.oracle.com](https://cloud.oracle.com).
2. **Compute → Instances → Create Instance.**
3. Shape: **VM.Standard.A1.Flex (Ampere ARM)** — Always Free tier gives up to 4 OCPU / 24GB RAM, comfortably enough for the embedding + reranker models.
4. Image: **Ubuntu 22.04**.
5. Generate/download an SSH key pair during creation — you'll need it to connect.
6. Note the instance's public IP once it's running.

### Open the required ports (two places — this trips people up)

**A. Oracle Console** → your VM's *Virtual Cloud Network* → *Security List* → *Ingress Rules* → add rules for:
- `80` (HTTP)
- `443` (HTTPS, if you set up a domain + SSL)

**B. Inside the VM itself** (Ubuntu's own firewall), after SSH-ing in:
```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```
Both A and B must be open, or you'll get "connection refused" with no obvious reason why.

---

## Part 2 — Install dependencies on the VM

SSH in first:
```bash
ssh -i /path/to/your/key.pem ubuntu@<vm-public-ip>
```

```bash
sudo apt update && sudo apt upgrade -y

# Python 3.12 + venv
sudo apt install -y python3.12 python3.12-venv python3-pip

# Node.js 20 (for building the frontend)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Nginx (reverse proxy + static file server)
sudo apt install -y nginx

# PostgreSQL (skip this if you're using a hosted DB like Neon instead)
sudo apt install -y postgresql postgresql-contrib
```

If you installed Postgres locally, create the database and user:
```bash
sudo -u postgres psql -c "CREATE USER drivewise WITH PASSWORD 'choose-a-strong-password';"
sudo -u postgres psql -c "CREATE DATABASE drivewise OWNER drivewise;"
```
Then your `DATABASE_URL` will be:
```
postgresql+asyncpg://drivewise:choose-a-strong-password@localhost:5432/drivewise
```
If using a hosted provider (Neon/Supabase), just copy their connection string instead — no local Postgres install needed at all.

---

## Part 3 — Deploy the backend

```bash
# Get your code onto the VM (git clone, or scp the folder over)
git clone <your-repo-url> ~/drivewise
cd ~/drivewise

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env   # set DATABASE_URL, JWT_SECRET_KEY (generate a real random one),
            # LLM_PROVIDER=groq, LLM_FALLBACK_PROVIDERS=["gemini"],
            # GROQ_API_KEY, GEMINI_API_KEY, CORS_ORIGINS=["https://yourdomain.com"]
```

Generate a strong JWT secret:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Test it runs:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Ctrl+C once you've confirmed http://<vm-ip>:8000/api/v1/health responds
```

### Keep it running permanently with systemd

Create `/etc/systemd/system/drivewise-backend.service`:
```ini
[Unit]
Description=DriveWise FastAPI backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/drivewise
Environment="PATH=/home/ubuntu/drivewise/.venv/bin"
ExecStart=/home/ubuntu/drivewise/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable drivewise-backend
sudo systemctl start drivewise-backend
sudo systemctl status drivewise-backend   # should show "active (running)"
```

This survives VM reboots and restarts automatically if the process crashes — no "sleeping after 15 minutes" behavior like free-tier PaaS platforms.

---

## Part 4 — Build and deploy the frontend

```bash
cd ~/drivewise/frontend
npm install

# Point the build at your backend's public URL
echo "VITE_API_BASE_URL=https://yourdomain.com/api/v1" > .env.production
# (or http://<vm-ip>/api/v1 if you don't have a domain yet)

npm run build   # outputs to frontend/dist
```

Nginx will serve this `dist/` folder directly as static files — no Node process needs to stay running for the frontend.

---

## Part 5 — Wire up Nginx as the reverse proxy

Create `/etc/nginx/sites-available/drivewise`:
```nginx
server {
    listen 80;
    server_name yourdomain.com;   # or the VM's public IP if you don't have a domain

    # Frontend — serve the built static files
    root /home/ubuntu/drivewise/frontend/dist;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend — proxy /api requests to FastAPI running on 127.0.0.1:8000
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/drivewise /etc/nginx/sites-enabled/
sudo nginx -t          # test config syntax
sudo systemctl restart nginx
```

Visit `http://<vm-ip>` — you should see the DriveWise frontend, and it should be able to talk to the backend through `/api/...`.

---

## Part 6 (optional) — Domain + free HTTPS

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```
Certbot edits the Nginx config for you and auto-renews the certificate. Point your domain's DNS A record at the VM's public IP before running this.

---

## Ollama on production? Generally no

For production, use `LLM_PROVIDER=groq` with `LLM_FALLBACK_PROVIDERS=["gemini"]` instead of running Ollama on the VM. Running an 8B model on CPU is slow and eats RAM you'd rather give to the embedding/reranker models. Reserve Ollama for local development where its zero-cost, zero-rate-limit nature is the whole point.

## Production checklist

- [ ] Strong, random `JWT_SECRET_KEY` (never the `.env.example` placeholder)
- [ ] `DATABASE_URL` points at a real Postgres instance (local or hosted), not SQLite
- [ ] `CORS_ORIGINS` restricted to your actual domain
- [ ] `LLM_PROVIDER=groq` + `LLM_FALLBACK_PROVIDERS=["gemini"]` with both API keys set
- [ ] `DEBUG=false`, `APP_ENV=production`, `LOG_JSON=true`
- [ ] systemd service enabled (`systemctl enable`) so it survives reboots
- [ ] Nginx configured and (ideally) HTTPS via certbot
- [ ] `storage/uploads` and `storage/vectors` on a path that persists (they do by default on a VM — just don't delete the folder)

## Migrations note

`init_db()` (`app/core/database.py`) uses `Base.metadata.create_all` for zero-friction startup. For real schema evolution:
```bash
pip install alembic
alembic init alembic
# point alembic/env.py's target_metadata at app.core.database.Base.metadata
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```
Then remove the `create_all` call from `app/main.py`'s lifespan hook and run `alembic upgrade head` as a deploy step instead.

## Redeploying after code changes

```bash
cd ~/drivewise
git pull
source .venv/bin/activate
pip install -r requirements.txt          # if dependencies changed
sudo systemctl restart drivewise-backend

cd frontend
npm install                               # if frontend dependencies changed
npm run build
# Nginx serves the new dist/ immediately — no restart needed for frontend-only changes
```
