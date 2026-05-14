# Deployment

`wander-around` is a single FastAPI process. Deploy it like any FastAPI app. This guide describes the reference deployment used at `wanderaround.io`: a single $5/month VPS with HTTPS via Let's Encrypt.

## Single-VPS reference

Tested on Ubuntu 24.04, but any modern Linux with Python 3.10+ works.

### 1. Provision

Get any small VPS (Hetzner CPX11, DigitalOcean basic, Vultr regular). 1 vCPU + 2 GB RAM is enough for datasets up to ~100K cards. 4 vCPU + 8 GB RAM handles ~1M.

### 2. Install

```bash
ssh root@your-vps
apt update && apt install -y python3-pip nginx certbot python3-certbot-nginx
pip install wander-around
```

### 3. Drop your data

```bash
mkdir -p /opt/myworld
scp local_data.csv root@your-vps:/opt/myworld/
```

### 4. Systemd unit

`/etc/systemd/system/wander.service`:

```ini
[Unit]
Description=Wander Around — walkable 3D world over my data
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/myworld
ExecStart=/usr/bin/wander-around serve --csv /opt/myworld/local_data.csv \
    --layout ring --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now wander
systemctl status wander
```

### 5. Nginx reverse proxy

`/etc/nginx/sites-enabled/wander`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    server_tokens off;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

```bash
nginx -t && systemctl reload nginx
```

### 6. HTTPS

```bash
certbot --nginx -d yourdomain.com -d www.yourdomain.com --redirect
```

Certbot auto-renews via systemd timer. You're done.

## Air-gapped / offline

The 3D world loads `three.module.js` from a CDN by default. For air-gapped deployment, drop your own copy into `wander_around/static/`:

```bash
# Find your install dir
python -c "import wander_around; print(wander_around.__file__)"

# Copy three.js + PointerLockControls there
cp three.module.js /path/to/wander_around/static/
cp PointerLockControls.js /path/to/wander_around/static/
```

The server detects local copies and serves them instead of the CDN.

## Performance notes

- Datasets above 50K cards: serving the full `/api/cards` payload becomes the bottleneck. Replace it with a viewport-bounded endpoint that returns only cards near the player.
- Datasets above 500K cards: the 3D world loop becomes the bottleneck (one mesh per card). Use instanced meshes — see `docs/scaling.md` (TBD).
- The default `Wander.serve()` runs single-threaded uvicorn. For high-concurrency public deployments, swap in `gunicorn` with `uvicorn.workers.UvicornWorker` or front the FastAPI app from a separately-run uvicorn cluster.
