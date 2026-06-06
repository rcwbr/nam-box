#!/usr/bin/env python3
"""
Test sending patch:Set to NAM plugin via jalv.

This demonstrates the limitations and possible approaches for dynamic control.
"""

import os
import subprocess
import ctypes
from pathlib import Path

# LV2 URIs
LV2_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/opt/nam/models"))

def test_urid_mapping():
    """
    Show how to map URIs to URIDs using the lilv C library.

    This is needed to build proper atom messages.
    """
    # Load lilv
    lilv_lib = ctypes.CDLL("liblilv-0.so")

    # Check that we can load the library
    print("Lilv library loaded successfully")

    # Show that we can enumerate plugins
    result = subprocess.run(["lv2ls"], capture_output=True, text=True)
    plugins = result.stdout.strip().split('\n')
    print(f"Found {len(plugins)} plugins, NAM is {'available' if LV2_PLUGIN_URI in plugins else 'NOT available'}")

    return True


def test_jalv_running():
    """Check if jalv is running and accessible."""
    try:
        # Check for jalv process
        result = subprocess.run(["pgrep", "-f", "jalv"], capture_output=True, text=True)
        if result.stdout.strip():
            print(f"jalv is running (PID: {result.stdout.strip()})")
            return True
        print("jalv is NOT running")
        return False
    except Exception as e:
        print(f"Error checking jalv: {e}")
        return False


def show_atom_message_structure():
    """
    Explain the atom message structure needed for patch:Set.

    When jalv runs, it expects messages on the control input port (index 0)
    in the format of an LV2_Atom_Sequence containing LV2_Atom_Object events.
    """
    print("\n=== Atom Message Structure for patch:Set ===")
    print("""
The message structure is:
[LV2_Atom_Sequence_Header]
  time: 0 (frame time)
[LV2_Atom_Object]
  id: 0 (blank)
  otype: patch:Set URID
[LV2_Atom_Property]
  key: patch:property URID
  value: [LV2_Atom_URID] body = model property URID
[LV2_Atom_Property]
  key: patch:value URID
  value: [LV2_Atom_Path] body = path string (null-terminated)

This requires:
1. URID values for patch:Set, patch:property, patch:value, atom:Path, and the model property
2. Proper 64-bit alignment padding
3. Writing to jalv's control port buffer (shared memory access)
""")


def test_env_approach():
    """
    Test using environment variable to pass model to jalv.

    This is the simplest approach but requires jalv to support it.
    """
    print("\n=== Testing Environment Variable Approach ===")

    model_path = MODELS_DIR / "BossWN-feather.nam"
    if model_path.exists():
        print(f"Model exists at {model_path}")

        # The current main.py sets NAM_MODEL_PATH, but jalv doesn't use it
        # This needs to be validated
        print("Note: jalv doesn't natively read NAM_MODEL_PATH env var")
        print("      This would require plugin modification or custom host")
    else:
        print(f"Model not found at {model_path}")


def main():
    """Run all tests."""
    print("NAM patch:Set Control Test")
    print("==========================")

    test_urid_mapping()
    test_jalv_running()
    show_atom_message_structure()
    test_env_approach()

    print("\n=== Summary ===")
    print("""
Sending patch:Set messages to jalv dynamically requires:
1. Shared memory access to jalv's ring buffers (complex)
2. OR a control socket/protocol in jalv (would need to be added)
3. OR using state files properly (main.py needs fixing)
4. OR using a host with Python bindings like Carla

The simplest fix is to correct the state.ttl format in main.py
and ensure jalv loads it properly on startup.
""")


if __name__ == "__main__":
    import sys
    sys.exit(main())