# WebTransport Connection Debug Report

**Date:** 2026-05-15
**Issue:** WebTransport connection between webpage client and JackTrip server failing with "Transport shutdown" error

## Executive Summary

The WebTransport connection is failing due to a combination of:
1. **Certificate validation mismatch** between browser trust store and msquic
2. **Premature session state transitions** causing the server to drop the connection
3. **Incomplete SETTINGS frame exchange** timing issues

---

## Observed Symptoms

### Client Logs
```
[02:08:42] Server URL: https://nam-box.local:4464/webtransport
[02:08:42] WebTransport supported: true
[02:08:42] Creating WebTransport connection...
[02:08:42] WebTransport object created, initial state: undefined
[02:08:42] WARNING: No incomingDatagramReadable
[02:08:52] Connection failed:
[02:08:52] Error name: WebTransportError
[02:08:52] Error stack: undefined
```

### Server Logs
```
May 15 02:08:52 62c70cfd91b9 jacktrip[78]: WebTransportSession: QUIC connection established from 172.20.0.1:45560
May 15 02:08:52 62c70cfd91b9 jacktrip[78]: WebTransport session failed for worker 0: Transport shutdown
May 15 02:08:08 62c70cfd91b9 jacktrip[78]: UdpHubListener: Removing worker 0
```

---

## Root Cause Analysis

### 1. Transport Shutdown Error (10-second timeout)

**Location:** `WebTransportSession.cpp:716-723`

The server logs show:
1. QUIC connection is established at `02:08:52`
2. Transport shutdown occurs at `02:09:08` (~16 seconds later)
3. This matches browser timeout behavior (15s Promise.race in webplayer)

**Why This Happens:**
- The server enters `STATE_CONNECTED` after QUIC handshake
- Infrastructure streams (control, QPACK encoder/decoder) are created
- SETTINGS exchange must complete before session is fully ready
- Browser's `wt.ready` resolves before SETTINGS exchange completes
- If SETTINGS or datagram negotiation fails, transport closes

### 2. Certificate Trust Mismatch

**From Http3Server.cpp:144-171**
```cpp
QUIC_CREDENTIAL_CONFIG credConfig{};
credConfig.Type  = QUIC_CREDENTIAL_TYPE_CERTIFICATE_FILE;
credConfig.Flags = QUIC_CREDENTIAL_FLAG_NONE;
```

**The Problem:**
- Self-managed CA cert is trusted on client device (OS trust store)
- msquic uses its own certificate validation, not the OS store
- No explicit root certificate configuration in msquic credential setup
- The `QUIC_CREDENTIAL_FLAG_NONE` doesn't specify custom trust anchors

**Evidence:**
- Logs show "Loaded certificate chain (2 certificates)" confirming chain is being loaded
- But msquic may not trust the self-signed root CA

### 3. Race Condition in State Machine

**From WebTransportSession.cpp:701-714**
```cpp
case QUIC_CONNECTION_EVENT_CONNECTED:
    createInfrastructureStreams();
    // Connection is ready, but we wait for HTTP/3 CONNECT before declaring
    // session established
    break;
```

**Issue:** The session immediately transitions to `STATE_CONNECTING` but:
- Infrastructure streams are created but not guaranteed to have `START_COMPLETE`
- Client's SETTINGS frame hasn't been received yet
- Server's SETTINGS won't send until `mClientSettingsReceived` is true

**From WebTransportSession.cpp:480-482:**
```cpp
if (!mClientSettingsReceived) {
    return;  // Won't send SETTINGS until client sends theirs
}
```

---

## Required SETTINGS for WebTransport

| Setting ID | Value | Purpose |
|------------|-------|---------|
| 0x08 | 1 | SETTINGS_ENABLE_CONNECT_PROTOCOL - Enables extended CONNECT |
| 0x33 | 1 | SETTINGS_H3_DATAGRAM - Enables HTTP/3 datagrams |
| 0x2b603742 | 1 | SETTINGS_ENABLE_WEBTRANSPORT - Enables WebTransport |

The browser must send these; the server responds with the same.

---

## Troubleshooting Steps

### 1. Verify Certificate Chain
```bash
# Check certificate chain completeness
openssl s_client -connect nam-box.local:4464 -alpn h3 -servername nam-box.local -showcerts

# Verify the full chain is being sent (should show 2+ certificates)
```

### 2. Enable msquic Debugging
```bash
export QUIC_TRACE_API=1
# Also add verbose logging to jacktrip startup
```

### 3. Check Infrastructure Stream Creation
Add logging to `createInfrastructureStreams()` and verify all three streams:
- Control stream (type 0x00)
- QPACK encoder stream (type 0x02)  
- QPACK decoder stream (type 0x03)

### 4. Verify SetParam Call
The `SetParam` call to enable datagrams (line 130-131) should be verified:
```cpp
settings.DatagramReceiveEnabled = TRUE;
// Check the returned status for failures
```

---

## Known Issues from Documentation

### webtransport-client-fixes.md
- Wrong data reception model (streams vs datagrams)
- No SETTINGS exchange verification
- No datagram state checking

### webtransport-settings-frame-exchange.md
- Premature `wt.ready` resolution
- Missing SETTINGS verification in webplayer
- Race condition: session marked connected before client SETTINGS arrive

---

## Recommended Fixes

### 1. Certificate Trust Solution - Client-Side Hash Whitelisting

For self-signed certificates, browsers require `serverCertificateHashes` option in the WebTransport constructor. This is the **most likely fix** since:

- The CA is trusted on the OS level, but browsers don't use OS trust store for QUIC
- `QUIC_CREDENTIAL_TYPE_CERTIFICATE_FILE` doesn't affect browser trust
- Browser WebTransport requires explicit certificate hash whitelisting

**Required Change in nam-box-player.html:**
```javascript
// Calculate SHA-256 hash of the server certificate
// Use openssl: openssl x509 -in server.crt -outform DER | openssl dgst -sha256 -binary

const certHash = new Uint8Array([
    // 32-byte SHA-256 hash of server certificate in DER format
]).buffer;

wt = new WebTransport(url, {
    serverCertificateHashes: [certHash]
});
```

### 2. Alternative: Use Let's Encrypt Certificate
Per `local-https-strategy.md`, the recommended approach is using Let's Encrypt with DNS-01 challenge for full browser trust without client configuration.

### 3. Server-Side msquic Configuration


### 2. Add More Verbose Logging to Server
```cpp
// In handleInfraStreamEvent, log START_COMPLETE status
// In handleConnectionEvent, log DATAGRAM_STATE_CHANGED events
```

### 3. Client-Side WebTransport Constructor Options
The current code uses `new WebTransport(url)` without options. For self-signed certs:
```javascript
// Without options - fails for self-signed certs
wt = new WebTransport(url);

// With certificate hash - works for self-signed
wt = new WebTransport(url, {
    serverCertificateHashes: [cryptoSHA256(DER_encoded_cert)]
});
```

To get the hash:
```bash
# Get SHA-256 hash of certificate in DER format
openssl x509 -in server.crt -outform DER | openssl dgst -sha256 -binary | xxd -p
```

### 4. Debug Certificate Hash Calculation

The certificates are generated by `services/certs/Dockerfile` which:
1. Creates a self-signed CA (`ca.key`, `ca.crt`)
2. Creates a server certificate signed by the CA with SAN for `nam-box.local`
3. **Appends the CA certificate to server.crt** (line 68) for proper chain

**Certificate Chain Format (server.crt):**
```
-----BEGIN CERTIFICATE-----  (Server certificate - CN=nam-box.local)
...
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----  (CA certificate - CN=nam-box-local-ca)
...
-----END CERTIFICATE-----
-----BEGIN RSA PRIVATE KEY-----
...
-----END RSA PRIVATE KEY-----
```
- Wait for SETTINGS exchange before declaring connected
- Add delay after `wt.ready` to allow SETTINGS negotiation
- Check `datagramsWritable` before proceeding

---

## Files Involved

| File | Purpose |
|------|---------|
| `jacktrip/src/webtransport/WebTransportSession.cpp` | Session management |
| `jacktrip/src/http3/Http3Server.cpp` | QUIC server, certificate loading |
| `jacktrip/src/UdpHubListener.cpp` | Certificate chain loading |
| `services/webplayer/nam-box-player.html` | Client WebTransport code |
| `docs/webtransport-settings-frame-exchange.md` | Protocol documentation |

---

## Next Steps

1. [x] **Calculate certificate hash** - Run: `openssl x509 -in server.crt -outform DER | openssl dgst -sha256 -binary | xxd -p`
2. [x] **Add serverCertificateHashes to webplayer** - This is the primary fix
3. [ ] **Add verbose logging** to infrastructure stream creation (Http3Server.cpp)
4. [ ] **Check msquic status codes** in shutdown events (add logging for error codes at line 720-723)

## Current Status (2026-05-15 14:20)

### Progress Made
- Certificate hash calculated: `fc63fdc8c65c0ca578d85b76a7a0fe1d23d61864b85227f3cc30a189c095244a`
- `serverCertificateHashes` added to WebTransport constructor in `services/webplayer/nam-box-player.html`
- HTTPS test now passes (certificate trust established)
- Added verbose WebTransport logging to `WebTransportSession.cpp` for SETTINGS exchange debugging

### Verbose Logging Added
The following log points were added to `jacktrip/src/webtransport/WebTransportSession.cpp`:

1. **Connection events** (line ~710):
   - `QUIC_CONNECTION_EVENT_CONNECTED` - when QUIC handshake completes
   - `QUIC_CONNECTION_EVENT_SHUTDOWN_INITIATED_BY_TRANSPORT` - with error code
   - `QUIC_CONNECTION_EVENT_DATAGRAM_STATE_CHANGED` - datagram negotiation status

2. **Infrastructure stream events** (line ~1130):
   - Control/QPACK stream START_COMPLETE events
   - Stream ready status tracking

3. **SETTINGS exchange** (line ~473):
   - Client SETTINGS received notification
   - SETTINGS frame send attempts with conditions
   - Frame size logging

### Remaining Issue
The WebTransport connection still fails with "Transport shutdown" during HTTP/3 SETTINGS exchange:
- `WARNING: No incomingDatagramReadable` - indicates session not fully established
- Browser's `wt.ready` times out (15s) before SETTINGS handshake completes
- Server logs show QUIC connection established, then immediate shutdown by transport

### Next Steps
1. Rebuild and run with verbose logging enabled (`WEBTRANSPORT_VERBOSE`)
2. Check for:
   - Whether client SETTINGS frame is received
   - Whether control stream becomes ready
   - Whether SETTINGS frame is sent
   - Whether DATAGRAM_STATE_CHANGED shows datagrams enabled
3. Verify the shutdown status code to identify the specific error