#!/usr/bin/env python3
"""
Test script demonstrating the mod-host socket protocol for:
1. Adding a neural-amp-modeler-lv2 plugin
2. Setting its model file using patch_set
3. Connecting audio ports
4. Setting input/output levels

This uses the TCP socket protocol on port 5555.

Based on source analysis:
- mod-host: EFFECT_PATCH_SET format in mod-host.h:66
- mod-ui: Session.ws_patch_set in session.py:337-341
- mod-ui: Host.patch_set in host.py:2737-2746

See also: /tmp/mod-host-original/README.md for full protocol documentation
        /workspaces/nam-box/test/MOD-HOST-SOCKET-INTERFACE.md for detailed docs
"""

import socket
import sys

# Plugin URI for neural-amp-modeler-lv2
NAM_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
NAM_MODEL_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2#model"


def test_mod_host_socket(port=5555, timeout=2):
    """
    Test connecting to mod-host TCP socket and sending commands.

    mod-host protocol (from README and webserver.py analysis):
    - add <lv2_uri> <instance_number>
    - patch_set <instance> <property_uri> <value>
    - param_set <instance> <param_symbol> <value>
    - connect <origin_port> <destination_port>
    """
    print(f"Testing mod-host socket connection on port {port}...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(('127.0.0.1', port))
        print(f"Connected to mod-host on port {port}")

        # Send help command (works but sends response to stdout in -n mode)
        # Note: help output goes to stdout, not the socket in non-forking mode
        # We use basic commands instead

        # Send cpu_load command to verify connection
        sock.sendall(b"cpu_load\n")
        response = sock.recv(4096).decode('utf-8', errors='ignore')
        print(f"Response to 'cpu_load': {response.strip()}")

        sock.close()
        return True
    except socket.timeout:
        print("Connection timed out (mod-host not running)")
        return False
    except ConnectionRefusedError:
        print("Connection refused - mod-host not running")
        return False
    except Exception as e:
        print(f"Socket error: {e}")
        return False


def generate_patch_set_command(instance, model_path):
    """
    Generate the correct patch_set command for the NAM plugin model parameter.

    Based on mod-host source (mod-host.h:66):
    EFFECT_PATCH_SET "patch_set %i %s %s"

    This is 3 arguments: instance, property_uri, value
    """
    return f"patch_set {instance} {NAM_MODEL_URI} {model_path}"


def generate_add_command(instance, uri=NAM_PLUGIN_URI):
    """Generate the add plugin command."""
    return f'add "{uri}" {instance}'


def verify_protocol_format():
    """Verify and document the correct protocol formats."""
    print("\n" + "="*70)
    print("MOD-HOST PROTOCOL VERIFICATION (from source analysis)")
    print("=" * 70)

    print("\n1. ADD PLUGIN COMMAND:")
    print("   Format: add <lv2_uri> <instance_number>")
    print(f"   Example: add \"{NAM_PLUGIN_URI}\" 0")

    print("\n2. PATCH_SET COMMAND (for setting model file):")
    print("   Format: patch_set <instance> <property_uri> <value>")
    print("   NOTE: mod-host uses ONLY 3 arguments (no vtype)")
    print(f"   Example: patch_set 0 {NAM_MODEL_URI} /opt/nam/models/model.nam")

    print("\n3. PATCH_SET VIA MOD-UI WEBSOCKET (with vtype for feedback):")
    print("   Format: patch_set <inst> <uri> <vtype> <value>")
    print("   vtype 'p' = Path (used for model file)")
    print(f"   Example: patch_set 0 {NAM_MODEL_URI} p /opt/nam/models/model.nam")
    print("\n   NOTE: mod-ui websocket splits into 4 args and adds vtype prefix to value")
    print("   for communication with connected clients. But mod-host accepts 3 args.")

    print("\n4. FULL WORKFLOW:")
    workflow = f"""
    Step 1: Connect to TCP socket
        - TCP Socket: 127.0.0.1:5555 (mod-host control port)

    Step 2: Add the NAM plugin
        Command: add "{NAM_PLUGIN_URI}" 0

    Step 3: Set model file
        Command: patch_set 0 {NAM_MODEL_URI} /opt/nam/models/model.nam

    Step 4: Connect audio ports
        connect "system:capture_1" "effect_0:input"
        connect "effect_0:output" "system:playback_1"

    Step 5: Set levels
        param_set 0/input_level 0.0
        param_set 0/output_level 0.0
    """
    print(workflow)

    print("\n5. ERROR CODES:")
    errors = """
    -1      ERR_INSTANCE_INVALID           Invalid instance number
    -2      ERR_INSTANCE_ALREADY_EXISTS    Instance already exists
    -3      ERR_INSTANCE_NON_EXISTS        Instance does not exist
    -4      ERR_INSTANCE_UNLICENSED        Commercial plugin not licensed
    -101    ERR_LV2_INVALID_URI            Invalid plugin URI
    -102    ERR_LV2_INSTANTIATION          Plugin instantiation failed
    -103    ERR_LV2_INVALID_PARAM_SYMBOL   Invalid parameter symbol
    -104    ERR_LV2_INVALID_PRESET_URI     Invalid preset URI
    -105    ERR_LV2_CANT_LOAD_STATE        Cannot load state
    -201    ERR_JACK_CLIENT_CREATION       JACK client creation error
    -202    ERR_JACK_CLIENT_ACTIVATION     JACK client activation error
    -205    ERR_JACK_PORT_CONNECTION       JACK port connection error
    """
    print(errors)


def test_websocket_protocol_demo():
    """Demonstrate the websocket message format without requiring a connection."""
    print("\n" + "=" * 70)
    print("MESSAGE FORMAT DEMONSTRATION")
    print("=" * 70)

    print("\nMessage format for socket communication:")
    print("  - Messages are newline-terminated: 'command arg1 arg2 ...\\n'")
    print("  - Arguments are space-separated")
    print("  - Responses: 'resp <status> [value]'")

    print("\nExample messages to send via TCP socket:")

    messages = [
        f'add "{NAM_PLUGIN_URI}" 0',
        f'patch_set 0 {NAM_MODEL_URI} /opt/nam/models/silktone_classic.nam',
        f'param_set 0/input_level 0.5',
        f'param_get 0/input_level',
        'bypass 0 1',
        'cpu_load',
    ]

    for msg in messages:
        print(f"\n  Send: '{msg}'")


class ModHostClient:
    """Simple client for mod-host socket protocol."""

    def __init__(self, host='127.0.0.1', port=5555, timeout=5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None

    def connect(self):
        """Connect to mod-host."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))
        return self

    def send(self, cmd):
        """Send a command and return the response."""
        self.sock.sendall((cmd + '\n').encode())
        response = self.sock.recv(4096).decode('utf-8', errors='ignore')
        return response.strip()

    def close(self):
        """Close the connection."""
        if self.sock:
            self.sock.close()


def main():
    print("mod-host Protocol Test for Neural Amp Modeler LV2")
    print("=" * 70)

    verify_protocol_format()
    test_websocket_protocol_demo()

    print("\n" + "=" * 70)
    print("Running actual socket test (will fail if mod-host not running)...")
    test_mod_host_socket()

    print("\n" + "=" * 70)
    print("Python client usage example:")
    print("=" * 70)
    print("""
    client = ModHostClient()
    client.connect()

    # Add plugin
    resp = client.send(f'add "{NAM_PLUGIN_URI}" 0')

    # Set model
    resp = client.send(f'patch_set 0 {NAM_MODEL_URI} /opt/nam/models/model.nam')

    # Set levels
    resp = client.send('param_set 0/input_level 0.5')

    client.close()
    """)


if __name__ == "__main__":
    main()