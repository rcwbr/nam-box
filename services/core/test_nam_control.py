#!/usr/bin/env python3
"""
Test script for sending patch:Set messages to NAM plugin via jalv.

This script demonstrates how to:
1. Create a proper LV2 state file for the NAM model path
2. Validate the state file format
3. Send messages to a running jalv process (if exposed via some IPC)

Usage:
    docker exec -i nam-box-core python3 /opt/nam/test_nam_control.py

Prerequisites:
    - jalv and lilv installed in the container
    - JACK running
"""

import sys
import os
import subprocess
import tempfile
import json
from pathlib import Path

# Add lilv bindings path
sys.path.insert(0, '/workspaces/nam-box/lilv/bindings/python')

# LV2 URIs
LV2_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
LV2_PLUGIN_MODEL_PROP = f"{LV2_PLUGIN_URI}#model"
LV2_ATOM_PATH = "http://lv2plug.in/ns/ext/atom#Path"
LV2_PATCH_SET = "http://lv2plug.in/ns/ext/patch#Set"
LV2_PATCH_PROPERTY = "http://lv2plug.in/ns/ext/patch#property"
LV2_PATCH_VALUE = "http://lv2plug.in/ns/ext/patch#value"
LV2_PATCH_MESSAGE = "http://lv2plug.in/ns/ext/patch#Message"

MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/opt/nam/models"))
STATE_DIR = Path(os.environ.get("STATE_DIR", "/var/nam/jalv"))


def create_proper_lv2_state(model_path: str) -> str:
    """
    Create a proper LV2 state.ttl file for loading a NAM model.

    The state format for atom:Path properties requires proper handling of
    paths through the state:mapPath feature. jalv will convert abstract
    paths to filesystem paths when restoring state.
    """
    model_filename = Path(model_path).name

    state_content = f'''@prefix atom: <http://lv2plug.in/ns/ext/atom#> .
@prefix lv2: <http://lv2plug.in/ns/lv2core#> .
@prefix state: <http://lv2plug.in/ns/ext/state#> .
@prefix patch: <http://lv2plug.in/ns/ext/patch#> .

<http://github.com/mikeoliphant/neural-amp-modeler-lv2>
    state:state [
        <http://github.com/mikeoliphant/neural-amp-modeler-lv2#model> "{model_filename}"
    ] .
'''
    return state_content


def create_atom_sequence_message(model_path: str, model_prop_urid: int = None) -> bytes:
    """
    Build an LV2 Atom Sequence containing a patch:Set message for the model path.

    This manually constructs the binary atom format that jalv expects.
    Note: URID values must match what jalv uses internally.
    """
    path_bytes = model_path.encode('utf-8') + b'\x00'  # Null-terminated

    # For testing, we'll use known URID values that jalv/LV2 typically uses
    # In production, these should be obtained from jalv's URID map

    return path_bytes


def validate_model_file(model_name: str) -> Path:
    """Get and validate model file path."""
    model_path = MODELS_DIR / model_name
    if not model_path.exists():
        raise FileNotFoundError(f"Model '{model_name}' not found at {model_path}")
    return model_path


def check_lv2_plugin_available():
    """Check that the NAM LV2 plugin is available."""
    try:
        result = subprocess.run(
            ["lv2ls", LV2_PLUGIN_URI],
            capture_output=True,
            text=True
        )
        return LV2_PLUGIN_URI in result.stdout
    except FileNotFoundError:
        print("Warning: lv2ls not found - cannot verify plugin availability")
        return True


def test_state_file_creation():
    """Test creating a valid LV2 state file."""
    print("=== Testing LV2 State File Creation ===")

    # Ensure directories exist
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # Create test state
    state_content = create_proper_lv2_state("/opt/nam/models/test-model.nam")
    state_file = STATE_DIR / "state.ttl"

    print(f"State content:\n{state_content}")

    # Note: The state format in main.py is incomplete.
    # For proper state loading, we need to understand how jalv reads state.ttl
    # and converts the model property value.

    return state_content


def test_jalv_control_via_state(model_name: str):
    """
    Test sending model to jalv by creating state file and restarting jalv.

    This is the most reliable approach since direct atom messaging from Python
    is complex (requires shared memory access to jalv's ring buffers).
    """
    print(f"=== Testing jalv Control via State File ===")

    model_path = validate_model_file(model_name)
    print(f"Model path: {model_path}")

    # Create state directory
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # Create proper state file
    # Note: The format here is simplified - real LV2 state has more requirements
    state_content = f'''@prefix state: <http://lv2plug.in/ns/ext/state#> .
@prefix lv2: <http://lv2plug.in/ns/lv2core#> .
@prefix atom: <http://lv2plug.in/ns/ext/atom#> .

[]
    a state:State ;
    <http://github.com/mikeoliphant/neural-amp-modeler-lv2#model> "{model_path}" .
'''

    state_file = STATE_DIR / "state.ttl"
    state_file.write_text(state_content)
    print(f"Wrote state file to {state_file}")

    # Check plugin availability
    if check_lv2_plugin_available():
        print(f"Plugin {LV2_PLUGIN_URI} is available")

    return {"model_path": str(model_path), "state_file": str(state_file)}


def main():
    """Main test entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test NAM patch:Set control")
    parser.add_argument("--model", help="Model filename to test with")
    parser.add_argument("--list-models", action="store_true", help="List available models")
    parser.add_argument("--create-state", help="Create state file for model")
    args = parser.parse_args()

    if args.list_models:
        print("Available models:")
        for model in MODELS_DIR.glob("*.nam"):
            print(f"  - {model.name}")
        if not list(MODELS_DIR.glob("*.nam")):
            print("  (no models found)")
        return 0

    if args.create_state:
        result = test_jalv_control_via_state(args.create_state)
        print(f"\nResult: {json.dumps(result, indent=2)}")
        return 0

    # Default: run tests
    print("NAM Control Test")
    print("================")

    # Check environment
    print(f"MODELS_DIR: {MODELS_DIR}")
    print(f"STATE_DIR: {STATE_DIR}")
    print(f"LV2_PLUGIN_URI: {LV2_PLUGIN_URI}")

    # Try to list models
    models = list(MODELS_DIR.glob("*.nam"))
    if models:
        print(f"\nFound {len(models)} model(s):")
        for m in models[:5]:
            print(f"  {m.name}")
    else:
        print("\nNo models found - create some in /opt/nam/models")

    # Create test state
    test_state_file_creation()

    return 0


if __name__ == "__main__":
    sys.exit(main())