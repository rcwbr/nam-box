#!/usr/bin/env python3
"""
Exploration script for mod-host socket protocol with feedback port monitoring.

This script connects to both:
- Control socket (port 5555): send commands, receive status responses
- Feedback socket (port 5556): receive patch_get responses and notifications

For NAM model file verification, the patch_get response is sent to the feedback port
as an LV2 Patch response message.
"""

import socket
import time
import sys
import threading

# Plugin URI for neural-amp-modeler-lv2
NAM_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
NAM_MODEL_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2#model"

# Instance we'll use for testing
TEST_INSTANCE = 0

# Global to collect feedback messages
feedback_messages = []


def connect_to_mod_host(host='mod-host', port=5555, timeout=5):
    """Connect to mod-host control socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((host, port))
    return sock


def connect_to_feedback_port(host='mod-host', port=5556, timeout=5):
    """Connect to mod-host feedback socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((host, port))
    return sock


def send_command(sock, cmd):
    """Send a command and receive response."""
    print(f">>> {cmd}")
    sock.sendall((cmd + '\n').encode())
    try:
        response = sock.recv(4096).decode('utf-8', errors='ignore')
        response = response.replace('\x00', '').strip()
        print(f"<<< {response}")
        return response
    except socket.timeout:
        print("<<< (no response within timeout)")
        return None


def parse_response(response):
    """Parse mod-host response: 'resp <status> [value]'"""
    if response and response.startswith('resp '):
        parts = response.split(None, 2)
        status = int(parts[1])
        value = parts[2] if len(parts) > 2 else None
        return {'status': status, 'value': value, 'raw': response}
    return {'status': None, 'value': None, 'raw': response}


def feedback_listener(fb_sock, stop_event, duration=5):
    """Listen on feedback port for patch messages."""
    fb_sock.settimeout(duration)
    try:
        while not stop_event.is_set():
            data = fb_sock.recv(4096)
            if data:
                # Try to decode as text
                text = data.decode('utf-8', errors='ignore').replace('\x00', '').strip()
                print(f"[FB] {text}")
                feedback_messages.append(text)
            else:
                break
    except socket.timeout:
        print("[FB] Timeout - feedback listener ending")
    except Exception as e:
        print(f"[FB] Error: {e}")


def main():
    global feedback_messages
    print("=" * 70)
    print("MOD-HOST SOCKET PROTOCOL EXPLORATION (with feedback port)")
    print("=" * 70)

    # Connect to both sockets
    print("\n[1] Connecting to control socket (5555)...")
    try:
        sock = connect_to_mod_host(port=5555)
        print("    Control socket connected!")
    except Exception as e:
        print(f"    Failed to connect: {e}")
        sys.exit(1)

    print("\n[2] Connecting to feedback socket (5556)...")
    try:
        fb_sock = connect_to_feedback_port(port=5556)
        print("    Feedback socket connected!")
    except Exception as e:
        print(f"    Warning: Could not connect to feedback port: {e}")
        fb_sock = None

    try:
        # Add NAM plugin
        print("\n[3] Adding NAM plugin instance 0...")
        resp = send_command(sock, f'add "{NAM_PLUGIN_URI}" {TEST_INSTANCE}')
        result = parse_response(resp)
        print(f"    Parsed status: {result['status']}")

        time.sleep(2)

        if result['status'] == -2:  # ERR_INSTANCE_ALREADY_EXISTS
            print("    Plugin already exists, removing first...")
            send_command(sock, f'remove {TEST_INSTANCE}')
            time.sleep(1)
            resp = send_command(sock, f'add "{NAM_PLUGIN_URI}" {TEST_INSTANCE}')
            result = parse_response(resp)

        # Start feedback listener thread
        stop_event = threading.Event()
        if fb_sock:
            feedback_messages = []
            fb_thread = threading.Thread(target=feedback_listener, args=(fb_sock, stop_event))
            fb_thread.start()

        # patch_get with model parameter (responses on feedback port)
        print("\n[4] Getting model path via patch_get...")
        resp = send_command(sock, f'patch_get {TEST_INSTANCE} {NAM_MODEL_URI}')
        time.sleep(1)

        # patch_set with test model file
        TEST_MODEL_PATH = "/opt/nam/models/test.nam"
        print(f"\n[5] Setting model file to {TEST_MODEL_PATH}...")
        resp = send_command(sock, f'patch_set {TEST_INSTANCE} {NAM_MODEL_URI} {TEST_MODEL_PATH}')
        result = parse_response(resp)
        print(f"    patch_set result: status={result['status']}")
        time.sleep(1)

        # Read model path again
        print("\n[6] Verifying model by reading it back via patch_get...")
        resp = send_command(sock, f'patch_get {TEST_INSTANCE} {NAM_MODEL_URI}')
        time.sleep(1)

        # Stop feedback listener and show all messages
        if fb_sock:
            stop_event.set()
            fb_thread.join(timeout=1)
            print(f"\n[FB] All feedback messages: {feedback_messages}")

        # Remove plugin
        print("\n[7] Removing plugin instance...")
        resp = send_command(sock, f"remove {TEST_INSTANCE}")

    finally:
        sock.close()
        if fb_sock:
            fb_sock.close()
        print("\nConnection closed.")


if __name__ == "__main__":
    main()