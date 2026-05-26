# Playing JackTrip Audio Streams in a Webpage

JackTrip supports WebRTC-based connections that can be accessed from web browsers. This document explains how to create a webpage that receives and plays audio streams from a JackTrip server.

## WebRTC Data Channel Audio Streaming

JackTrip uses WebRTC data channels for browser-based audio streaming. The audio data is transmitted as raw PCM samples over an unreliable data channel (similar to UDP behavior).

## Example Webpage

Here's a complete HTML/JavaScript example that connects to a JackTrip WebRTC server and plays received audio:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JackTrip Audio Stream</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
        }
        .controls {
            margin: 20px 0;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 8px;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
            margin-right: 10px;
        }
        input {
            padding: 8px;
            font-size: 14px;
            width: 300px;
        }
        #status {
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }
        #status.connected { background: #d4edda; color: #155724; }
        #status.disconnected { background: #f8d7da; color: #721c24; }
        #status.connecting { background: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <h1>JackTrip Audio Stream Player</h1>

    <div class="controls">
        <input type="text" id="serverUrl" placeholder="wss://server.example.com/signaling" value="wss://app.jacktrip.org/ws">
        <button id="connectBtn">Connect</button>
        <button id="disconnectBtn" disabled>Disconnect</button>
    </div>

    <div id="status" class="disconnected">Disconnected</div>

    <div>
        <label>Volume: <input type="range" id="volume" min="0" max="100" value="80"></label>
        <span id="volumeValue">80%</span>
    </div>

    <script>
        // Configuration - matches JackTrip defaults
        const AUDIO_CONFIG = {
            sampleRate: 48000,
            channels: 2,
            bufferFrameCount: 128,
            bitResolution: 16
        };

        // Audio context and nodes
        let audioContext;
        let scriptProcessor;
        let gainNode;
        let outputBuffer = [];
        let isConnected = false;

        // WebRTC connection
        let peerConnection;
        let dataChannel;
        let signalingSocket;

        // DOM elements
        const connectBtn = document.getElementById('connectBtn');
        const disconnectBtn = document.getElementById('disconnectBtn');
        const serverUrlInput = document.getElementById('serverUrl');
        const statusDiv = document.getElementById('status');
        const volumeSlider = document.getElementById('volume');
        const volumeValue = document.getElementById('volumeValue');

        // Initialize Web Audio API
        function initAudio() {
            try {
                audioContext = new (window.AudioContext || window.webkitAudioContext)({
                    sampleRate: AUDIO_CONFIG.sampleRate
                });

                gainNode = audioContext.createGain();
                gainNode.gain.value = volumeSlider.value / 100;
                gainNode.connect(audioContext.destination);

                // Create script processor for real-time audio
                scriptProcessor = audioContext.createScriptProcessor(
                    AUDIO_CONFIG.bufferFrameCount * 2,
                    0,
                    AUDIO_CONFIG.channels
                );

                scriptProcessor.onaudioprocess = (event) => {
                    if (outputBuffer.length >= AUDIO_CONFIG.bufferFrameCount) {
                        for (let channel = 0; channel < AUDIO_CONFIG.channels; channel++) {
                            const output = event.outputBuffer.getChannelData(channel);
                            for (let i = 0; i < AUDIO_CONFIG.bufferFrameCount; i++) {
                                output[i] = outputBuffer.shift();
                            }
                        }
                    } else {
                        // Fill with zeros if not enough data
                        for (let channel = 0; channel < AUDIO_CONFIG.channels; channel++) {
                            event.outputBuffer.getChannelData(channel).fill(0);
                        }
                    }
                };

                scriptProcessor.connect(gainNode);
                return true;
            } catch (error) {
                console.error('Failed to initialize audio:', error);
                return false;
            }
        }

        // Update status display
        function setStatus(message, type) {
            statusDiv.textContent = message;
            statusDiv.className = type;
        }

        // Process incoming audio data
        function handleDataChannelMessage(event) {
            if (event.data instanceof ArrayBuffer) {
                const samples = decodeAudioSamples(event.data);
                outputBuffer.push(...samples);
            }
        }

        // Decode 16-bit PCM audio samples
        function decodeAudioSamples(arrayBuffer) {
            const samples = [];
            const int16 = new Int16Array(arrayBuffer);
            for (let i = 0; i < int16.length; i++) {
                // Convert 16-bit integer to float (-1.0 to 1.0)
                samples.push(int16[i] / 32768.0);
            }
            return samples;
        }

        // Connect to JackTrip server
        async function connect() {
            try {
                if (!initAudio()) {
                    throw new Error('Failed to initialize audio');
                }

                setStatus('Connecting...', 'connecting');
                connectBtn.disabled = true;
                disconnectBtn.disabled = false;

                const serverUrl = serverUrlInput.value;

                // Create WebSocket connection for signaling
                signalingSocket = new WebSocket(serverUrl);

                signalingSocket.onopen = async () => {
                    console.log('Signaling connection established');
                };

                signalingSocket.onmessage = async (event) => {
                    const message = JSON.parse(event.data);
                    await handleSignalingMessage(message);
                };

                signalingSocket.onerror = (error) => {
                    console.error('Signaling error:', error);
                    setStatus('Connection error', 'disconnected');
                    resetConnection();
                };

                isConnected = true;

            } catch (error) {
                console.error('Connection failed:', error);
                setStatus('Connection failed: ' + error.message, 'disconnected');
                resetConnection();
            }
        }

        // Handle signaling messages from server
        async function handleSignalingMessage(message) {
            if (message.type === 'offer') {
                await handleOffer(message.sdp);
            } else if (message.type === 'answer') {
                await handleAnswer(message.sdp);
            } else if (message.type === 'ice-candidate') {
                try {
                    await peerConnection.addIceCandidate(
                        new RTCIceCandidate(message.candidate)
                    );
                } catch (error) {
                    console.error('Error adding ICE candidate:', error);
                }
            }
        }

        // Handle SDP offer from server
        async function handleOffer(sdp) {
            peerConnection = new RTCPeerConnection({
                iceServers: [
                    { urls: 'stun:stun.l.google.com:19302' }
                ]
            });

            peerConnection.onicecandidate = (event) => {
                if (event.candidate) {
                    signalingSocket.send(JSON.stringify({
                        type: 'ice-candidate',
                        candidate: event.candidate
                    }));
                }
            };

            peerConnection.ontrack = (event) => {
                console.log('Received track', event.streams[0]);
            };

            peerConnection.oniceconnectionstatechange = () => {
                console.log('ICE state:', peerConnection.iceConnectionState);
                if (peerConnection.iceConnectionState === 'connected') {
                    setStatus('Connected - Receiving audio', 'connected');
                } else if (peerConnection.iceConnectionState === 'failed') {
                    setStatus('Connection failed', 'disconnected');
                    resetConnection();
                }
            };

            // Create data channel for audio
            dataChannel = peerConnection.createDataChannel('jacktrip-audio', {
                ordered: false,
                maxRetransmits: 0
            });

            dataChannel.onopen = () => {
                console.log('Data channel open');
            };

            dataChannel.onmessage = handleDataChannelMessage;
            dataChannel.onerror = (error) => {
                console.error('Data channel error:', error);
            };

            dataChannel.onclose = () => {
                console.log('Data channel closed');
            };

            await peerConnection.setRemoteDescription({
                type: 'offer',
                sdp: sdp
            });

            const answer = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(answer);

            signalingSocket.send(JSON.stringify({
                type: 'answer',
                sdp: answer.sdp
            }));
        }

        // Handle SDP answer
        async function handleAnswer(sdp) {
            await peerConnection.setRemoteDescription({
                type: 'answer',
                sdp: sdp
            });
        }

        // Disconnect from server
        function disconnect() {
            if (dataChannel) {
                dataChannel.close();
            }
            if (peerConnection) {
                peerConnection.close();
            }
            if (signalingSocket) {
                signalingSocket.close();
            }
            if (scriptProcessor) {
                scriptProcessor.disconnect();
            }
            outputBuffer = [];
            resetConnection();
            setStatus('Disconnected', 'disconnected');
        }

        // Reset connection state
        function resetConnection() {
            isConnected = false;
            connectBtn.disabled = false;
            disconnectBtn.disabled = true;
        }

        // Update volume
        volumeSlider.addEventListener('input', () => {
            volumeValue.textContent = volumeSlider.value + '%';
            if (gainNode) {
                gainNode.gain.value = volumeSlider.value / 100;
            }
        });

        // Event listeners
        connectBtn.addEventListener('click', connect);
        disconnectBtn.addEventListener('click', disconnect);

        // Handle page unload
        window.addEventListener('beforeunload', () => {
            disconnect();
        });
    </script>
</body>
</html>
```

## Audio Data Format

JackTrip sends audio over WebRTC data channels in the following format:

- **Sample Rate**: 48000 Hz (default, configurable)
- **Channels**: 1 (mono) or 2 (stereo)
- **Bit Depth**: 16-bit signed integers
- **Byte Order**: Little-endian
- **Packet Format**: Raw PCM samples (interleaved for multi-channel)

## Decoding Audio Samples

The JavaScript example above shows how to decode 16-bit PCM:

```javascript
// Each packet contains interleaved audio samples
function decodeAudioSamples(arrayBuffer) {
    const samples = [];
    const int16 = new Int16Array(arrayBuffer);
    for (let i = 0; i < int16.length; i++) {
        // Convert 16-bit integer to float (-1.0 to 1.0)
        samples.push(int16[i] / 32768.0);
    }
    return samples;
}
```

## Connecting to JackTrip WebRTC Server

The connection flow is:

1. Establish WebSocket connection to signaling server
1. Exchange SDP offer/answer via WebSocket
1. Create WebRTC PeerConnection
1. Create data channel named "jacktrip-audio" (unreliable mode)
1. Receive audio packets and feed to Web Audio API

## Server Requirements

For WebRTC connections, the JackTrip hub server needs:

- ICE servers (STUN/TURN) configured via `--iceservers` flag
- WebSocket signaling endpoint
- WebRTC support compiled in

Example server command:

```bash
jacktrip -S --iceservers "stun:stun.l.google.com:19302,turn:turn.example.com:3478"
```

## WebTransport Alternative

JackTrip also supports WebTransport for browser connections. WebTransport provides lower latency than WebRTC data channels:

```javascript
// Example WebTransport setup (requires server support)
const wt = new WebTransport('https://server.example.com/webtransport');
await wt.ready;
const stream = await wt.createBidirectionalStream();
const reader = stream.readable.getReader();

while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    // Process audio data
}
```

## Recommended Settings

For optimal browser audio playback:

| Setting     | Value            | Notes                                  |
| ----------- | ---------------- | -------------------------------------- |
| Buffer Size | 512-1024 samples | Balance between latency and smoothness |
| Sample Rate | 48000 Hz         | Matches JackTrip default               |
| Channels    | 2 (stereo)       | Most common configuration              |
| Volume      | 0.8 (80%)        | Prevent clipping                       |

## Troubleshooting

**No audio**:

- Check browser microphone permissions
- Verify WebSocket connection to signaling server
- Check console for WebRTC errors

**Choppy audio**:

- Increase buffer size in script processor
- Check network connectivity
- Consider WebTransport instead of WebRTC
