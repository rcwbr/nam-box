# TLS Certificate Implementation for nam-box

## Quick Start

1. **Generate certificate** from any internet-connected machine:
```bash
CF_API_TOKEN=your_token ./scripts/generate-cert.sh
```

2. **Deploy certificates** to device:
```bash
# Copy from /tmp/nambox-ssl/ to device
scp /tmp/nambox-ssl/* root@nam-box.local:/etc/nam-box/ssl/
```

3. **Start device services**:
```bash
docker-compose -f manifests/nam-box/docker-compose.yaml up -d
```

4. **Access**: Browse to `https://nam-box-local.weber.lol`

## Files Created/Modified

| File | Purpose |
|------|---------|
| `scripts/generate-cert.sh` | Cloudflare DNS-01 certificate generation |
| `scripts/renew-cert.sh` | Certificate renewal automation |
| `services/webplayer/nginx.conf` | NGINX config with hostname redirect |
| `services/webplayer/avahi/service-https` | mDNS service discovery |
| `manifests/nam-box/docker-compose.yaml` | Docker services configuration |
| `docs/cloudflare-dns-approach.md` | Strategy documentation |

## Certificate Flow

```
Cloudflare DNS API ←→ Certbot → /tmp/nambox-ssl/ → Device /etc/nam-box/ssl/
       (DNS-01 challenge)    ↑
                             │
                    Local DNS resolves nam-box-local.weber.lol to device IP
```

## mDNS Discovery Flow

1. Device advertises as `nam-box.local` via Avahi
2. Service record includes `txt-record host=nam-box-local.weber.lol`
3. Users discover device via `https://nam-box.local`
4. Connection automatically redirects to trusted hostname

## Required Setup

1. **Cloudflare API Token** with DNS:Edit permission
2. **Local DNS resolution** for `nam-box-local.weber.lol` → device IP
3. **Port 443** accessible on local network (network_mode: host)