# WebTransport HTTP/3 SETTINGS Frame Exchange Requirements

## Overview

WebTransport runs over HTTP/3 (QUIC) and requires a specific SETTINGS exchange between client and server before the session can be considered fully established and ready for audio transport. This is defined in the HTTP/3 specification (RFC 9114) and the WebTransport specification (draft-ietf-wt-transport).

## The SETTINGS Exchange Flow

### 1. Connection Establishment
1. QUIC handshake completes (TLS 1.3 negotiation)
2. HTTP/3 infrastructure streams are created:
   - Control stream (type 0x00) - server-initiated
   - QPACK encoder stream (type 0x02)
   - QPACK decoder stream (type 0x03)

### 2. SETTINGS Frame Transmission
Both endpoints must send SETTINGS frames on their respective control streams:

**Client sends:**
- `SETTINGS_QPACK_MAX_TABLE_CAPACITY` (0x01) = 0
- `SETTINGS_QPACK_BLOCKED_STREAMS` (0x07) = 0
- `SETTINGS_ENABLE_CONNECT_PROTOCOL` (0x08) = 1
- `SETTINGS_H3_DATAGRAM` (0x33) = 1
- `SETTINGS_ENABLE_WEBTRANSPORT` (0x2b603742) = 1

**Server responds with:**
Same settings plus potentially additional values.

### 3. Critical Settings for WebTransport

| Setting ID | Value | Purpose |
|------------|-------|---------|
| 0x08 (SETTINGS_ENABLE_CONNECT_PROTOCOL) | 1 | Enables extended CONNECT method required for WebTransport |
| 0x33 (SETTINGS_H3_DATAGRAM) | 1 | Enables HTTP/3 datagrams (unreliable transport) |
| 0x2b603742 (SETTINGS_ENABLE_WEBTRANSPORT) | 1 | Enables WebTransport sessions |

## Implementation in JackTrip Server

From `WebTransportSession.cpp`:

```cpp
// buildSettingsFrame() - Server sends these settings
settingsPayload.push_back(0x01);  // SETTINGS_QPACK_MAX_TABLE_CAPACITY = 0
settingsPayload.push_back(0x00);
settingsPayload.push_back(0x07);  // SETTINGS_QPACK_BLOCKED_STREAMS = 0
settingsPayload.push_back(0x00);
settingsPayload.push_back(0x08);  // SETTINGS_ENABLE_CONNECT_PROTOCOL = 1
settingsPayload.push_back(0x01);
settingsPayload.push_back(0x33);  // SETTINGS_H3_DATAGRAM = 1
settingsPayload.push_back(0x01);
// SETTINGS_ENABLE_WEBTRANSPORT (0x2b603742) = 1
settingsPayload.push_back(0xab);
settingsPayload.push_back(0x60);
settingsPayload.push_back(0x37);
settingsPayload.push_back(0x42);
settingsPayload.push_back(0x01);
```

The server waits for the client's SETTINGS before sending its own:
```cpp
// From handleStreamEvent() - lines 943-958
if (frameType == Http3::FRAME_SETTINGS) {
    mClientSettingsReceived = true;
    sendSettingsFrame();  // Send our settings in response
}
```

## Common Failure Modes

### 1. Premature Connect() Readiness
The client's `WebTransport.ready` promise resolves after QUIC handshake but BEFORE SETTINGS exchange completes in some browser implementations. The webplayer code might think the session is ready when it isn't.

**Evidence in webplayer:**
```javascript
await Promise.race([
    wt.ready,
    new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Connection timeout after 10s')), 10000)
    )
]);
setStatus('Connected - Receiving audio', 'connected');
```

This status message is misleading - setting is connected before datagrams are verified to work.

### 2. Missing SETTINGS Verification
The webplayer never verifies that the required SETTINGS are actually enabled on the server side.

### 3. Datagram State Checking
The webplayer doesn't check `wt.datagramsWritable` or `wt.datagramsReadable` to confirm datagram support.

## Server-Side State Tracking

From `WebTransportSession.h`:
```cpp
bool mControlStreamReady;       // Control stream START_COMPLETE received
bool mQpackEncoderStreamReady;    // QPACK encoder stream ready
bool mQpackDecoderStreamReady;   // QPACK decoder stream ready
bool mClientSettingsReceived;     // Client's SETTINGS frame received
bool mServerSettingsSent;         // Our SETTINGS frame sent
```

These must all be true before considering the session fully ready for datagram transport.

## Timing Considerations

The WebTransportSession class uses a state machine:
- `STATE_NEW` → `STATE_CONNECTING` (after QUIC handshake)
- `STATE_CONNECTING` → `STATE_CONNECTED` (after CONNECT request accepted)
- Datagrams enabled when `DATAGRAM_STATE_CHANGED` event fires with `SendEnabled=true`

However, there's a race: the session may be marked `STATE_CONNECTED` before the client's SETTINGS arrive, meaning the server will drop any datagrams sent too early.