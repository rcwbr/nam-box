#!/usr/bin/env python3
"""
Exploration script for mod-host socket protocol.

This script connects to the mod-host TCP socket on port 5555 and:
1. Tests plugin add/remove commands
2. Explores the patch_set workflow for setting NAM model files
3. Tests parameter setting/getting
4. Tests bypass functionality

Based on mod-host protocol (from README.md and mod-host.h):
- add <lv2_uri> <instance_number>
- remove <instance_number> OR remove -1 (all)
- patch_set <instance> <property_uri> <value>
- patch_get <instance> <property_uri>
- param_set <instance> <param_symbol> <value>
- param_get <instance> <param_symbol>
- bypass <instance> <0|1>
- connect <origin_port> <destination_port>
- disconnect <origin_port> <destination_port>
"""

import socket
import time
import sys

# Plugin URI for neural-amp-modeler-lv2
NAM_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
NAM_MODEL_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2#model"

# Instance we'll use for testing
TEST_INSTANCE = 0


def connect_to_mod_host(host='mod-host', port=5555, timeout=5):
    """Connect to mod-host socket."""
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
        # Strip null bytes and whitespace
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


def main():
    print("=" * 70)
    print("MOD-HOST SOCKET PROTOCOL EXPLORATION (TCP socket on port 5555)")
    print("=" * 70)

    # Connect to mod-host
    print("\n[1] Connecting to mod-host...")
    try:
        sock = connect_to_mod_host()
        print("    Connected successfully!")
    except Exception as e:
        print(f"    Failed to connect: {e}")
        sys.exit(1)

    try:
        # Add NAM plugin (this is the core command)
        print("\n[2] Adding NAM plugin instance 0...")
        resp = send_command(sock, f'add "{NAM_PLUGIN_URI}" {TEST_INSTANCE}')
        result = parse_response(resp)
        print(f"    Parsed status: {result['status']}")

        # Wait for plugin to load
        time.sleep(2)

        # Check if plugin loaded (re-add if already exists)
        if result['status'] == -2:  # ERR_INSTANCE_ALREADY_EXISTS
            print("    Plugin already exists, removing first...")
            send_command(sock, f'remove {TEST_INSTANCE}')
            time.sleep(1)
            resp = send_command(sock, f'add "{NAM_PLUGIN_URI}" {TEST_INSTANCE}')
            result = parse_response(resp)
            print(f"    Re-added, status: {result['status']}")

        # patch_get for model (to see initial state - blank)
        print("\n[3] Getting model path via patch_get (initial)...")
        resp = send_command(sock, f'patch_get {TEST_INSTANCE} {NAM_MODEL_URI}')

        # patch_set with test model file
        TEST_MODEL_PATH = "/opt/nam/models/test.nam"
        print(f"\n[4] Setting model file to {TEST_MODEL_PATH}...")
        resp = send_command(sock, f'patch_set {TEST_INSTANCE} {NAM_MODEL_URI} {TEST_MODEL_PATH}')
        result = parse_response(resp)
        print(f"    patch_set result: status={result['status']}")

        # Give plugin time to process the model
        time.sleep(1)

        # Read back the model path to verify it was set
        print("\n[5] Verifying model path was set via patch_get...")
        resp = send_command(sock, f'patch_get {TEST_INSTANCE} {NAM_MODEL_URI}')
        result = parse_response(resp)
        print(f"    patch_get result: {result['raw']}")

        # Test param_set/param_get with NAM parameters
        print("\n[6] Testing param_set/param_get for NAM parameters...")
        for param in ['input_level', 'output_level']:
            resp = send_command(sock, f'param_set {TEST_INSTANCE} {param} 0.5')
            result = parse_response(resp)
            print(f"    param_set {param}: status={result['status']}")

            resp = send_command(sock, f'param_get {TEST_INSTANCE} {param}')
            result = parse_response(resp)
            print(f"    param_get {param}: status={result['status']}, value={result['value']}")

        # Bypass test
        print("\n[7] Testing bypass...")
        resp = send_command(sock, f"bypass {TEST_INSTANCE} 1")
        result = parse_response(resp)
        print(f"    Bypass ON: status={result['status']}")

        resp = send_command(sock, f"bypass {TEST_INSTANCE} 0")
        result = parse_response(resp)
        print(f"    Bypass OFF: status={result['status']}")

        # Connect command (audio routing test)
        print("\n[8] Testing connect (JACK audio routing)...")
        resp = send_command(sock, f'connect "system:capture_1" "effect_{TEST_INSTANCE}:input"')
        result = parse_response(resp)
        print(f"    connect input: status={result['status']}")

        resp = send_command(sock, f'connect "effect_{TEST_INSTANCE}:output" "system:playback_1"')
        result = parse_response(resp)
        print(f"    connect output: status={result['status']}")

        # Remove plugin
        print("\n[9] Removing plugin instance...")
        resp = send_command(sock, f"remove {TEST_INSTANCE}")
        result = parse_response(resp)
        print(f"    Parsed status: {result['status']}")

        # CPU load test
        print("\n[10] Testing cpu_load...")
        resp = send_command(sock, "cpu_load")
        result = parse_response(resp)
        print(f"    CPU load: {result['raw']}")

    finally:
        sock.close()
        print("\nConnection closed.")


if __name__ == "__main__":
    main()