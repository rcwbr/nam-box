# Cloudflare DNS-01 Approach for Local IoT Device

How to obtain valid Let's Encrypt certificates for a local device using Cloudflare DNS-01 challenge, with local-only HTTPS access via local DNS resolution.

## Overview

Use Cloudflare's API to automate DNS-01 challenges for Let's Encrypt, enabling certificate issuance for local-only devices without public server requirements or tunneling.

## How It Works

When `nam-box-local.weber.lol` resolves to the local device's IP (via local DNS):

```
Browser → 192.168.1.x (direct connection, no cloud routing)
         → HTTPS server with valid cert for nam-box-local.weber.lol
         → No warnings - hostname matches SAN in certificate
```

**Key Point**: DNS A records must contain IP addresses, not hostnames. `nam-box.local` is an mDNS name that cannot be used in DNS records.

## DNS Record Constraints

- **A/AAAA records**: Must contain IP addresses (e.g., `192.168.1.100`)
- **CNAME records**: Must reference existing DNS hostnames, but `nam-box.local` only exists in mDNS
- **Result**: You cannot point a DNS record to `nam-box.local` and expect it to resolve

## Implementation

### Phase 1: Certificate Acquisition

```bash
# 1. Install certbot with Cloudflare plugin
pip install certbot-dns-cloudflare

# 2. Create API token in Cloudflare Dashboard
# Permissions: Zone:DNS:Edit for weber.lol zone
echo "dns_cloudflare_api_token = YOUR_TOKEN" > ~/.secrets/cf.ini
chmod 600 ~/.secrets/cf.ini

# 3. Obtain certificate
certbot certonly --dns-cloudflare \
  --dns-cloudflare-credentials ~/.secrets/cf.ini \
  -d "nam-box-local.weber.lol"
```

### Phase 2: Device Setup

```bash
# 4. Copy certificates to device
mkdir -p /etc/nginx/ssl
scp /etc/letsencrypt/live/nam-box-local.weber.lol/*.pem device:/etc/nginx/ssl/

# 5. Configure NGINX
cat > /etc/nginx/sites-available/nam-box << 'EOF'
server {
    listen 443 ssl;
    server_name nam-box-local.weber.lol;
    
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    location / {
        root /var/www;
    }
}
EOF
```

### Phase 3: Local DNS Resolution

**Option A: Static IP + DHCP Reservation (Recommended)**
```bash
# 1. Reserve static IP for device (router DHCP reservation)
# Device always gets: 192.168.1.100

# 2. Cloudflare DNS record:
# Type: A
# Name: nam-box-local
# Content: 192.168.1.100 (this works in Cloudflare DNS)
```

**Option B: mDNS Discovery Bonus**
```bash
# Device also advertises via mDNS for discovery
# Users can find the device via https://nam-box.local
# But access requires https://nam-box-local.weber.lol for trusted cert
```

### Phase 4: Renewal Automation

```bash
# Run from any internet-connected machine monthly
certbot renew --dns-cloudflare --dns-cloudflare-credentials ~/.secrets/cf.ini

# Deploy new certs to device
rsync -av /etc/letsencrypt/live/nam-box-local.weber.lol/*.pem device:/etc/nginx/ssl/
ssh device "systemctl reload nginx"
```

## Why Not mDNS Hostname in DNS?

1. **DNS protocol requires IPs**: A records take IP addresses, not hostnames like `nam-box.local`
2. **mDNS is separate namespace**: `.local` domains only resolve on local network via multicast
3. **CNAME doesn't help**: CNAME would need `nam-box.local` in public DNS, which doesn't exist

## Required Infrastructure

1. Cloudflare-managed domain (weber.lol)
2. API token with DNS:Edit permissions
3. Local DNS resolution pointing the subdomain to device IP (via A record)
4. Device reserves IP via DHCP reservation or static assignment