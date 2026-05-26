# WebTransport vs WebRTC for JackTrip

## Quick Comparison

| Feature | WebRTC | WebTransport |
|---------|--------|--------------|
| Transport | UDP (media) + TCP (signaling) | HTTP/3 (QUIC over UDP/TCP) |
| Tunnel Support | Requires TURN server | Works through HTTP proxies |
| Browser Support | All modern browsers | Chrome 97+, Firefox 113+ |
| Latency | Very low | Very low |
| Unreliable Transport | Data channel | Datagram extension |

## WebTransport Details

**Protocol Stack:**
```
JackTrip Audio Data
        ↓
WebTransport Datagrams (RFC 9221)
        ↓
HTTP/3 over QUIC
        ↓
UDP (default) or TCP (fallback)
```

**Important:** While QUIC typically uses UDP transport, HTTP/3 can work through:
- Cloudflare Tunnel (cloudflared) - supports HTTP/3 proxying
- Corporate proxies that allow HTTP/3 traffic
- Standard HTTPS port 443 inspection

## For Your Cloudflared Setup

WebTransport is the preferred solution because:

1. **Single HTTP connection** on port 443 - works through most proxies
2. **No separate signaling** - session establishment is part of HTTP/3 handshake
3. **No ICE negotiation** - no STUN/TURN servers needed
4. **Unreliable datagrams** available via `createUnreliableStream()` or `incomingUnreliableStreams`

## Building JackTrip with WebTransport

```bash
cd /workspaces/nam-box/jacktrip
CC=gcc CXX=g++ meson setup \
  -Dmsquic=enabled \
  -Drtaudio=enabled \
  -Drtaudio:jack=disabled \
  -Drtaudio:default_library=static \
  -Drtaudio:alsa=enabled \
  -Drtaudio:pulse=disabled \
  -Drtaudio:werror=false \
  -Dnofeedback=true \
  -Dlibsamplerate=enabled \
  -Ddefault_library=shared \
  builddir --wipe

meson compile -C builddir
```

## Using WebTransport Client

1. Open `services/webplayer/index-webtransport.html` in Chrome or Firefox
2. Connect to your server's HTTPS endpoint (e.g., `https://your-server.example.com:4464/webtransport`)
3. Audio will flow through the QUIC connection

## Why Not Both?

Both WebRTC and WebTransport are useful:

- **WebRTC**: Best for direct P2P connections with public IPs
- **WebTransport**: Best for proxy/tunnel scenarios, corporate networks

The fix I made to `WebRtcPeerConnection.cpp` (creating data channel before setting remote description) is still needed for WebRTC to work properly.