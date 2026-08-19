"""Integration test configuration.

Uses mod-host testcontainer based on ghcr.io/rcwbr/nam-box/effects:local image
with JACK dummy mode for /dev/snd device mocking.

/dev/snd Device Mocking Configuration:
- Uses JACK dummy mode (-d dummy) to provide virtual audio ports
- System ports (system:capture_1/2, system:playback_1/2) are available
- These simulate audio devices from /dev/snd hardware

To build the effects image for container testing:
    docker build -t ghcr.io/rcwbr/nam-box/effects:local ./services/effects
"""

import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

import httpx
import pytest
from pathlib import Path
from testcontainers.compose import DockerCompose

# Path to test LV2 resources directory
_LV2_RESOURCES_PATH = Path(__file__).parent.parent / "resources" / "lv2"

# Add fixtures to the path so pytest can discover fixtures
fixtures_path = Path(__file__).parent.parent / "fixtures"
sys.path.insert(0, str(fixtures_path))


@pytest.fixture(scope="session")
def mod_host_container():
    """Mod-host server fixture using DockerCompose for /dev/snd mocking.

    Uses ghcr.io/rcwbr/nam-box/effects:local container with JACK dummy mode
    for /dev/snd device mocking.

    Returns a dict with:
    - control_port: TCP port for mod-host protocol commands
    - feedback_port: Port for feedback messages
    - lv2_path: Path to LV2 plugins
    """
    compose_file = Path(__file__).parent.parent / "resources" / "docker-compose.mod-host.yaml"

    compose = DockerCompose(
        context=compose_file.parent,
        compose_file_name=compose_file.name,
        wait=False,
    )

    with compose:
        ctrl_port = int(compose.get_service_port("mod-host", 5555))
        fb_port = int(compose.get_service_port("mod-host", 5556))

        # Wait for LV2 export directory to be populated by container entrypoint
        lv2_export_path = _LV2_RESOURCES_PATH
        for _ in range(30):
            if lv2_export_path.exists() and any(lv2_export_path.iterdir()):
                manifest_path = lv2_export_path / "neural_amp_modeler.lv2" / "manifest.ttl"
                if manifest_path.exists():
                    break
            time.sleep(0.5)
        else:
            raise RuntimeError(f"LV2 export directory not populated: {lv2_export_path}")

        # Verify mod-host is actually responding (must connect to BOTH ports)
        # mod-host blocks on feedback port accept() before entering recv() loop
        ctrl_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        fb_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ctrl_sock.settimeout(5)
        fb_sock.settimeout(5)
        # Wait for the server to come up
        time.sleep(3)
        try:
            # Connect to both ports simultaneously (mod-host expects both)
            fb_sock.connect(('localhost', fb_port))
            ctrl_sock.connect(('localhost', ctrl_port))
            ctrl_sock.sendall(b'cpu_load\n')
            # Try multiple times since there might be a race
            for _ in range(5):
                try:
                    response = ctrl_sock.recv(4096)
                    if b'resp' in response:
                        break
                except socket.timeout:
                    time.sleep(0.5)
            else:
                raise RuntimeError(f"mod-host not responding")
        finally:
            ctrl_sock.close()
            fb_sock.close()

        yield {
            "control_port": ctrl_port,
            "feedback_port": fb_port,
            "lv2_path": str(_LV2_RESOURCES_PATH),
        }


@pytest.fixture(scope="session")
def mod_api_server(mod_host_container):
    """Start mod-api server on host, connected to mod-host."""
    mod_host_port = mod_host_container["control_port"]
    api_port = 8001
    lv2_path = str(_LV2_RESOURCES_PATH)

    pedalboard_dir = tempfile.mkdtemp(prefix="pedalboard_test_")

    env = os.environ.copy()
    env["MOD_HOST_HOST"] = "localhost"
    env["MOD_HOST_PORT"] = str(mod_host_port)
    env["MOD_HOST_FB_PORT"] = str(mod_host_container["feedback_port"])
    env["PEDALBOARD_DATA_DIR"] = pedalboard_dir
    env["LV2_PATH"] = lv2_path
    # Set system ports for port discovery (JACK dummy defaults)
    env["SYSTEM_PORTS"] = "system:capture_1,system:capture_2,system:playback_1,system:playback_2"

    src_path = Path(__file__).parent.parent / "src"
    env["PYTHONPATH"] = str(src_path)

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "mod_api.main:app", "--host", "0.0.0.0", "--port", str(api_port)],
        cwd=Path(__file__).parent.parent,
        env=env,
    )

    max_wait = 30
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            httpx.get(f"http://localhost:{api_port}/health", timeout=1)
            break
        except Exception:
            time.sleep(0.5)

    yield f"http://localhost:{api_port}/api/v1"

    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    shutil.rmtree(pedalboard_dir, ignore_errors=True)


__all__ = ["mod_api_server", "mod_host_container"]