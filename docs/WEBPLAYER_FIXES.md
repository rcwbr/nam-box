# WebPlayer Fixes and Findings

## Issues Fixed

### 1. Deprecated ScriptProcessorNode Warning

**Error:** `[Deprecation] The ScriptProcessorNode is deprecated. Use AudioWorkletNode instead.`

**Solution:** Replaced `ScriptProcessorNode` with `AudioWorkletNode` per modern Web Audio API recommendations.

- Created inline AudioWorklet processor using Blob URL
- Processor receives audio samples via `postMessage` from main thread
- Uses `AudioWorkletNode` API which runs on AudioWorklet global scope thread

### 2. AudioProcessor `undefined.length` Error

**Error:** `Uncaught TypeError: Cannot read properties of undefined (reading 'length')`

**Solution:** Added defensive null checks in the AudioWorklet processor:

- Check if `outputs` exists and `outputs[0]` is defined
- Check if `channelCount` is greater than 0 before accessing arrays

## WebTransport Connection Issues

### Current Error

```
net::ERR_METHOD_NOT_SUPPORTED
WebTransportError: Opening handshake failed.
```

### Root Cause Analysis

The `ERR_METHOD_NOT_SUPPORTED` error indicates the browser cannot establish a WebTransport session with the server. This typically happens when:

1. **Server Configuration**

   - JackTrip server may need WebTransport explicitly enabled via command-line flags
   - Server requires `--webtransport` flag (or similar) to enable WebTransport endpoint

1. **HTTP/3 Support**

   - WebTransport requires HTTP/3 support on the server
   - Reverse proxy must allow HTTP/3 passthrough (many proxies don't support this)

1. **URL Format**

   - Ensure the URL uses `https://` scheme (WebTransport requires secure context)
   - Verify the endpoint path matches server configuration

1. **Browser Compatibility**

   - Chrome 97+ has full WebTransport support
   - Firefox support is limited/incomplete

## Recommendations

1. **Verify Server Configuration:**

   ```bash
   # Check if JackTrip was compiled with WebTransport support
   jacktrip --help | grep -i transport

   # Example server command with WebTransport
   jacktrip -S --iceservers "stun:stun.l.google.com:19302" --webtransport
   ```

1. **Check HTTP/3 Support:**

   - Ensure reverse proxy supports HTTP/3
   - Consider direct connection if behind proxy

1. **Alternative: Use WebRTC Player**

   - The `index-webrtc.html` file uses WebRTC data channels
   - More widely supported and doesn't require HTTP/3

## Files Modified

- `services/webplayer/index.html` - AudioWorklet migration and improved error handling
