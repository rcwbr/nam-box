#!/usr/bin/env python3
"""
Check if a NAM model file was loaded into the plugin.

This uses:
1. log messages on feedback port (shows "Staging model change" when model is loaded)
2. monitor_output for output control ports (if the plugin has them)
"""

import socket
import time
import sys
import threading

NAM_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
NAM_MODEL_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2#model"
TEST_INSTANCE = 0
TEST_MODEL_PATH = "/opt/nam/models/test.nam"

feedback_received = []


def connect_socket(host, port, timeout=5):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((host, port))
    return sock


def feedback_listener(fb_sock, stop_event, duration=10):
    """Listen on feedback port for log messages and output_set notifications."""
    fb_sock.settimeout(1)
    start = time.time()
    while time.time() - start < duration and not stop_event.is_set():
        try:
            data = fb_sock.recv(4096)
            if data:
                text = data.decode('utf-8', errors='ignore').replace('\x00', '').strip()
                if text:
                    print(f"[FB] {text}")
                    feedback_received.append(text)
        except socket.timeout:
            continue
        except OSError:
            break  # Socket closed


def main():
    print("=" * 70)
    print("CHECK MODEL LOADED WORKFLOW")
    print("=" * 70)

    # Connect sockets
    print("\n[1] Connecting to control socket (5555)...")
    sock = connect_socket('mod-host', 5555)
    print("    Connected!")

    print("\n[2] Connecting to feedback socket (5556)...")
    fb_sock = connect_socket('mod-host', 5556)
    print("    Connected!")

    stop_event = threading.Event()
    fb_thread = threading.Thread(target=feedback_listener, args=(fb_sock, stop_event))
    fb_thread.daemon = True
    fb_thread.start()
    time.sleep(0.5)

    try:
        # Add plugin
        print(f"\n[3] Adding NAM plugin...")
        sock.sendall(f'add "{NAM_PLUGIN_URI}" {TEST_INSTANCE}\n'.encode())
        resp = sock.recv(4096).decode().replace('\x00', '').strip()
        print(f"<<< {resp}")
        time.sleep(2)

        # Set model
        print(f"\n[4] Setting model to {TEST_MODEL_PATH}...")
        sock.sendall(f'patch_set {TEST_INSTANCE} {NAM_MODEL_URI} {TEST_MODEL_PATH}\n'.encode())
        resp = sock.recv(4096).decode().replace('\x00', '').strip()
        print(f"<<< {resp}")

        # Wait for model loading log messages
        time.sleep(3)

        # Check feedback messages for model loading confirmation
        print("\n[5] Checking feedback for model loaded confirmation...")
        model_staged = any('Staging model' in msg for msg in feedback_received)
        model_loaded = any('model' in msg.lower() for msg in feedback_received)

        if model_staged or model_loaded:
            print("    ✓ Model messages received in feedback!")
        else:
            print("    ! No model messages in feedback (plugin may need real model file)")

        print(f"\n[FB] All feedback received:")
        for msg in feedback_received:
            print(f"    - {msg}")

    finally:
        stop_event.set()
        sock.sendall(f'remove {TEST_INSTANCE}\n'.encode())
        sock.close()
        try:
            fb_sock.close()
        except:
            pass
        print("\nConnection closed.")


if __name__ == "__main__":
    main()