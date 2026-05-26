# udp2raw Tunnelling for WebTransport (TCP Mode)

## Problem Statement

WebTransport uses HTTP/3 over QUIC, which requires UDP transport. When using cloudflared or other TCP-only tunnels, WebTransport connections fail because the underlying QUIC protocol cannot traverse TCP-only proxies.

## Solution: udp2raw in Fake TCP Mode

udp2raw can encapsulate UDP QUIC traffic within a TCP stream that cloudflared can forward, while making the traffic appear as normal TCP to firewalls/proxies.

## Architecture

```
Browser (WebTransport) 
    ↓ (wss:// via cloudflared - TCP)
cloudflared (TCP tunnel)
    ↓ (TCP port 4464)
udp2raw (TCP mode)
    ↓ (encapsulated QUIC/UDP)
JackTrip msquic server
```

## Server Setup (with Docker Compose)

```yaml
# docker-compose.udp2raw.yaml
services:
  jacktrip-hub:
    image: jacktrip/jacktrip
    command: >
      --jacktripserver 
      --hubpatch 4 
      --bufstrategy 4 
      --certfile /etc/nam-box/ssl/server.crt 
      --keyfile /etc/nam-box/ssl/server.key
    network_mode: host  # Required for msquic QUIC traffic
    volumes:
      - nambox-ssl:/etc/nam-box/ssl
    environment:
      - JACKTRIP_PORT=4464

  udp2raw-tunnel:
    image: ghcr.io/wy-tech/udp2raw:latest
    command: >
      -s -l0.0.0.0:4464
      -r host.docker.internal:4464
      -k ${UDP2RAW_PASSWORD:-changeme123}
      --raw-mode faketcp
      --cipher aes-128-cbc
    ports:
      - "4464:4464"
    restart: unless-stopped

volumes:
  nambox-ssl:
```

### Step-by-step server setup:

1. **Build JackTrip with msquic support:**
```bash
cd /workspaces/nam-box/jacktrip
CC=gcc CXX=g++ meson setup \
  -Dmsquic=enabled \
  -Drtaudio=enabled \
  -Drtaudio:jack=disabled \
  -Drtaudio:default_library=static \
  -Drtaudio:alsa=enabled \
  -Drtaaudio:pulse=disabled \
  -Dnofeedback=true \
  builddir --wipe
meson compile -C builddir
```

2. **Create SSL certificates for msquic:**
```bash
mkdir -p /etc/nam-box/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nam-box/ssl/server.key \
  -out /etc/nam-box/ssl/server.crt \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

3. **Run udp2raw:**
```bash
# Set password
export UDP2RAW_PASSWORD="your_secure_password"

# Start the tunnel
docker-compose -f docker-compose.udp2raw.yaml up -d
```

## cloudflared Configuration

```yaml
# .cloudflared/config.yml
tunnel: your-tunnel-id
credentials-file: /etc/cloudflared/your-tunnel-id.json

originRequest:
  originServerName: localhost
  caPool: /etc/nam-box/ssl/server.crt

ingress:
  - hostname: nam-box-jacktrip.example.com
    service: tcp://localhost:4464
  - service: http_status:404
```

## Client Webpage Configuration

Use the existing WebTransport client, but ensure the URL matches:

```html
<!-- services/webplayer/index-webtransport.html -->
<script>
const serverUrl = 'https://nam-box-jacktrip.example.com:4464/webtransport';

wt = new WebTransport(serverUrl, {
    allowPooling: true
});

wt.onstatechange = () => {
    if (wt.readyState === 'connected') {
        console.log('WebTransport connected via udp2raw tunnel');
    }
};
</script>
```

## Client Native udp2raw Setup (for WebSockets)

For the WebRTC client to work through cloudflared, you need udp2raw running locally:

```bash
# Client: Connect to server's udp2raw
./udp2raw -c -l127.0.0.1:4464 -r nam-box-jacktrip.example.com:4464 -k your_secure_password --raw-mode faketcp

# Then point WebRTC client to localhost
# wss://127.0.0.1:4464/webrtc
```

## Important Considerations

1. **Port 4464 must be forwarded through cloudflared as TCP** - this is already your config
2. **msquic server must bind to all interfaces** (0.0.0.0:4464) for udp2raw to forward to it  
3. **fake-tcp mode** makes UDP traffic resemble TCP to bypass firewalls that block QUIC
4. **Encryption key (-k)** must match between client and server

## Verification Steps

1. Check udp2raw is listening:
```bash
netstat -tlnp | grep 4464
```

2. Test TCP connectivity through cloudflared:
```bash
curl -vk https://nam-box-jacktrip.example.com/ping
```

3. Check msquic logs for QUIC handshake:
```bash
docker logs jacktrip-hub 2>&1 | grep -i quic
```

## Troubleshooting

**Connection times out:**
- Verify udp2raw password matches
- Check msquic is listening on correct interface (0.0.0.0 not 127.0.0.1)
- Ensure cloudflared tunnel shows as active: `cloudflared tunnel list`

**Certificate errors:**
- Verify certificate SubjectAltName includes your domain
- Use `openssl x509 -in server.crt -text -noout` to inspect

**High latency:**
- UDP header compression is disabled in TCP mode
- Consider increasing buffer sizes in JackTrip command line