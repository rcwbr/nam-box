#!/usr/bin/env python3
"""
Comprehensive test script for mod-host socket protocol.

Tests all documented commands and their responses.
"""

import socket
import time
import sys
import json

# Plugin URI for neural-amp-modeler-lv2
NAM_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
NAM_MODEL_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2#model"

# Instance we'll use for testing
TEST_INSTANCE = 0


def connect_to_mod_host(host='effects', port=5555, timeout=5):
    """Connect to mod-host socket."""
    print(f"Connecting to mod-host at {host}:{port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((host, port))
    print("Connected!")
    return sock


def send_command(sock, cmd, expect_response=True):
    """Send a command and receive response."""
    sock.sendall((cmd + '\n').encode())
    if expect_response:
        response = sock.recv(4096).decode('utf-8', errors='ignore')
        return response.strip()
    return None


def parse_response(response):
    """Parse mod-host response into status and optional value."""
    if response.startswith('resp '):
        parts = response.split(None, 2)
        status = int(parts[1])
        value = parts[2] if len(parts) > 2 else None
        return {'status': status, 'value': value, 'raw': response}
    return {'status': None, 'value': None, 'raw': response}


def main():
    results = []

    print("=" * 70)
    print("MOD-HOST COMPREHENSIVE COMMAND TEST")
    print("=" * 70)

    sock = connect_to_mod_host()

    try:
        # Help command
        print("\n[T] Testing 'help' command...")
        resp = send_command(sock, "help")
        parsed = parse_response(resp)
        print(f"Response status: {parsed['status']}")
        results.append(('help', parsed))

        # Add command
        print("\n[T] Testing 'add' command...")
        resp = send_command(sock, f'add "{NAM_PLUGIN_URI}" {TEST_INSTANCE}')
        parsed = parse_response(resp)
        print(f"Response: {parsed['raw']}")
        results.append(('add', parsed))

        if parsed['status'] < 0:
            print("Failed to add plugin, exiting tests.")
            return

        # Wait for plugin to load
        time.sleep(1)

        # Instances command (if available)
        print("\n[T] Checking for 'instances' command...")
        try:
            resp = send_command(sock, "instances")
            parsed = parse_response(resp)
            print(f"Response: {parsed['raw']}")
            results.append(('instances', parsed))
        except Exception as e:
            print(f"'instances' not available or error: {e}")

        # param_list command
        print("\n[T] Testing 'param_list' command...")
        try:
            resp = send_command(sock, f"param_list {TEST_INSTANCE}")
            print(f"Response: {resp}")
            results.append(('param_list', {'raw': resp}))
        except Exception as e:
            print(f"'param_list' error: {e}")

        # Get engine info
        print("\n[T] Testing 'info' command...")
        try:
            resp = send_command(sock, f"info {TEST_INSTANCE}")
            print(f"Response: {resp[:500]}...")
            results.append(('info', {'raw': resp}))
        except Exception as e:
            print(f"'info' error: {e}")

        # patch_get model
        print("\n[T] Testing 'patch_get' for model URI...")
        resp = send_command(sock, f'patch_get {TEST_INSTANCE} {NAM_MODEL_URI}')
        parsed = parse_response(resp)
        print(f"Response: {parsed['raw']}")
        results.append(('patch_get_model', parsed))

        # patch_set with nonexistent file (will likely fail)
        print("\n[T] Testing 'patch_set' with nonexistent model file...")
        resp = send_command(sock, f'patch_set {TEST_INSTANCE} {NAM_MODEL_URI} /opt/nam/models/nonexistent.nam')
        parsed = parse_response(resp)
        print(f"Response: {parsed['raw']}")
        results.append(('patch_set_model_fail', parsed))

        # Test parameter set/get if we know the param names
        print("\n[T] Testing 'param_set' and 'param_get'...")
        # Try common NAM parameter names
        for param in ['input_level', 'output_level', 'gain']:
            resp = send_command(sock, f'param_set {TEST_INSTANCE}/{param} 0.5')
            parsed = parse_response(resp)
            print(f"  param_set {param}: {parsed['raw']}")
            results.append((f'param_set_{param}', parsed))

            resp = send_command(sock, f'param_get {TEST_INSTANCE}/{param}')
            parsed = parse_response(resp)
            print(f"  param_get {param}: {parsed['raw']}")
            results.append((f'param_get_{param}', parsed))

        # Bypass test
        print("\n[T] Testing 'bypass' command...")
        resp = send_command(sock, f"bypass {TEST_INSTANCE} 1")
        parsed = parse_response(resp)
        print(f"Response: {parsed['raw']}")
        results.append(('bypass_on', parsed))

        resp = send_command(sock, f"bypass {TEST_INSTANCE} 0")
        parsed = parse_response(resp)
        print(f"Response: {parsed['raw']}")
        results.append(('bypass_off', parsed))

        # Remove plugin
        print("\n[T] Testing 'remove' command...")
        resp = send_command(sock, f"remove {TEST_INSTANCE}")
        parsed = parse_response(resp)
        print(f"Response: {parsed['raw']}")
        results.append(('remove', parsed))

        # CPU load test
        print("\n[T] Testing 'cpu_load' command...")
        resp = send_command(sock, "cpu_load")
        parsed = parse_response(resp)
        print(f"Response: {parsed['raw']}")
        results.append(('cpu_load', parsed))

        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY OF RESULTS")
        print("=" * 70)
        for name, result in results:
            status = result.get('status', 'N/A')
            print(f"  {name}: status={status}")

    finally:
        sock.close()
        print("\nConnection closed.")

        # Save results
        with open('/scripts/test_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print("Results saved to /scripts/test_results.json")


if __name__ == "__main__":
    main()