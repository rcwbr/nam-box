# Local HTTPS with Public Domain Strategy

How to serve trusted HTTPS from a local device using a public domain name via DNS-01 ACME challenge.

## Overview

Use `nam-box-local.weber.lol` pointing to the local device's IP, with Let's Encrypt certificate obtained via DNS-01 challenge (doesn't require public server reachability).

## Implementation Steps

### Phase 1: Certificate Generation (Cloud/Controlled Environment)

```bash
# 1. Get wildcard cert for weber.lol
# Use DNS-01 challenge - you control the DNS zone
certbot certonly --manual --preferred-challenges dns \
  -d "nam-box-local.weber.lol" -d "*.weber.lol"

# This gives you 3 files:
# - /etc/letsencrypt/live/nam-box-local.weber.lol/fullchain.pem
# - /etc/letsencrypt/live/nam-box-local.weber.lol/cert.pem
# - /etc/letsencrypt/live/nam-box-local.weber.lol/privkey.pem

# 2. Bundle for device
tar -czf nam-box-cert.tar.gz \
  /etc/letsencrypt/live/nam-box-local.weber.lol/{fullchain.pem,cert.pem,privkey.pem} \
  --transform 's/.*\.pem/certs\/.pem/'
```

### Phase 2: Device Setup

```bash
# 3. Install cert on device
mkdir -p /etc/ssl/private
tar -xzf nam-box-cert.tar.gz -C /etc/ssl

# 4. Configure HTTPS server to use cert with SNI for nam-box-local.weber.lol
# Example Nginx config:
cat > /etc/nginx/sites-available/nam-box << 'EOF'
server {
    listen 443 ssl;
    server_name nam-box-local.weber.lol;
    
    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/private/privkey.pem;
    
    location / {
        root /var/www;
    }
}
EOF
```

### Phase 3: DNS Resolution (Choose One)

**Option A: Static IP + DNS A Record (Simplest)**
```bash
# On your router/DHCP server, reserve IP for nam-box
# e.g., 192.168.1.100

# In your DNS zone (weber.lol):
# nam-box-local  IN  A  192.168.1.100
```

**Option B: DNS-SD Service Discovery**
```bash
# If running Avahi/Bonjour on the device
# Create /etc/avahi/services/https.service:
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">HTTPS on %h</name>
  <service>
    <type>_https._tcp</type>
    <port>443</port>
    <txt-record>path=/</txt-record>
    <txt-record>tls-name=nam-box-local.weber.lol</txt-record>
  </service>
</service-group>
```

### Phase 4: Certificate Renewal

```bash
# Since device can't reach public internet for ACME:
# Run this from your infrastructure monthly:

# 1. Renew cert (from a machine with DNS access to weber.lol)
certbot renew --manual --preferred-challenges dns

# 2. Copy renewed certs to device
scp /etc/letsencrypt/live/nam-box-local.weber.lol/*.pem device:/etc/ssl/certs/
scp /etc/letsencrypt/archive/nam-box-local.weber.lol/privkey*.pem device:/etc/ssl/private/privkey.pem

# 3. Restart web server
ssh device "systemctl reload nginx"
```

## Key Advantages

1. **Full browser trust** - Let's Encrypt cert works everywhere
2. **No client configuration** - Users just go to `https://nam-box-local.weber.lol`
3. **Offline capable** - Device doesn't need internet for operation
4. **Renewable** - You control when to push updates

## Required Upfront Work

1. You own/control the `weber.lol` domain
2. DNS hosting that supports TXT records for ACME (any provider)
3. A machine with internet access for cert renewal (can be your laptop)