"""Test fixtures for mod-api service.

Uses mod_host_compose fixture (container or mock) for /dev/snd device mocking.
"""

import os
import signal
import subprocess
import sys
import tempfile
import time

import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def mod_api_server(mod_host_compose):
    """Start mod-api server on host, connected to mod-host.

    Uses MOD_HOST_HOST/PORT from mod_host_compose fixture.
    Uses LV2_PATH from mod_host_compose fixture.
    """
    # Get mod-host host and port from the container's network
    mod_host_port = mod_host_compose["control_port"]
    api_port = 8001  # Use different port for test API server

    lv2_path = mod_host_compose.get("lv2_path", "")
    if not lv2_path:
        # Create minimal LV2 if not provided
        lv2_path = tempfile.mkdtemp(prefix="lv2_fallback_")
        _create_minimal_lv2(lv2_path)

    # Create a temp directory for pedalboard storage
    pedalboard_dir = tempfile.mkdtemp(prefix="pedalboard_test_")

    # Set environment for the API server
    env = os.environ.copy()
    env["MOD_HOST_HOST"] = "localhost"
    env["MOD_HOST_PORT"] = str(mod_host_port)
    env["PEDALBOARD_DATA_DIR"] = pedalboard_dir
    env["LV2_PATH"] = lv2_path
    # Set system ports for port discovery (JACK dummy defaults)
    env["SYSTEM_PORTS"] = "system:capture_1,system:capture_2,system:playback_1,system:playback_2"

    # Add src directory to path for mod_api import
    src_path = Path(__file__).parent.parent.parent / "src"
    env["PYTHONPATH"] = str(src_path)

    # Start the API server using python -m uvicorn
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "mod_api.main:app", "--host", "0.0.0.0", "--port", str(api_port)],
        cwd=Path(__file__).parent.parent.parent,
        env=env,
    )

    # Wait for server to start
    max_wait = 30
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            import httpx
            httpx.get(f"http://localhost:{api_port}/health", timeout=1)
            break
        except Exception:
            time.sleep(0.5)

    yield f"http://localhost:{api_port}/api/v1"

    # Cleanup: stop the server and remove temp directories
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    # Clean up temp directories
    import shutil
    shutil.rmtree(pedalboard_dir, ignore_errors=True)


def _create_minimal_lv2(dest_dir: str) -> None:
    """Create a minimal NAM LV2 plugin directory structure."""
    import os
    os.makedirs(dest_dir, exist_ok=True)

    plugin_dir = os.path.join(dest_dir, "neural_amp_modeler.lv2")
    os.makedirs(plugin_dir, exist_ok=True)

    manifest = '''@prefix lv2: <http://lv2plug.in/ns/lv2core#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<http://github.com/mikeoliphant/neural-amp-modeler-lv2> a lv2:Plugin ;
    lv2:binary <neural_amp_modeler.so> ;
    lv2:symbol <neural_amp_modeler> .
'''
    with open(os.path.join(plugin_dir, "manifest.ttl"), "w") as f:
        f.write(manifest)

    plugin_ttl = '''@prefix lv2: <http://lv2plug.in/ns/lv2core#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix doap: <http://usefulinc.com/ns/doap#> .

<http://github.com/mikeoliphant/neural-amp-modeler-lv2> a lv2:Plugin ;
    doap:name "Neural Amp Modeler" ;
    lv2:port [
        a lv2:InputPort, lv2:AudioPort ;
        lv2:symbol "input" ;
        lv2:name "Input"
    ] ;
    lv2:port [
        a lv2:OutputPort, lv2:AudioPort ;
        lv2:symbol "output" ;
        lv2:name "Output"
    ] ;
    lv2:port [
        a lv2:InputPort, lv2:ControlPort ;
        lv2:symbol "input_level" ;
        lv2:name "Input Level" ;
        lv2:minimum 0.0 ;
        lv2:maximum 1.0 ;
        lv2:default 0.5
    ] ;
    lv2:port [
        a lv2:InputPort, lv2:ControlPort ;
        lv2:symbol "output_level" ;
        lv2:name "Output Level" ;
        lv2:minimum 0.0 ;
        lv2:maximum 1.0 ;
        lv2:default 0.5
    ] .

# Model parameter - defined as a standalone Parameter subject (Path type)
<http://github.com/mikeoliphant/neural-amp-modeler-lv2#model> a lv2:Parameter ;
    rdfs:label "model" ;
    rdfs:range <http://lv2plug.in/ns/lv2core#Path> .
'''
    with open(os.path.join(plugin_dir, "neural_amp_modeler.ttl"), "w") as f:
        f.write(plugin_ttl)