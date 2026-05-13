# Cloudflared Tunnel Setup for JackTrip WebTransport

This guide explains how to use Cloudflare Tunnel (`cloudflared`) to expose JackTrip's WebTransport endpoint with proper TLS using your own domain.

## Overview

Cloudflare Tunnel creates a secure outbound connection from your server to Cloudflare's edge. For WebTransport, this requires special consideration since UDP/QUIC support is still developing.

## Why WebTransport + Cloudflare?

1. **Single port** - UDP 4464 handles signaling and audio
1. **No ICE candidates** - No complex NAT traversal logic
1. **HTTP/3 protocol** - Built on QUIC, managed by Cloudflare
1. **Security** - TLS handled by Cloudflare edge

### Cloudflared Configuration for WebTransport

**Current Status**: Cloudflare Tunnel supports HTTP/3 (QUIC) but **does not support UDP tunnel endpoints** for WebTransport. The tunnel terminates QUIC at Cloudflare's edge.

#### Option A: Cloudflare Tunnel with TCP-to-WebTransport Proxy (Workaround)

This requires an intermediate proxy inside your container that converts TCP WebSocket to UDP WebTransport:

1. **Install cloudflared** on your host/VM:

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared
```

2. **Create the tunnel configuration** (`~/.cloudflared/config.yml`):

```yaml
tunnel: jacktrip-webtransport
credentials-file: /home/USERNAME/.cloudflared/JUMPTRA-NDEX.UMN.EDU.json

ingress:
  # HTTP/3 endpoint - cloudflared handles QUIC termination
  - hostname: wt.yourdomain.com
    service: tcp_local_port

  # Health check
  - hostname: ping.yourdomain.com
    service: https://localhost:4464/ping

  - service: http_status:404
```

3. **Run a TCP-to-QUIC proxy** (like `quic-go` or `caddy` with UDP upstream):

```bash
# Using Caddy as a reverse proxy with UDP upstream
# Caddyfile:
wt.yourdomain.com {
    reverse_proxy localhost:4464

    transport http {
        versions h3c  # HTTP/3 Cleartext to upstream
    }
}
```

**Limitation**: This approach degrades to HTTP/1.1 between the proxy and JackTrip, losing WebTransport benefits.

#### Option B: Cloudflare Tunnel over TCP with Regular WebSocket

Since cloudflared can't proxy UDP, use traditional WebSocket over TCP:

1. **Configure JackTrip for WebSocket only**:

```bash
jacktrip -S \
	--hubpatch 4 \
	--webrtc \
	--certfile /etc/ssl/cert.pem \
	--keyfile /etc/ssl/key.pem
```

2. **cloudflared config** (`~/.cloudflared/config.yml`):

```yaml
tunnel: jacktrip-websocket
credentials-file: ~/.cloudflared/TUNNEL.json

ingress:
  - hostname: ws.yourdomain.com
    service: https://localhost:4464
    originRequest:
      noTLSVerify: true  # If using self-signed cert
  - hostname: api.yourdomain.com
    service: https://localhost:443

  - service: http_status:404
```

3. **Web player connection** (in `services/webplayer/index.html`):

```javascript
const DEFAULT_URL = 'wss://ws.yourdomain.com/webrtc';
```

This works because WebSocket over TCP can traverse cloudflared, though it's WebRTC DataChannel rather than WebTransport.

#### Option C: Wait for Cloudflare UDP Tunnel Support

As of 2024, Cloudflare is developing UDP tunnel support for cloudflared. Monitor:

- https://github.com/cloudflare/cloudflared/releases
- https://blog.cloudflare.com/

Expected configuration when available:

```yaml
tunnel: jacktrip-webtransport
credentials-file: ~/.cloudflared/TUNNEL.json

ingress:
  # Future feature - UDP + QUIC passthrough
  - hostname: wt.yourdomain.com
    service: udp://localhost:4464
    udp: true
    http3: true
```

#### Option D: Use a Different Tunneling Service

**Tailscale Funnel** (supports UDP):

```bash
# Install tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Enable UDP Funnel
tailscale funnel --udp=443 4464

# This exposes UDP 4464 via your MagicDNS name
```

**Inlets PRO** (supports UDP tunnels):

```bash
# On the client (exit server with public IP)
inlets-pro udp --port 4464 --token YOUR_TOKEN

# On the server (JackTrip host)
inlets-pro udp --url wss://exit-server.com --port 4464 --token YOUR_TOKEN
```

#### Option E: Direct VM Deployment (Recommended for Production)

For WebTransport, deploy to a VM with direct UDP access:

1. **AWS EC2/Azure VM/Compute Engine** with security groups allowing UDP 4464

1. **Install JackTrip** with TLS certificates from Let's Encrypt:

```bash
# Get certificate
certbot certonly --standalone -d wt.yourdomain.com

# Start JackTrip
jacktrip -S \
	--hubpatch 4 \
	--webtransport \
	--certfile /etc/letsencrypt/live/wt.yourdomain.com/fullchain.pem \
	--keyfile /etc/letsencrypt/live/wt.yourdomain.com/privkey.pem
```

3. **Point your domain's A record** to the VM's IP (Cloudflare can proxy UDP with "DNS only" mode)

## Browser Client

### Connecting via WebTransport

```javascript
// WebTransport connection example
const wt = new WebTransport('https://yourdomain.com:4464');

try {
  // Wait for connection
  await wt.ready;
  console.log('WebTransport connection established');

  // Create bidirectional stream for audio
  const audioStream = await wt.createBidirectionalStream();

  // Read audio frames from server
  const reader = audioStream.readable.getReader();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    // value is a Uint8Array containing audio samples
    decodeAndPlayAudio(value);
  }
} catch (error) {
  console.error('WebTransport error:', error);
}
```

### Integration with Existing WebPlayer

```javascript
// In services/webplayer/index.html, add WebTransport support:

async function connectWebTransport() {
  try {
    const wtUrl = serverUrlInput.value.replace('wss://', 'https://');
    wt = new WebTransport(wtUrl);

    setStatus('Connecting via WebTransport...', 'connecting');

    await wt.ready;
    log('WebTransport connected');
    setStatus('Connected - Receiving audio', 'connected');

    // Audio handling would be similar to WebRTC
    startWebTransportAudio();

  } catch (error) {
    console.error('WebTransport connection failed:', error);
    setStatus(`Connection failed: ${error.message}`, 'disconnected');
  }
}

async function startWebTransportAudio() {
  const stream = await wt.createBidirectionalStream();
  const reader = stream.readable.getReader();

  while (wt.ready && !wt.closed) {
    const { done, value } = await reader.read();
    if (done) break;

    // Process audio data
    const samples = decodeAudioSamples(value);
    outputBuffer.push(...samples);
  }
}
```

## Comparing WebRTC vs WebTransport

| Feature         | WebRTC                | WebTransport    |
| --------------- | --------------------- | --------------- |
| Port usage      | TCP 4464 + UDP 61000+ | UDP 4464 only   |
| Signaling       | WebSocket (separate)  | Inline (HTTP/3) |
| NAT traversal   | ICE/STUN/TURN         | None needed     |
| Browser support | Universal             | Modern browsers |
| Complexity      | Higher                | Lower           |

## Troubleshooting

### QUIC Handshake Fails

1. Verify UDP 4464 is open: `nc -u yourdomain.com 4464`
1. Check certificate includes the domain: `openssl s_client -connect yourdomain.com:4464 -alpn h3`
1. Ensure server logs show "WebTransport enabled"

### Audio Choppy or Stuttering

1. Check buffer settings: `--bufstrategy 4 --queue auto`
1. Verify network latency: `< 100ms recommended`
1. Adjust sample rate: `-r 48000` (default, don't change)

### Connection Timeout

1. WebTransport connections may take 500ms-2s to establish
1. Check browser console for QUIC handshake logs
1. Ensure no corporate firewall blocking UDP 443/4464

## Production Deployment

For production use, consider:

1. **Cloudflare** - Coming soon: UDP tunnel support for WebTransport
1. **AWS ALB** - Supports UDP pass-through to containerized apps
1. **Direct VM** - Simplest option with a virtual machine
