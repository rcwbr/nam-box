# Cloudflare Full TLS Approach for Local IoT Device

How to serve trusted HTTPS from a local device using Cloudflare Tunnel with Full TLS (origin certificates).

## Overview

Cloudflare Tunnel routes traffic through Cloudflare's edge, allowing you to use Cloudflare Origin Certificates for the local device while presenting a publicly-trusted edge certificate to browsers.

## Architecture

```
Browser → Cloudflare Edge (public cert, trusted) 
       → Cloudflare Tunnel (encrypted proxy) 
       → Local Device (origin cert, self-signed but encrypted in transit)
```

## Implementation Steps

### Phase 1: Cloudflare Setup

```bash
# 1. Install cloudflared on the device
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# 2. Authenticate (one-time)
cloudflared tunnel login

# 3. Create tunnel
cloudflared tunnel create nam-box-local

# This returns a tunnel ID like: f34d210e-1234-4567-8901-234567890abc
```

### Phase 2: DNS Record

In Cloudflare DNS (for weber.lol zone):
- Type: CNAME
- Name: nam-box-local.weber.lol
- Target: tunnel-id.cfargotunnel.com
- Proxy status: Proxied (orange cloud)

### Phase 3: Origin Certificate

```bash
# 4. Generate Origin Certificate in Cloudflare Dashboard
# SSL/TLS → Origin Server → Create Certificate
# - Hostnames: nam-box-local.weber.lol
# - Certificate validity: 15 years recommended

# Download both files:
# - nam-box-local.weber.lol.pem (certificate)
# - nam-box-local.weber.lol-key.pem (private key)
```

### Phase 4: Device Configuration

```bash
# 5. Move certs to device
mkdir -p /etc/cloudflared
mv nam-box-local.weber.lol*.pem /etc/cloudflared/

# 6. Create tunnel config
cat > /etc/cloudflared/config.yml << 'EOF'
tunnel: nam-box-local
credentials-file: /etc/cloudflared/nam-box-local.json

ingress:
  - hostname: nam-box-local.weber.lol
    service: https://localhost:8443
    originRequest:
      originServerName: nam-box-local.weber.lol
      noTLSVerify: true  # Because origin cert is self-signed
      
  - service: http_status:404
EOF

# 7. Configure HTTPS server with origin cert
cat > /etc/nginx/sites-available/nam-box << 'EOF'
server {
    listen 8443 ssl;
    server_name nam-box-local.weber.lol;
    
    ssl_certificate /etc/cloudflared/nam-box-local.weber.lol.pem;
    ssl_certificate_key /etc/cloudflared/nam-box-local.weber.lol-key.pem;
    
    location / {
        root /var/www;
    }
}
EOF
```

### Phase 5: Run as Service

```bash
# 8. Install cloudflared as service
cloudflared service install

# 9. Start tunnel
systemctl start cloudflared

# 10. Verify
curl https://nam-box-local.weber.lol
```

## Auto-Updates and Reliability

```bash
# Create systemd service for automatic restarts
cat > /etc/systemd/system/cloudflared.service << 'EOF'
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=notify
User=root
ExecStart=/usr/local/bin/cloudflared tunnel run nam-box-local
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl enable cloudflared
```

## Network Considerations

**Firewall Requirements:**
- Outbound HTTPS (443) to Cloudflare IP ranges
- No inbound ports required
- No public IP needed on device

**Cloudflare IP Ranges (allow outbound):**
```bash
# These ranges change, so use Cloudflare's published list
# https://www.cloudflare.com/ips/
# IPv4: 173.245.48.0/20, 103.21.244.0/22, etc.
# IPv6: 2400:cb00::/32, 2606:4700::/32, etc.
```

## Advantages

1. **Zero public exposure** - Device never directly exposed to internet
2. **Automatic cert management** - Cloudflare edge cert auto-renews
3. **No port forwarding** - Works behind any NAT/firewall
4. **DDoS protection** - Protected by Cloudflare's edge
5. **Always works** - Even if device IP changes (mDNS handles this)

## Disadvantages

1. **Cloudflare dependency** - Requires functional Cloudflare service
2. **Latency** - Traffic routes through Cloudflare edge
3. **Domain locked** - Must use Cloudflare-managed DNS

## Device Requirements

- Internet outbound access (HTTPS 443)
- Cloudflare account with your domain
- 50MB RAM for cloudflared process
- ~500 bytes/sec keep-alive traffic