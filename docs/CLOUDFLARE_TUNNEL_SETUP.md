# Cloudflare Tunnel Setup for Development Testing

This guide explains how to set up Cloudflare Tunnel to forward jacktrip and webplayer ports for development testing.

## Prerequisites

- A Cloudflare account with a domain managed by Cloudflare
- `cloudflared` installed locally (for tunnel creation)

## Manual Setup Steps

### 1. Install cloudflared CLI

```bash
# Linux
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

# Or use package manager
# macOS: brew install cloudflare/cloudflare/cloudflared
```

### 2. Authenticate with Cloudflare

```bash
cloudflared tunnel login
```

This will open a browser window to authenticate and create a certificate at `~/.cloudflared/cert.pem`.

### 3. Create a Named Tunnel

```bash
cloudflared tunnel create nam-box-dev
```

This returns a tunnel ID. Note it for the next step.

### 4. Create Tunnel Configuration

Create `manifests/nam-box/cloudflared/config.yml`:

```yaml
tunnel: <TUNNEL_ID>  # Replace with your tunnel ID from step 3
credentials-file: /etc/cloudflared/<TUNNEL_ID>.json

# Note: The tunnel service uses network_mode: host to access both:
# - localhost:8443 (webplayer HTTPS) - mapped from webplayer container
# - localhost:8080 (webplayer HTTP) - mapped from webplayer container
# - localhost:4464 (jacktrip) - from jacktrip-hub with network_mode: host

ingress:
  # Webplayer HTTPS - connects to webplayer via localhost since tunnel has network_mode: host
  # The webplayer ports 8443:443 and 8080:80 are mapped to the host
  - hostname: webplayer.yourdomain.com
    service: https://localhost:8443
    originRequest:
      originServerName: localhost

  # Webplayer HTTP - connects to webplayer via localhost
  - hostname: webplayer-http.yourdomain.com
    service: http://localhost:8080

  # Jacktrip - connects to localhost:4464 since tunnel has network_mode: host
  # The jacktrip-hub service also uses network_mode: host, so both run on host network
  - hostname: jacktrip.yourdomain.com
    service: tcp://localhost:4464

  # Catch-all
  - service: http_status:404
```

### 5. Route the Tunnel

```bash
cloudflared tunnel route dns nam-box-dev webplayer.yourdomain.com
cloudflared tunnel route dns nam-box-dev jacktrip.yourdomain.com
```

### 6. Get Tunnel Token

```bash
cloudflared tunnel token nam-box-dev
```

Copy the returned token.

### 7. Set Environment Variable

```bash
export CLOUDFLARE_TUNNEL_TOKEN=<your-token-here>
```

Or create a `.env` file in the project root:

```
CLOUDFLARE_TUNNEL_TOKEN=<your-token-here>
```

### 8. Download Credentials File

Place the credentials JSON file in the same directory as config.yml:

```bash
# The credentials file is typically at:
# ~/.cloudflared/<TUNNEL_ID>.json
# Copy it to the cloudflared directory:
mkdir -p manifests/nam-box/cloudflared
cp ~/.cloudflared/ manifests/nam-box/cloudflared/ <TUNNEL_ID >.json
```

Update `config.yml` to reference the correct path if your credentials file has a different name.

### 9. Start the Development Environment

```bash
docker compose -f manifests/nam-box/docker-compose.dev.yaml up
```

## Port Forwarding Summary

| Service           | Local Port | External URL                         |
| ----------------- | ---------- | ------------------------------------ |
| Webplayer (HTTPS) | 8443       | https://webplayer.yourdomain.com     |
| Webplayer (HTTP)  | 8080       | http://webplayer-http.yourdomain.com |
| Jacktrip          | 4464/tcp   | tcp://jacktrip.yourdomain.com:4464   |

## Notes

- The tunnel service uses `network_mode: host` to access both the webplayer ports (mapped to host) and the jacktrip-hub service (which also uses `network_mode: host`)
- The webplayer container maps ports 8443:443 and 8080:80 to the host, allowing the tunnel to reach them via localhost
- Ensure your domain's DNS is managed by Cloudflare (orange cloud icon in DNS settings)
- The tunnel token is sensitive - do not commit it to version control
