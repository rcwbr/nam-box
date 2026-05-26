# WebTransport Client Fixes for WebPlayer

## Analysis: Required Changes to `services/webplayer/index.html`

This document compares the WebTransport SETTINGS requirements (see `webtransport-settings-frame-exchange.md`) against the current `index.html` implementation and provides specific fixes.

---

## Critical Issues

### Issue 1: Wrong Data Reception Model (HIGH PRIORITY)

**Current Code (lines 367-385):**
```javascript
stream = await wt.createBidirectionalStream();
reader = stream.readable.getReader();
readLoop();
```

**Problem:** The JackTrip server uses QUIC **datagrams** for audio transport, not bidirectional streams. This is confirmed in:
- `WebTransportSession.cpp:274` - `mApi->DatagramSend()` for audio
- `WebTransportSession.cpp:772-798` - `DATAGRAM_RECEIVED` event handler

**Fix:** Replace stream-based reading with datagram reception:

```javascript
// After wt.ready resolves, check datagram support
if (!wt.datagramsWritable || !wt.datagramsReadable) {
    throw new Error('Server does not support WebTransport datagrams');
}

console.log('Datagrams supported, ready for audio');
setStatus('WebTransport connected - waiting for datagrams', 'connected');

// Use incomingDatagramReadable for audio data
if (wt.incomingDatagramReadable) {
    datagramReader = wt.incomingDatagramReadable.getReader();
    readDatagramLoop();
} else {
    console.warn('No incoming datagrams available, creating datagram pipe');
    // Fallback: create unreliable stream if available
}
```

---

### Issue 2: No SETTINGS Exchange Verification

**Current Code:** Sets status "Connected - Receiving audio" immediately after `wt.ready` resolves (line 358).

**Problem:** The `wt.ready` promise only indicates QUIC handshake completion, not that the required HTTP/3 SETTINGS have been exchanged.

**Required SETTINGS for WebTransport:**
- `SETTINGS_ENABLE_CONNECT_PROTOCOL` (0x08) = 1
- `SETTINGS_H3_DATAGRAM` (0x33) = 1
- `SETTINGS_ENABLE_WEBTRANSPORT` (0x2b603742) = 1

**Fix:** Add verification delay and datagram readiness check:

```javascript
// After wt.ready, wait for SETTINGS exchange to complete
console.log('WebTransport ready, waiting for SETTINGS exchange...');
await new Promise(resolve => setTimeout(resolve, 500)); // Allow SETTINGS exchange

// Verify datagram support before declaring connected
if (wt.datagramsWritable === undefined || !wt.datagramsWritable) {
    throw new Error('Server datagrams not writable - SETTINGS exchange may have failed');
}
```

---

### Issue 3: URL Path Not Specified

**Current Code (line 79):**
```html
<input type="text" id="serverUrl" value="https://localhost:4464">
```

**Problem:** The JackTrip server expects a CONNECT request to `/webtransport` path (see `WebTransportSession.cpp:1009-1010`):
```cpp
if (method == "CONNECT" && protocol == "webtransport")
```

**Fix:** Append the correct path:
```javascript
let url = serverUrlInput.value;
// Ensure path ends with /webtransport for CONNECT request
const parsed = new URL(url);
if (!parsed.pathname.includes('webtransport')) {
    parsed.pathname = parsed.pathname.replace(/\/$/, '') + '/webtransport';
    url = parsed.toString();
}
```

---

### Issue 4: No Datagram Reading Logic

The current `readLoop()` tries to read from a stream that will never receive audio data.

**Fix:** Add datagram-specific reading:

```javascript
async function readDatagramLoop() {
    console.log('Datagram readLoop started');
    try {
        while (true) {
            const { value, done } = await datagramReader.read();
            if (done) {
                console.log('Datagram stream closed');
                break;
            }
            if (value) {
                // value is a Uint8Array containing Float32 samples
                const samples = decodeFloat32Samples(value);
                feedAudio(samples);
            }
        }
    } catch (error) {
        console.error('Datagram read error:', error);
        setStatus('Datagram error', 'disconnected');
        resetConnection();
    }
}
```

---

## Complete Fix Implementation

### Step 1: Update URL Handling (around line 258)
```javascript
let url = serverUrlInput.value;
console.log('Server URL from input:', url);

// Ensure correct path for WebTransport CONNECT
try {
    const parsedUrl = new URL(url);
    if (!parsedUrl.pathname.includes('webtransport') && !parsedUrl.pathname.includes('jacktrip')) {
        parsedUrl.pathname = parsedUrl.pathname.replace(/\/$/, '') + '/webtransport';
    }
    url = parsedUrl.toString();
    console.log('Adjusted URL for WebTransport:', url);
} catch (e) {
    console.error('Invalid URL format');
}
```

### Step 2: Replace Stream Creation with Datagram Support Check (lines 367-385)
```javascript
// Check datagram support before proceeding
console.log('Checking datagram support...');
console.log('datagramsWritable:', wt.datagramsWritable);
console.log('datagramsReadable:', wt.datagramsReadable);
console.log('incomingDatagramReadable:', wt.incomingDatagramReadable);

if (!wt.datagramsWritable) {
    throw new Error('Server does not support WebTransport datagrams. Ensure jacktrip-hub is built with msquic=enabled.');
}

setStatus('WebTransport connected - datagrams ready', 'connected');

// Use incoming datagrams for audio (unreliable transport)
if (wt.incomingDatagramReadable) {
    datagramReader = wt.incomingDatagramReadable.getReader();
    console.log('Starting datagram read loop...');
    readDatagramLoop();
} else {
    throw new Error('No incoming datagram stream available');
}
```

### Step 3: Add Datagram Reading Function (replace readLoop or add new)
```javascript
async function readDatagramLoop() {
    console.log('Datagram readLoop started');
    const startTime = Date.now();
    let datagramCount = 0;
    try {
        while (true) {
            const { value, done } = await datagramReader.read();
            datagramCount++;

            if (datagramCount % 100 === 0) {
                console.log(`Datagram #${datagramCount} after ${Date.now() - startTime}ms, bytes: ${value?.byteLength || 0}`);
            }

            if (done) {
                console.log('Datagram stream closed, total datagrams:', datagramCount);
                break;
            }

            if (value && value.byteLength > 0) {
                const samples = decodeFloat32Samples(value);
                feedAudio(samples);
            }
        }
    } catch (error) {
        console.error('Datagram read error:', error);
        if (error.name !== 'TypeError' || error.message !== 'ReadableStreamDefaultReader.read() has no token') {
            setStatus('Stream error', 'disconnected');
        }
        resetConnection();
    }
}
```

### Step 4: Update Status Messages (line 358)
```javascript
// Change from:
setStatus('Connected - Receiving audio', 'connected');
// To:
setStatus('WebTransport connected - handshaking...', 'connecting');
```

Then after datagram verification:
```javascript
setStatus('Connected - Receiving datagrams', 'connected');
```

---

## Summary of Required File Changes

| Line Range | Current Behavior | Required Change |
|------------|------------------|-----------------|
| 79 | `value="https://localhost:4464"` | Keep default but add path handling in JS |
| 358 | `setStatus('Connected - Receiving audio', 'connected')` | Change to "WebTransport connected - handshaking..." |
| 367-385 | Creates bidirectional stream | Check datagram support, use `incomingDatagramReadable` |
| 419-447 | `readLoop()` reads stream data | Add `readDatagramLoop()` for datagram data |

---

## Additional Debugging Recommendations

Add these console logs for troubleshooting:

```javascript
// After connection, log session details
console.log('WebTransport session details:');
console.log('  - datagramsWritable:', wt.datagramsWritable);
console.log('  - datagramsReadable:', wt.datagramsReadable);
console.log('  - incomingDatagramReadable:', !!wt.incomingDatagramReadable);
console.log('  - outgoingDatagramWritable:', !!wt.outgoingDatagramWritable);
```