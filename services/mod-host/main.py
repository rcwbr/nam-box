"""
NAM Audio Manager API

Manages JACK, mod-host, and NAM model files via REST API.
"""

import subprocess
import asyncio
import threading
import time
import json
import socket
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel


# Configuration paths
MODELS_DIR = Path("/opt/nam/models")
STATE_DIR = Path("/var/nam")
STATE_FILE = STATE_DIR / "state.json"
LV2_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
MODEL_PROPERTY_URI = LV2_PLUGIN_URI + "#model"  # Full property URI for patch_set
DEFAULT_JACKD_ARGS = ["-d", "alsa", "-r", "44100", "-p", "512"]
MOD_HOST_SOCKET_PORT = 5555
MOD_HOST_INSTANCE_LEFT = 0
MOD_HOST_INSTANCE_RIGHT = 1


class ProcessInfo(BaseModel):
    args: List[str] = []
    running: bool = False
    pid: Optional[int] = None
    exit_code: Optional[int] = None
    returncode: Optional[int] = None


class ModelSelectRequest(BaseModel):
    model: str
    restart_plugin: bool = False


class LogEntry(BaseModel):
    process: str
    lines: List[str]


# State models for persistence
class JackConnection(BaseModel):
    """Represents a JACK audio connection."""
    output_port: str
    input_port: str


class AppState(BaseModel):
    """Persistent application state."""
    current_model: Optional[str] = None
    connections: List[JackConnection] = []
    devices: List[str] = []
    jackd_args: List[str] = []
    stereo: bool = False  # When True, run two NAM effects (L/R); when False, run one (mono)


class ConnectionRequest(BaseModel):
    """Request to create a JACK connection."""
    output_port: str
    input_port: str


class PortList(BaseModel):
    """List of JACK ports."""
    ports: List[str]


class DevicesList(BaseModel):
    """List of selected audio devices."""
    devices: List[str]


class DeviceAction(BaseModel):
    """Request to add/remove a device."""
    device: str


class ArgsAction(BaseModel):
    """Request to add/remove jackd args."""
    args: List[str]


class DeviceInfo(BaseModel):
    """Information about an available audio device."""
    name: str
    card: str
    hw_id: str


class NamAudioManager:
    """Manages JACK, mod-host, and NAM model files."""

    def __init__(self):
        self.jackd_process: Optional[subprocess.Popen] = None
        self.mod_host_process: Optional[subprocess.Popen] = None
        self._jackd_logs: List[str] = []
        self._mod_host_logs: List[str] = []
        self._log_threads: List[threading.Thread] = []
        self.state: Optional[AppState] = None

    # ==================== Model Management ====================

    def list_models(self) -> list[str]:
        """List all NAM model files."""
        return [f.name for f in MODELS_DIR.glob("*.nam") if f.is_file()]

    def read_current_model(self) -> Optional[str]:
        """Read the currently selected model from config file."""
        return self.state.current_model

    def write_current_model(self, model_path: str):
        """Write the current model to config file and update state."""
        self.state.current_model = model_path
        self.save_state()

    def get_model_path(self, model_name: str) -> Path:
        """Get full path for a model file."""
        return MODELS_DIR / model_name

    def validate_model(self, model_name: str) -> Path:
        """Validate that model file exists and return its path."""
        model_path = self.get_model_path(model_name)
        if not model_path.exists():
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
        return model_path

    # ==================== mod-host Socket Communication ====================

    def _send_mod_host_command(self, command: str) -> str:
        """Send a command to mod-host via TCP socket and return the response."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect(("127.0.0.1", MOD_HOST_SOCKET_PORT))
            sock.sendall((command + "\x00").encode())
            response = sock.recv(4096).decode().strip()
            sock.close()
            return response
        except socket.error as e:
            raise HTTPException(status_code=503, detail=f"mod-host socket error: {e}")

    def _get_nam_instances(self) -> List[int]:
        """Get the list of instance numbers based on stereo configuration."""
        return [MOD_HOST_INSTANCE_LEFT, MOD_HOST_INSTANCE_RIGHT] if self.state.stereo else [MOD_HOST_INSTANCE_LEFT]

    def mod_host_add_plugin(self) -> dict:
        """Add the NAM LV2 plugin(s) to mod-host based on stereo configuration."""
        results = []
        for instance in self._get_nam_instances():
            response = self._send_mod_host_command(f'add "{LV2_PLUGIN_URI}" {instance}')
            results.append({"instance": instance, "response": response})
        return {"status": "plugins added", "results": results}

    def mod_host_remove_plugin(self) -> dict:
        """Remove the NAM LV2 plugin(s) from mod-host."""
        results = []
        for instance in self._get_nam_instances():
            response = self._send_mod_host_command(f"remove {instance}")
            results.append({"instance": instance, "response": response})
        return {"status": "plugins removed", "results": results}

    def mod_host_set_model(self, model_path: str) -> dict:
        """Set the NAM model file via patch_set command for all instances."""
        results = []
        for instance in self._get_nam_instances():
            response = self._send_mod_host_command(
                f'patch_set {instance} {MODEL_PROPERTY_URI} "{model_path}"'
            )
            results.append({"instance": instance, "model": model_path, "response": response})
        return {"status": "model set", "results": results}

    # ==================== Log Reader Thread ====================

    def _start_log_reader(self, process: subprocess.Popen, logs_list: List[str], process_name: str) -> None:
        """Start a background thread to read process output."""
        def reader():
            while process.poll() is None:
                try:
                    line = process.stdout.readline()
                    if line:
                        logs_list.append(f"[{process_name}] {line.rstrip()}")
                    line = process.stderr.readline()
                    if line:
                        logs_list.append(f"[{process_name}-err] {line.rstrip()}")
                except Exception:
                    pass
                time.sleep(0.1)

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        self._log_threads.append(thread)

    # ==================== Process Management ====================

    def _get_process_info(self, process: Optional[subprocess.Popen]) -> ProcessInfo:
        """Get detailed info about a process."""
        if process is None:
            return ProcessInfo(args=[], running=False)
        return ProcessInfo(
            args=process.args,
            running=process.poll() is None,
            pid=process.pid,
            exit_code=process.poll(),
            returncode=process.poll(),
        )

    async def start_jackd(self) -> dict:
        """Start the JACK daemon with configured devices and args."""
        if self.jackd_process and self.jackd_process.poll() is None:
            return {"status": "jackd already running"}

        # Build jackd command: devices first as -d args, then jackd_args
        cmd = ["jackd"]
        cmd.extend(self.state.jackd_args)
        for device in self.state.devices:
            cmd.extend(["--device", device])

        self.jackd_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._start_log_reader(self.jackd_process, self._jackd_logs, "jackd")
        await asyncio.sleep(2)
        return {"status": "jackd started", "pid": self.jackd_process.pid, "cmd": " ".join(cmd)}

    async def stop_jackd(self) -> dict:
        """Stop the JACK daemon."""
        if self.jackd_process and self.jackd_process.poll() is None:
            self.jackd_process.terminate()
            try:
                self.jackd_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.jackd_process.kill()
            self.jackd_process = None
        return {"status": "jackd stopped"}

    def start_mod_host(self) -> dict:
        """Start mod-host with the NAM LV2 plugin loaded."""
        if self.mod_host_process and self.mod_host_process.poll() is None:
            return {"status": "mod-host already running"}

        # Start mod-host in non-forking mode with socket
        self.mod_host_process = subprocess.Popen(
            ["mod-host", "-n", "-p", str(MOD_HOST_SOCKET_PORT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._start_log_reader(self.mod_host_process, self._mod_host_logs, "mod-host")

        # Wait for mod-host to be ready
        time.sleep(1)

        # Add the NAM plugin
        add_result = self.mod_host_add_plugin()

        # Load current model if available
        current_model = self.read_current_model()
        if current_model:
            model_result = self.mod_host_set_model(current_model)
            return {"status": "mod-host started", "pid": self.mod_host_process.pid, "model": current_model, "responses": [add_result, model_result]}
        return {"status": "mod-host started", "pid": self.mod_host_process.pid, "response": add_result}

    def stop_mod_host(self) -> dict:
        """Stop mod-host process and remove all plugin instances."""
        if self.mod_host_process and self.mod_host_process.poll() is None:
            # Remove all plugins based on stereo mode
            for instance in self._get_nam_instances():
                try:
                    self._send_mod_host_command(f"remove {instance}")
                except HTTPException:
                    pass
            self.mod_host_process.terminate()
            try:
                self.mod_host_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.mod_host_process.kill()
            self.mod_host_process = None
        return {"status": "mod-host stopped"}

    async def restart_mod_host(self, model_path: Optional[str] = None) -> dict:
        """Restart mod-host with optional model."""
        # Update state with provided model path if set
        if model_path is not None:
            self.write_current_model(model_path)

        self.stop_mod_host()
        await asyncio.sleep(1)
        return self.start_mod_host()

    async def restart_jackd_and_mod_host(self) -> dict:
        """Restart jackd and mod-host to apply device/args changes."""
        state = self.load_state()

        # Stop mod-host first
        self.stop_mod_host()

        # Restart jackd
        await self.stop_jackd()
        await asyncio.sleep(1)
        await self.start_jackd()
        await asyncio.sleep(1)

        # Restore connections
        if state.connections:
            self.restore_state()

        # Restart mod-host with current model
        result = self.start_mod_host()
        return {"jackd": "restarted", "mod-host": result}

    def get_jackd_status(self) -> ProcessInfo:
        """Get detailed JACK daemon status."""
        return self._get_process_info(self.jackd_process)

    def get_mod_host_status(self) -> ProcessInfo:
        """Get detailed mod-host status."""
        return self._get_process_info(self.mod_host_process)

    async def initialize_services(self) -> dict:
        """Start JACK and mod-host on API startup."""
        await self.start_jackd()
        await asyncio.sleep(1)
        result = self.start_mod_host()
        return result

    # ==================== Log Management ====================

    def get_jackd_logs(self, lines: Optional[int] = None) -> LogEntry:
        """Get logs from the JACK daemon process."""
        all_logs = self._jackd_logs.copy()
        if lines is not None and len(all_logs) > lines:
            all_logs = all_logs[-lines:]
        return LogEntry(process="jackd", lines=all_logs)

    def get_mod_host_logs(self, lines: Optional[int] = None) -> LogEntry:
        """Get logs from the mod-host process."""
        all_logs = self._mod_host_logs.copy()
        if lines is not None and len(all_logs) > lines:
            all_logs = all_logs[-lines:]
        return LogEntry(process="mod-host", lines=all_logs)

    # ==================== State Persistence ====================

    def _ensure_state_dirs(self) -> None:
        """Ensure the state directory exists."""
        STATE_DIR.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> AppState:
        """Load persisted state from file, using cache if available."""
        if self.state is not None:
            return self.state

        self._ensure_state_dirs()
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text())
                self.state = AppState(**data)
                # Set defaults if empty
                if not self.state.jackd_args:
                    self.state.jackd_args = DEFAULT_JACKD_ARGS
                return self.state
            except (json.JSONDecodeError, Exception):
                pass
        # Return default state with default jackd args
        self.state = AppState(jackd_args=DEFAULT_JACKD_ARGS)
        return self.state

    def save_state(self) -> None:
        """Save state to file and update cache."""
        self._ensure_state_dirs()
        if self.state is not None:
            STATE_FILE.write_text(json.dumps(self.state.model_dump(), indent=2))

    def _invalidate_state_cache(self) -> None:
        """Invalidate the state cache to force reload from file."""
        self.state = None

    def restore_state(self) -> None:
        """Restore connections from saved state."""
        for conn in self.state.connections:
            self._create_connection(conn.output_port, conn.input_port)

    # ==================== Device Management ====================

    def list_available_devices(self) -> List[DeviceInfo]:
        """List available audio devices with their hw: identifiers.

        Reads /dev/snd/by-id symlinks to get card numbers, then maps to hw:CARD_ID format.
        Returns a list of dict-like structures with name, card, and hw_id.
        """
        devices = []
        devices_path = Path("/dev/snd/by-id")
        if not devices_path.exists():
            return devices

        # Read /proc/asound/cards to get card ID mappings
        cards_info = {}
        cards_path = Path("/proc/asound/cards")
        if cards_path.exists():
            for line in cards_path.read_text().splitlines():
                # Format: " 0 [HDMI            ]: HDA-Intel - HDA ATI HDMI"
                parts = line.split(" [", 1)
                if len(parts) == 2:
                    card_num = parts[0].strip()
                    card_id = parts[1].split("]", 1)[0].strip()
                    cards_info[card_num] = card_id

        for device_link in devices_path.iterdir():
            if device_link.is_symlink():
                target = str(device_link.readlink())
                # target format: ../controlC0
                if target.startswith("../controlC"):
                    card_num = target.replace("../controlC", "")
                    card_id = cards_info.get(card_num, card_num)
                    devices.append(DeviceInfo(
                        name=device_link.name,
                        card=card_num,
                        hw_id=f"hw:{card_id}"
                    ))
        return devices

    def get_selected_devices(self) -> DevicesList:
        """Get the list of selected devices from state."""
        return DevicesList(devices=self.state.devices)

    def add_device(self, device: str) -> dict:
        """Add a device to the selected devices list."""
        if device not in self.state.devices:
            self.state.devices.append(device)
            self.save_state()
        return {"status": "device added", "device": device}

    def remove_device(self, device: str) -> dict:
        """Remove a device from the selected devices list."""
        self.state.devices = [d for d in self.state.devices if d != device]
        self.save_state()
        return {"status": "device removed", "device": device}

    def set_devices(self, devices: List[str]) -> dict:
        """Set the complete list of devices."""
        self.state.devices = devices
        self.save_state()
        return {"status": "devices updated", "devices": devices}

    def add_jackd_args(self, args: List[str]) -> dict:
        """Add jackd arguments to the state."""
        self.state.jackd_args.extend([a for a in args if a not in self.state.jackd_args])
        self.save_state()
        return {"status": "args added", "args": args}

    def remove_jackd_args(self, args: List[str]) -> dict:
        """Remove jackd arguments from the state."""
        self.state.jackd_args = [a for a in self.state.jackd_args if a not in args]
        self.save_state()
        return {"status": "args removed", "args": args}

    def set_jackd_args(self, args: List[str]) -> dict:
        """Set the complete list of jackd arguments."""
        self.state.jackd_args = args
        self.save_state()
        return {"status": "args updated", "args": args}

    # ==================== JACK Connection Management ====================

    def _run_jack_connect(self, output_port: str, input_port: str) -> subprocess.CompletedProcess:
        """Run jack_connect command and return result."""
        return subprocess.run(
            ["jack_connect", output_port, input_port],
            capture_output=True,
            text=True,
        )

    def _create_connection(self, output_port: str, input_port: str) -> bool:
        """Create a JACK connection. Returns True if successful."""
        result = self._run_jack_connect(output_port, input_port)
        return result.returncode == 0

    def list_connections(self) -> List[JackConnection]:
        """List all current JACK connections."""
        return self.state.connections

    def list_ports(self) -> PortList:
        """List all available JACK ports."""
        result = subprocess.run(
            ["jack_lsp"],
            capture_output=True,
            text=True,
        )
        ports = []
        if result.returncode == 0:
            ports = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        return PortList(ports=ports)

    def create_connection(self, output_port: str, input_port: str) -> dict:
        """Create a JACK connection."""
        success = self._create_connection(output_port, input_port)
        if success:
            # Update state
            conn = JackConnection(output_port=output_port, input_port=input_port)
            if conn not in self.state.connections:
                self.state.connections.append(conn)
                self.save_state()
            return {"status": "connection created", "output_port": output_port, "input_port": input_port}
        return {"status": "connection failed", "output_port": output_port, "input_port": input_port}

    def remove_connection(self, output_port: str, input_port: str) -> dict:
        """Remove a JACK connection."""
        result = subprocess.run(
            ["jack_disconnect", output_port, input_port],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            # Update state
            self.state.connections = [
                c for c in self.state.connections
                if not (c.output_port == output_port and c.input_port == input_port)
            ]
            self.save_state()
            return {"status": "connection removed", "output_port": output_port, "input_port": input_port}
        return {"status": "disconnection failed", "output_port": output_port, "input_port": input_port}


class StatusResponse(BaseModel):
    jackd: ProcessInfo
    mod_host: ProcessInfo


# Create manager instance
manager = NamAudioManager()

# Create FastAPI app
app = FastAPI(title="NAM Audio Manager", debug=False)


@app.on_event("startup")
async def startup_event():
    """Initialize services when API starts."""
    # Load persisted state
    state = manager.load_state()

    # Start services
    await manager.start_jackd()
    await asyncio.sleep(1)

    # Restore connections after JACK is up
    if state.connections:
        manager.restore_state()

    # Start mod-host and load NAM plugin (non-blocking since mod-host uses socket)
    # mod-host must be running for socket commands to work
    try:
        manager.start_mod_host()
    except Exception as e:
        # Log but don't fail - mod-host can be started manually later
        pass


@app.get("/status", response_model=StatusResponse)
async def status():
    """Get detailed process status including PID and exit codes."""
    return StatusResponse(
        jackd=manager.get_jackd_status(),
        mod_host=manager.get_mod_host_status()
    )


@app.get("/jackd", response_model=ProcessInfo)
async def jackd_status():
    """Get detailed JACK daemon status."""
    return manager.get_jackd_status()


@app.get("/mod-host", response_model=ProcessInfo)
async def mod_host_status():
    """Get detailed mod-host status."""
    return manager.get_mod_host_status()


@app.post("/jackd/start")
async def jackd_start():
    """Start JACK daemon."""
    return await manager.start_jackd()


@app.post("/jackd/stop")
async def jackd_stop():
    """Stop JACK daemon."""
    return await manager.stop_jackd()


@app.post("/jackd/restart")
async def jackd_restart():
    """Restart JACK daemon and restore connections."""
    await manager.stop_jackd()
    await asyncio.sleep(1)
    await manager.start_jackd()
    manager.restore_state()
    return {"status": "jackd restarted"}


@app.post("/mod-host/start")
async def mod_host_start():
    """Start mod-host and load NAM plugin."""
    return manager.start_mod_host()


@app.post("/mod-host/stop")
async def mod_host_stop():
    """Stop mod-host."""
    return manager.stop_mod_host()


@app.post("/mod-host/restart")
async def mod_host_restart(model: Optional[str] = None):
    """Restart mod-host with optional model."""
    return await manager.restart_mod_host(model)


# ==================== Stereo Configuration Endpoint ====================

@app.get("/stereo")
async def get_stereo():
    """Get the current stereo mode configuration."""
    return {"stereo": manager.state.stereo, "instances": manager._get_nam_instances()}


@app.post("/stereo")
async def set_stereo(stereo: bool = Query(default=False)):
    """Set stereo mode (true=2 effects, false=1 effect). Restarts services to apply."""
    manager.state.stereo = stereo
    manager.save_state()
    result = await manager.restart_jackd_and_mod_host()
    return result


@app.get("/models", response_model=list[str])
async def list_models_endpoint():
    """List all available NAM models."""
    return manager.list_models()


@app.get("/models/current")
async def get_current_model():
    """Get the currently selected model."""
    model = manager.read_current_model()
    if model:
        return {"model": Path(model).name, "path": model}
    return {"model": None, "path": None}


@app.post("/models/select")
async def select_model(request: ModelSelectRequest):
    """Select a model and optionally restart mod-host."""
    model_path = manager.validate_model(request.model)
    manager.write_current_model(str(model_path))

    if request.restart_plugin:
        return await manager.restart_mod_host(str(model_path))

    # If mod-host is running, just set the model without restart
    if manager.mod_host_process and manager.mod_host_process.poll() is None:
        try:
            manager.mod_host_set_model(str(model_path))
        except HTTPException as e:
            return {"status": "model selected but mod-host update failed", "model": request.model, "error": str(e)}
    return {"status": "model selected", "model": request.model}


@app.post("/models/upload")
async def upload_model(file: UploadFile = File(...)):
    """Upload a new NAM model file, select it by default, and restart mod-host."""
    if not file.filename.endswith(".nam"):
        raise HTTPException(status_code=400, detail="File must be a .nam file")

    model_path = MODELS_DIR / file.filename
    content = await file.read()
    model_path.write_bytes(content)

    manager.write_current_model(str(model_path))

    result = await manager.restart_mod_host(str(model_path))
    return {**result, "uploaded": file.filename}


@app.delete("/models/{model_name}")
async def delete_model(model_name: str):
    """Delete a NAM model file."""
    model_path = manager.validate_model(model_name)

    # Check if this is the current model - we should not delete it
    current = manager.read_current_model()
    if current == str(model_path):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete current model. Select another model first."
        )

    model_path.unlink()
    return {"status": "model deleted", "model": model_name}


@app.get("/models/{model_name}")
async def download_model(model_name: str):
    """Download a NAM model file."""
    model_path = manager.validate_model(model_name)
    return FileResponse(
        path=str(model_path),
        media_type="application/octet-stream",
        filename=model_name
    )


@app.get("/logs/jackd", response_model=LogEntry)
async def get_jackd_logs(lines: Optional[int] = None):
    """Get logs from the JACK daemon process."""
    return manager.get_jackd_logs(lines)


@app.get("/logs/mod-host", response_model=LogEntry)
async def get_mod_host_logs(lines: Optional[int] = None):
    """Get logs from the mod-host process."""
    return manager.get_mod_host_logs(lines)


# ==================== Connection Endpoints ====================

@app.get("/connections", response_model=List[JackConnection])
async def list_connections_endpoint():
    """List all current JACK connections."""
    return manager.list_connections()


@app.post("/connection")
async def create_connection_endpoint(request: ConnectionRequest):
    """Create a JACK connection."""
    return manager.create_connection(request.output_port, request.input_port)


@app.delete("/connection")
async def remove_connection_endpoint(request: ConnectionRequest):
    """Remove a JACK connection."""
    return manager.remove_connection(request.output_port, request.input_port)


@app.get("/state", response_model=AppState)
async def get_state():
    """Get the current persisted application state."""
    return manager.state


@app.get("/ports", response_model=PortList)
async def list_ports_endpoint():
    """List all available JACK ports."""
    return manager.list_ports()


# ==================== Device Endpoints ====================

@app.get("/devices", response_model=List[DeviceInfo])
async def list_available_devices():
    """List available audio devices from /dev/snd/by-id with hw: identifiers."""
    return manager.list_available_devices()


@app.get("/devices/selected", response_model=DevicesList)
async def get_selected_devices():
    """Get the selected devices from state."""
    return manager.get_selected_devices()


@app.post("/devices")
async def add_device_endpoint(request: DeviceAction):
    """Add a device to the selected list and restart services."""
    result = manager.add_device(request.device)
    # Restart services to apply device change
    await manager.restart_jackd_and_mod_host()
    return result


@app.delete("/devices")
async def remove_device_endpoint(device: str):
    """Remove a device from the selected list and restart services."""
    result = manager.remove_device(device)
    await manager.restart_jackd_and_mod_host()
    return result


@app.put("/devices")
async def set_devices_endpoint(request: DevicesList):
    """Set the complete list of selected devices and restart services."""
    result = manager.set_devices(request.devices)
    await manager.restart_jackd_and_mod_host()
    return result


# ==================== jackd Args Endpoints ====================

@app.get("/args/jackd", response_model=List[str])
async def get_jackd_args():
    """Get the current jackd arguments from state."""
    return manager.state.jackd_args


@app.post("/args/jackd")
async def add_jackd_args_endpoint(request: ArgsAction):
    """Add jackd arguments to the state."""
    result = manager.add_jackd_args(request.args)
    await manager.restart_jackd_and_mod_host()
    return result


@app.delete("/args/jackd")
async def remove_jackd_args_endpoint(args: List[str] = Query(default=[])):
    """Remove jackd arguments from the state."""
    return manager.remove_jackd_args(args)


@app.put("/args/jackd")
async def set_jackd_args_endpoint(request: ArgsAction):
    """Set the complete list of jackd arguments and restart services."""
    result = manager.set_jackd_args(request.args)
    await manager.restart_jackd_and_mod_host()
    return result