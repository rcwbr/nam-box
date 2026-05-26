# TURN Server Setup for WebRTC Audio Streaming

## Problem Statement

WebRTC requires UDP connectivity for audio data transport. When clients connect through tunneling/proxy services (like cloudflared), UDP ports are typically not forwarded, causing connection failures.

## What is a TURN Server?

TURN (Traversal Using Relays around NAT) is a protocol that relays traffic between WebRTC peers when direct P2P connectivity fails due to:

- NAT firewalls blocking incoming UDP
- Symmetric NAT restrictions  
- Proxy/tunnel services that don't forward UDP
- Corporate networks blocking UDP traffic

### How TURN Works

```
Client ──Signaling──┐
(WebSocket TCP)     │
                    ├── JackTrip Hub Server (ws:// or wss://)
                     │
Client ──Audio Data─┼── TURN Server (UDP/TCP/TLS) ── Audio Data ── Other Clients
(WebRTC UDP)         (relay)                              (UDP)
```

1. Client establishes signaling connection via WebSocket (TCP) - this works through cloudflared
2. Client and server attempt direct P2P connection (UDP) - this typically fails through tunnels
3. If P2P fails, both sides connect to TURN server
4. TURN server relays audio data bidirectionally

## Solution Options

### Option 1: Deploy coturn (Recommended)

**coturn** is the most popular open-source TURN server.

#### Installation (Ubuntu/Debian)
```bash
sudo apt install coturn
```

#### Configuration (`/etc/turnserver.conf`)
```
# Basic TURN settings
listening-port=3478
tls-listening-port=5349
relay-ip=YOUR_SERVER_IP
external-ip=YOUR_PUBLIC_IP
realm=jacktrip.local

# Authentication
lt-cred-mech
user=jacktrip:password123

# Security
min-port=49152
max-port=49200
log-file=/var/log/turnserver.log
simple-log
```

#### Running
```bash
# As service
sudo systemctl enable coturn
sudo systemctl start coturn

# Or standalone
turnserver -c /etc/turnserver.conf
```

### Option 2: Docker Deployment

Create a `turnserver.conf`:
```
listening-port=3478
tls-listening-port=5349
relay-ip=0.0.0.0
realm=jacktrip.local
lt-cred-mech
user=jacktrip:turnpassword
min-port=49152
max-port=49200
```

Run with Docker:
```bash
docker run -d \
  --name coturn \
  -p 3478:3478 \
  -p 3478:3478/udp \
  -p 5349:5349 \
  -p 5349:5349/udp \
  -p 49152-49200:49152-49200/udp \
  -v $(pwd)/turnserver.conf:/etc/turnserver.conf \
  instrumentisto/coturn
```

### Option 3: Use Existing TURN Services

For testing, you can use free TURN servers like:
- `turn:relay.webrtc.org:3478` (no authentication)
- Twilio TURN servers (paid service)

## JackTrip Server Configuration

The JackTrip hub server needs to be configured with TURN server credentials.

### Command Line Arguments
```bash
./jacktrip -S --stun-server sturn:YOUR_SERVER_IP:3478 --turn-server turn:YOUR_SERVER_IP:3478 --turn-username jacktrip --turn-password turnpassword
```

### Environment Variables (if supported)
```bash
export TURN_SERVER=turn:your-turn-server:3478
export TURN_USERNAME=jacktrip
export TURN_PASSWORD=turnpassword
```

## WebRTC Client Configuration

The webplayer needs to be updated to include TURN servers in the ICE configuration.

### Current (STUN only)
```javascript
peerConnection = new RTCPeerConnection({
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' }
    ]
});
```

### With TURN
```javascript
peerConnection = new RTCPeerConnection({
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { 
            urls: 'turn:your-turn-server:3478',
            username: 'jacktrip',
            credential: 'turnpassword'
        }
    ]
});
```

## Firewall Configuration

Open these ports on your TURN server:

| Port | Protocol | Purpose |
|------|----------|---------|
| 3478 | TCP/UDP | TURN signaling |
| 5349 | TCP/UDP | TURN TLS |
| 49152-49200 | UDP | TURN relay ports |

Example iptables rules:
```bash
# TURN signaling
iptables -A INPUT -p tcp --dport 3478 -j ACCEPT
iptables -A INPUT -p udp --dport 3478 -j ACCEPT
iptables -A INPUT -p tcp --dport 5349 -j ACCEPT
iptables -A INPUT -p udp --dport 5349 -j ACCEPT

# TURN relay ports
iptables -A INPUT -p udp --dport 49152:49200 -j ACCEPT
```

## Troubleshooting

### Check TURN Server Status
```bash
# Test TURN server connectivity
openssl s_client -connect your-turn-server:5349 -servername your-turn-server

# Verify ports are open
nmap -p 3478,5349,49152-49200 your-turn-server
```

### Common Issues

1. **"Permission denied" errors**: Make sure relay-ip matches your server's actual IP
2. **Clients can't connect**: Verify firewall allows UDP on relay ports
3. **One-way audio**: Check that both clients can reach the TURN server