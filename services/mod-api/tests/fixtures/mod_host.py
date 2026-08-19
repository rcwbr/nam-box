"""Testcontainers fixtures for mod-host service.

This fixture uses Docker to run mod-host with JACK dummy mode, which simulates
/dev/snd audio device functionality without requiring real audio hardware.

Configuration for /dev/snd Device Mocking:
- Uses JACK dummy mode (-d dummy) to provide virtual audio ports
- System ports (system:capture_1/2, system:playback_1/2) are available
- These would normally come from /dev/snd hardware

To build and use the container:
    docker build -t ghcr.io/rcwbr/nam-box/effects:local ./services/effects

For real /dev/snd hardware (when available on host):
    # In docker-compose.mod-host.yaml, uncomment:
    # devices:
    #   - "/dev/snd:/dev/snd"
"""

import os
import shutil
import subprocess
import tempfile

import pytest
from pathlib import Path

from testcontainers.compose import DockerCompose
from testcontainers.core.wait_strategies import PortWaitStrategy


def _image_exists(image_name: str) -> bool:
    """Check if a Docker image exists locally."""
    result = subprocess.run(
        ["docker", "inspect", image_name],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def _create_minimal_lv2(dest_dir: str) -> None:
    """Create a minimal NAM LV2 plugin directory structure with parameters."""
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


@pytest.fixture(scope="session")
def mod_host_compose():
    """Mod-host server fixture using container with /dev/snd mocking.

    Uses ghcr.io/rcwbr/nam-box/effects:local container with JACK dummy mode
    for /dev/snd device mocking. Falls back to mock TCP server if image unavailable.

    Returns a dict with:
    - control_port: TCP port for mod-host protocol commands
    - feedback_port: Port for feedback messages
    - lv2_path: Path to LV2 plugins
    """
    if _image_exists("ghcr.io/rcwbr/nam-box/effects:local"):
        compose_file = Path(__file__).parent.parent / "resources" / "docker-compose.mod-host.yaml"
        lv2_host_dir = tempfile.mkdtemp(prefix="lv2_host_")

        compose = DockerCompose(
            context=compose_file.parent,
            compose_file_name=compose_file.name,
            wait=True,
        )
        compose.waiting_for({"mod-host": PortWaitStrategy(5555)})

        with compose:
            yield {
                "control_port": compose.get_service_port("mod-host", 5555),
                "feedback_port": compose.get_service_port("mod-host", 5556),
                "lv2_path": os.path.join(lv2_host_dir, "lv2"),
            }
    else:
        # Fall back to mock server - provides /dev/snd mocking without Docker
        from mod_host_mock import MockModHostServer

        server = None
        port = None
        for p in [5555, 5557, 5559, 5561]:
            try:
                server = MockModHostServer(port=p)
                server.start()
                port = p
                break
            except OSError:
                continue

        if not server:
            raise RuntimeError("Could not find available port for mock mod-host server")

        lv2_host_dir = tempfile.mkdtemp(prefix="lv2_fallback_")
        _create_minimal_lv2(lv2_host_dir)

        yield {
            "control_port": port,
            "feedback_port": 5556,
            "lv2_path": lv2_host_dir,
        }

        server.stop()
        shutil.rmtree(lv2_host_dir, ignore_errors=True)