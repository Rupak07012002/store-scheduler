# Hosting This on Your Own Hardware, Reachable From the Internet

This covers taking the machine running Store Scheduler (already working on your local network per [setup-runbook.md](setup-runbook.md)) and making it reachable from anywhere - so your managers and employees can use it from their phones, not just on your office WiFi.

**Read this whole page before doing anything** - the two paths below have a real trade-off, and picking wrong means redoing router configuration later.

## The one thing that decides which path you take: CGNAT

Most home/small-business internet connections in 2026 no longer give you a real public IP address - your ISP puts you behind **CGNAT** (Carrier-Grade NAT), sharing one public IP across many customers. If you're behind CGNAT, **port forwarding will not work at all**, no matter how correctly you configure it, because there's no direct path from the internet to your router.

**Check this first:**
1. Log into your router's admin page and find its "WAN IP" or "Internet IP."
2. Go to [whatismyipaddress.com](https://whatismyipaddress.com) (or similar) from a device on the same network and note the IP it shows you.
3. If those two IPs **match**, you have a real public IP - either path below works.
4. If they **don't match**, you're behind CGNAT - skip straight to **Path A**, because **Path B is not possible** for you.

If you're not sure, or don't want to deal with your router at all, **Path A works regardless** and is genuinely simpler to set up. It's the recommended default for exactly this reason.

## Path A (Recommended): Cloudflare Tunnel

A small program (`cloudflared`) runs on your machine and opens an *outbound* connection to Cloudflare, which then routes public traffic to it. No inbound ports, no router configuration, works even behind CGNAT, and TLS is handled for you automatically.

### 1. Get a domain and add it to Cloudflare

If you don't have a domain, buy one (~$10-15/year from any registrar, or Cloudflare's own registrar at cost). Then, in the [Cloudflare dashboard](https://dash.cloudflare.com):
1. "Add a site," enter your domain, choose the **Free** plan.
2. Cloudflare gives you two nameservers - go to wherever you bought the domain and change its nameservers to those two. This can take a few minutes to a few hours to take effect.

### 2. Install `cloudflared` on the machine running the app

```bash
# macOS
brew install cloudflared

# Linux (Debian/Ubuntu)
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
```

### 3. Log in and create a tunnel

```bash
cloudflared tunnel login          # opens a browser, pick your domain
cloudflared tunnel create store-scheduler
```

This prints a tunnel ID and creates a credentials file (`~/.cloudflared/<tunnel-id>.json`) - this file is a credential; treat it like a password.

### 4. Route a hostname to the tunnel

```bash
cloudflared tunnel route dns store-scheduler scheduler.yourdomain.com
```

### 5. Configure the tunnel to point at your app

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: store-scheduler
credentials-file: /home/youruser/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: scheduler.yourdomain.com
    service: http://localhost:80
  - service: http_status:404
```

That `http://localhost:80` is the nginx reverse proxy from this repo (see step 6) - the tunnel hands traffic to it exactly like a normal request would arrive at port 80, just without port 80 ever being opened on your router.

### 6. Start the app's nginx proxy (still needed - it's what routes `/api/` vs `/` to the right container)

```bash
cd store-scheduler
echo "VITE_API_BASE_URL=/api/v1" >> .env
echo "CORS_ALLOWED_ORIGINS=https://scheduler.yourdomain.com" >> .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile proxy up -d --build
```

**Why these two env vars matter**: `VITE_API_BASE_URL=/api/v1` makes the frontend call the API as a relative path (since nginx now serves both under one origin) - this is baked into the frontend at *build* time, so changing it later needs `--build` again, not just a restart. `CORS_ALLOWED_ORIGINS` locks the API down to only accept requests from your real domain instead of `*` - see `app/main.py` for how this is read.

### 7. Run the tunnel

```bash
cloudflared tunnel run store-scheduler
```

Visit `https://scheduler.yourdomain.com` - Cloudflare terminates TLS for you automatically (free, auto-renewing certificate), so it's already `https://` with no certbot step needed.

**Keep the tunnel running permanently**: install it as a system service so it survives reboots:
```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared   # Linux
# or on macOS: brew services start cloudflared
```

## Path B: Port Forwarding + Dynamic DNS + Let's Encrypt

Only viable if you confirmed above that you have a real public IP (no CGNAT). This is the "classic" approach: your router directly accepts inbound connections on ports 80/443 and forwards them to this machine.

### 1. Give the machine a fixed local IP
In your router's DHCP settings, reserve a fixed local IP (e.g. `192.168.1.50`) for this machine's MAC address, so port forwarding rules don't break when it gets a new IP after a reboot.

### 2. Set up Dynamic DNS
Your home IP changes periodically even without CGNAT. Sign up for a free dynamic DNS service (e.g. [DuckDNS](https://www.duckdns.org) or use Cloudflare's own DNS with a small update script) and install its update client on this machine - it periodically tells the DNS provider "this is my current IP," so `scheduler.yourdomain.com` always resolves correctly.

### 3. Forward ports 80 and 443
In your router's admin page, add port-forwarding rules: external port 80 → this machine's local IP, port 80 (and the same for 443). **Do not forward any other port** - specifically not 5432 (Postgres) or 8000/5173 (the app's dev ports) - the base `docker-compose.yml` in this repo no longer exposes those to the host at all when run via `docker-compose.prod.yml`, so there's nothing there to accidentally forward anyway.

### 4. Bring up the app with the nginx proxy
```bash
cd store-scheduler
echo "VITE_API_BASE_URL=/api/v1" >> .env
echo "CORS_ALLOWED_ORIGINS=https://scheduler.yourdomain.com" >> .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile proxy up -d --build
```

### 5. Get a real TLS certificate with Certbot
```bash
docker run -it --rm --network host \
  -v ./infra/certbot/etc:/etc/letsencrypt \
  certbot/certbot certonly --standalone -d scheduler.yourdomain.com
```
Then update `infra/nginx/nginx.conf` to add a `listen 443 ssl;` server block pointing at the certificate files Certbot just created, and reload nginx (`docker compose -f docker-compose.yml -f docker-compose.prod.yml exec nginx nginx -s reload`). Certificates expire every 90 days - set up a cron job to re-run Certbot and reload nginx monthly.

## Security checklist before either path goes live with real data

- [ ] Changed `JWT_SECRET_KEY` in `.env` to a long random string (`openssl rand -hex 32` generates one).
- [ ] Changed `POSTGRES_PASSWORD` in `.env` from the default.
- [ ] Re-seeded with real owner credentials, or at minimum changed the seeded Owner password (default `owner-password-change-me` is public in this repo's `.env.example` and seed script - anyone who's seen this codebase knows it).
- [ ] Set `CORS_ALLOWED_ORIGINS` to your actual domain, not `*`.
- [ ] Confirmed `docker compose -f docker-compose.yml -f docker-compose.prod.yml ps` shows **no** host port bindings for `postgres`, `backend`, or `frontend` - only `nginx` should show published ports.
- [ ] The machine's OS and Docker are set to receive security updates.
- [ ] You have a backup of the Postgres database somewhere *other than this machine* (see [setup-runbook.md](setup-runbook.md)'s backup section) - a machine reachable from the internet is a machine worth having a real backup plan for.

## Reasonable next question: "should I really run this on hardware in my office?"

This guide does what you asked, but it's worth saying plainly: a machine you're personally responsible for patching, backing up, and keeping physically secure - now reachable from the internet - carries more operational risk than a $6/month managed VPS that comes with a provider's network security team behind it. If uptime or security ever becomes a real worry, [scaling-guide.md](scaling-guide.md) item 7 covers moving these same containers to a cloud VPS or Kubernetes with no code changes - it's a deployment-target change, not a rewrite, whenever you're ready for it.
