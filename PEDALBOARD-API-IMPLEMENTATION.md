# Pedalboard API Implementation Design

A FastAPI service implementation design for the pedalboard management API, providing REST endpoints for managing pedalboards, effect instances, ports, connections, and parameters on the MOD Audio platform.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Service                           │
├─────────────────────────────────────────────────────────────────┤
│  REST API Endpoints (PEDALBOARD-API.md)                          │
│  ↓                                                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   API Layer                            │    │
│  │  - Response models for JSON serialization               │    │
│  │  - Request validation                                   │    │
│  │  - Error handling                                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ↓                                                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Service Layer                         │    │
│  │  - Business logic for pedalboard operations              │    │
│  │  - State management (current pedalboard tracking)        │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ↓                                                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Data Layer                             │    │
│  │  - Pedalboard model (file I/O)                          │    │
│  │  - In-memory state management                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ↓                                                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Mod-Host Client                         │    │
│  │  - TCP socket communication (port 5555)                │    │
│  │  - Command translation to mod-host protocol              │    │
│  │  - Response parsing                                       │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                   ┌───────────────────────┐
                   │   mod-host (TCP)      │
                   │   Port 5555           │
                   └───────────────────────┘
```

## Core Components

### 1. Mod-Host Socket Client

The client handles low-level TCP socket communication with mod-host, abstracting the protocol details.

```python
# src/mod_host_client.py
import socket
from typing import Optional, Tuple

class ModHostClient:
    """TCP socket client for mod-host protocol communication."""

    # Error codes from MOD-HOST-SOCKET-INTERFACE.md
    ERR_INSTANCE_INVALID = -1
    ERR_INSTANCE_ALREADY_EXISTS = -2
    ERR_INSTANCE_NON_EXISTS = -3
    ERR_INSTANCE_UNLICENSED = -4
    ERR_LV2_INVALID_URI = -101
    ERR_LV2_INSTANTIATION = -102
    ERR_LV2_INVALID_PARAM_SYMBOL = -103
    ERR_LV2_INVALID_PRESET_URI = -104
    ERR_LV2_CANT_LOAD_STATE = -105
    ERR_JACK_CLIENT_CREATION = -201
    ERR_JACK_CLIENT_ACTIVATION = -202
    ERR_JACK_PORT_CONNECTION = -205
    ERR_JACK_PORT_DISCONNECTION = -206
    ERR_JACK_VALUE_OUT_OF_RANGE = -207
    ERR_ASSIGNMENT_ALREADY_EXISTS = -301
    ERR_ASSIGNMENT_INVALID_OP = -302
    ERR_ASSIGNMENT_LIST_FULL = -303
    ERR_ASSIGNMENT_FAILED = -304
    ERR_CONTROL_CHAIN_UNAVAILABLE = -401
    ERR_LINK_UNAVAILABLE = -402
    ERR_HMI_UNAVAILABLE = -403
    ERR_EXTERNAL_UI_UNAVAILABLE = -404
    ERR_MEMORY_ALLOCATION = -901
    ERR_INVALID_OPERATION = -902

    def __init__(self, host: str = '127.0.0.1', port: int = 5555, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None

    def connect(self) -> None:
        """Establish TCP connection to mod-host."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        self.socket.connect((self.host, self.port))

    def send_command(self, command: str) -> Tuple[int, Optional[str]]:
        """
        Send a command and return parsed response.

        Returns:
            Tuple of (status_code, optional_value)
            status_code >= 0 indicates success
            status_code < 0 indicates error (see ERR_* constants)
        """
        if not self.socket:
            raise RuntimeError("Not connected to mod-host")

        self.socket.sendall((command + '\n').encode())
        response = self.socket.recv(4096).decode('utf-8', errors='ignore')

        # Parse response format: "resp <status> [value]"
        parts = response.strip().split()
        if parts[0] != 'resp':
            raise RuntimeError(f"Unexpected response: {response}")

        status = int(parts[1])
        value = parts[2] if len(parts) > 2 else None

        return status, value

    def add_plugin(self, uri: str, instance: int) -> int:
        """Add an LV2 plugin. Returns status code."""
        status, _ = self.send_command(f'add "{uri}" {instance}')
        return status

    def remove_plugin(self, instance: int) -> int:
        """Remove an LV2 plugin. Returns status code."""
        status, _ = self.send_command(f'remove {instance}')
        return status

    def connect_ports(self, source: str, destination: str) -> int:
        """Connect two JACK ports. Returns status code."""
        status, _ = self.send_command(f'connect "{source}" "{destination}"')
        return status

    def disconnect_ports(self, source: str, destination: str) -> int:
        """Disconnect two JACK ports. Returns status code."""
        status, _ = self.send_command(f'disconnect "{source}" "{destination}"')
        return status

    def param_set(self, instance: int, symbol: str, value: float) -> int:
        """Set a control port value. Returns status code."""
        status, _ = self.send_command(f'param_set {instance} {symbol} {value}')
        return status

    def param_get(self, instance: int, symbol: str) -> Tuple[int, float]:
        """Get a control port value. Returns (status, value)."""
        status, value = self.send_command(f'param_get {instance} {symbol}')
        return status, float(value) if value else 0.0

    def patch_set(self, instance: int, property_uri: str, value: str) -> int:
        """Set a property value via LV2 Patch protocol. Returns status code."""
        status, _ = self.send_command(f'patch_set {instance} {property_uri} {value}')
        return status

    def bypass(self, instance: int, enabled: bool) -> int:
        """Toggle bypass. Returns status code."""
        status, _ = self.send_command(f'bypass {instance} {1 if enabled else 0}')
        return status

    def close(self) -> None:
        """Close the socket connection."""
        if self.socket:
            self.socket.close()
            self.socket = None
```

### 2. Data Models

Pydantic models defining the data structures for pedalboards, effects, and connections.

```python
# src/models/pedalboard.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class PortType(str, Enum):
    INPUT = "input"
    OUTPUT = "output"
    MIDI_IN = "midi_in"
    MIDI_OUT = "midi_out"

class ParameterType(str, Enum):
    NUMBER = "number"
    FILENAME = "filename"
    STRING = "string"

class Parameter(BaseModel):
    name: str
    type: ParameterType
    value: float | str
    min: Optional[float] = None
    max: Optional[float] = None
    default: float | str

class Port(BaseModel):
    id: str
    name: str
    type: PortType
    owner_type: str  # "system" or "effect"
    effect_instance_id: Optional[int] = None

class EffectInstance(BaseModel):
    id: int
    uri: str
    name: Optional[str] = None
    ports: List[str]
    parameters: Dict[str, Any]

class Connection(BaseModel):
    id: int
    input_port_id: str
    output_port_id: str

class Pedalboard(BaseModel):
    id: int
    name: str
    file: str
    is_current: bool = False
    effects: List[EffectInstance] = []
    connections: List[Connection] = []
    parameters: List[Parameter] = []

class EffectInfo(BaseModel):
    uri: str
    name: str
    ports: List[Dict[str, str]]  # [{"name": "input", "type": "input"}]
    parameters: List[Parameter]
```

### 3. Persistence Layer

Pedalboard state is persisted to JSON files in a designated directory.

```python
# src/storage/pedalboard_store.py
import json
import os
from pathlib import Path
from typing import List, Optional
from models.pedalboard import Pedalboard, EffectInstance, Connection, Parameter

class PedalboardStore:
    """Manages pedalboard persistence to disk."""

    def __init__(self, data_dir: str = "/var/mod/pedalboards"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._next_id = self._calculate_next_id()
        self._pedalboards: Dict[int, Pedalboard] = {}
        self._current_id: Optional[int] = None

    def _calculate_next_id(self) -> int:
        """Calculate the next available pedalboard ID."""
        existing = list(self.data_dir.glob("*.json"))
        if not existing:
            return 1
        # Extract IDs from filenames or stored data
        max_id = 0
        for f in existing:
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    max_id = max(max_id, data.get('id', 0))
            except (json.JSONDecodeError, KeyError):
                continue
        return max_id + 1

    def load_all(self) -> List[Pedalboard]:
        """Load all pedalboards from disk."""
        pedalboards = []
        for file in self.data_dir.glob("*.json"):
            try:
                with open(file) as f:
                    data = json.load(f)
                    pedalboards.append(Pedalboard(**data))
            except (json.JSONDecodeError, KeyError):
                continue
        self._pedalboards = {pb.id: pb for pb in pedalboards}
        return pedalboards

    def get(self, pedalboard_id: int) -> Optional[Pedalboard]:
        """Get a specific pedalboard by ID."""
        return self._pedalboards.get(pedalboard_id)

    def create(self, name: str, duplicate_from_id: Optional[int] = None) -> Pedalboard:
        """Create a new pedalboard, optionally duplicating another."""
        # Determine filename from name
        filename = f"{name.lower().replace(' ', '-')}.json"
        filepath = self.data_dir / filename

        # Create pedalboard
        if duplicate_from_id and duplicate_from_id in self._pedalboards:
            source = self._pedalboards[duplicate_from_id]
            new_pedalboard = Pedalboard(
                id=self._next_id,
                name=name,
                file=filename,
                effects=source.effects.copy(),
                connections=source.connections.copy()
            )
        else:
            new_pedalboard = Pedalboard(
                id=self._next_id,
                name=name,
                file=filename
            )

        self._next_id += 1
        self._pedalboards[new_pedalboard.id] = new_pedalboard
        self._save_pedalboard(new_pedalboard)
        return new_pedalboard

    def delete(self, pedalboard_id: int) -> bool:
        """Delete a pedalboard by ID."""
        if pedalboard_id not in self._pedalboards:
            return False

        pb = self._pedalboards[pedalboard_id]
        filepath = self.data_dir / pb.file

        try:
            os.remove(filepath)
        except FileNotFoundError:
            pass

        del self._pedalboards[pedalboard_id]
        return True

    def rename(self, pedalboard_id: int, new_name: str) -> Optional[Pedalboard]:
        """Rename a pedalboard."""
        pb = self._pedalboards.get(pedalboard_id)
        if not pb:
            return None

        pb.name = new_name
        pb.file = f"{new_name.lower().replace(' ', '-')}.json"
        self._save_pedalboard(pb)
        return pb

    def _save_pedalboard(self, pedalboard: Pedalboard) -> None:
        """Save a pedalboard to disk."""
        filepath = self.data_dir / pedalboard.file
        with open(filepath, 'w') as f:
            json.dump(pedalboard.model_dump(), f, indent=2)
```

### 4. Effects Registry

Manages the catalog of available LV2 effects.

```python
# src/effects/registry.py
from models.pedalboard import EffectInfo
from typing import Dict, List, Optional
from mod_host_client import ModHostClient

class EffectsRegistry:
    """Registry of available LV2 effects."""

    def __init__(self, client: ModHostClient):
        self._client = client
        self._effects: Dict[str, EffectInfo] = {}

    def discover(self) -> List[EffectInfo]:
        """
        Discover available LV2 effects.

        Note: This would ideally query mod-host for available plugins,
        but mod-host doesn't have a direct 'list all plugins' command.
        Instead, we maintain a predefined list of supported effects,
        or scan the LV2_PATH for plugin manifests.
        """
        # For NAM-box, we primarily support neural-amp-modeler-lv2
        self._effects = {
            "http://github.com/mikeoliphant/neural-amp-modeler-lv2": EffectInfo(
                uri="http://github.com/mikeoliphant/neural-amp-modeler-lv2",
                name="Neural Amp Modeler",
                ports=[
                    {"name": "input", "type": "input"},
                    {"name": "output", "type": "output"}
                ],
                parameters=[
                    Parameter(
                        name="model",
                        type=ParameterType.FILENAME,
                        value="/opt/nam/models/default.nam",
                        default=""
                    ),
                    Parameter(
                        name="input_level",
                        type=ParameterType.NUMBER,
                        value=0.5,
                        min=0.0,
                        max=1.0,
                        default=0.5
                    ),
                    Parameter(
                        name="output_level",
                        type=ParameterType.NUMBER,
                        value=0.5,
                        min=0.0,
                        max=1.0,
                        default=0.5
                    )
                ]
            )
        }
        return list(self._effects.values())

    def get(self, uri: str) -> Optional[EffectInfo]:
        """Get effect info by URI."""
        return self._effects.get(uri)

    def get_all(self) -> List[EffectInfo]:
        """Get all available effects."""
        return list(self._effects.values())
```

### 5. REST API Endpoints

FastAPI endpoint implementations following the PEDALBOARD-API.md specification.

```python
# src/api/routes/pedalboards.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from models.pedalboard import Pedalboard, EffectInstance, Connection
from storage.pedalboard_store import PedalboardStore
from effects.registry import EffectsRegistry

router = APIRouter(prefix="/api/v1/pedalboards")

def get_pedalboard_store() -> PedalboardStore:
    """Dependency injection for pedalboard store."""
    ...

def get_effects_registry() -> EffectsRegistry:
    """Dependency injection for effects registry."""
    ...

@router.get("")
async def list_pedalboards(store: PedalboardStore = Depends(get_pedalboard_store)):
    """GET /api/v1/pedalboards - List all pedalboards."""
    pedalboards = store.load_all()
    return {
        "pedalboards": [
            {
                "id": pb.id,
                "name": pb.name,
                "file": pb.file,
                "is_current": pb.id == store._current_id
            }
            for pb in pedalboards
        ]
    }

@router.get("/current")
async def get_current_pedalboard(store: PedalboardStore = Depends(get_pedalboard_store)):
    """GET /api/v1/pedalboards/current - Get current pedalboard."""
    if not store._current_id or store._current_id not in store._pedalboards:
        return JSONResponse(status_code=204)

    pb = store._pedalboards[store._current_id]
    return {
        "id": pb.id,
        "name": pb.name,
        "effects": pb.effects,
        "connections": pb.connections,
        "parameters": pb.parameters
    }

@router.get("/{pedalboard_id}")
async def get_pedalboard(pedalboard_id: int, store: PedalboardStore = Depends(get_pedalboard_store)):
    """GET /api/v1/pedalboards/{id} - Get specific pedalboard."""
    pb = store.get(pedalboard_id)
    if not pb:
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}
        )
    return pb

@router.post("")
async def create_pedalboard(
    request: dict,
    store: PedalboardStore = Depends(get_pedalboard_store)
):
    """POST /api/v1/pedalboards - Create new pedalboard."""
    name = request.get("name")
    if not name:
        raise HTTPException(
            status_code=400,
            detail={"error": "Name required", "code": "INVALID_REQUEST"}
        )

    duplicate_current = request.get("duplicate_current", False)
    source_id = store._current_id if duplicate_current else None

    pedalboard = store.create(name, duplicate_from_id=source_id)
    store._current_id = pedalboard.id
    return JSONResponse(status_code=201, content=pedalboard.model_dump())

@router.delete("/{pedalboard_id}")
async def delete_pedalboard(
    pedalboard_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store)
):
    """DELETE /api/v1/pedalboards/{id} - Delete pedalboard."""
    if not store.get(pedalboard_id):
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}
        )

    if store._current_id == pedalboard_id:
        store._current_id = None

    store.delete(pedalboard_id)
    return JSONResponse(status_code=204)

@router.put("/{pedalboard_id}/select")
async def select_pedalboard(
    pedalboard_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store)
):
    """PUT /api/v1/pedalboards/{id}/select - Select current pedalboard."""
    if not store.get(pedalboard_id):
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}
        )

    store._current_id = pedalboard_id
    return JSONResponse(status_code=200)

@router.put("/{pedalboard_id}/rename")
async def rename_pedalboard(
    pedalboard_id: int,
    request: dict,
    store: PedalboardStore = Depends(get_pedalboard_store)
):
    """PUT /api/v1/pedalboards/{id}/rename - Rename pedalboard."""
    name = request.get("name")
    if not name:
        raise HTTPException(
            status_code=400,
            detail={"error": "Name required", "code": "INVALID_REQUEST"}
        )

    pb = store.rename(pedalboard_id, name)
    if not pb:
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}
        )

    return JSONResponse(status_code=200)
```

```python
# src/api/routes/effects.py
from fastapi import APIRouter, HTTPException, Depends
from storage.pedalboard_store import PedalboardStore
from effects.registry import EffectsRegistry

effect_router = APIRouter(prefix="/api/v1")

@effect_router.get("/effects")
async def list_effects(registry: EffectsRegistry = Depends(get_effects_registry)):
    """GET /api/v1/effects - List available effects."""
    return {"effects": registry.get_all()}

@effect_router.get("/effects/{uri:path}")
async def get_effect(uri: str, registry: EffectsRegistry = Depends(get_effects_registry)):
    """GET /api/v1/effects/{uri} - Get effect details."""
    effect = registry.get(uri)
    if not effect:
        raise HTTPException(
            status_code=404,
            detail={"error": "Effect not available", "code": "EFFECT_NOT_AVAILABLE"}
        )
    return effect

@effect_router.post("/pedalboards/{pedalboard_id}/effects")
async def create_effect_instance(
    pedalboard_id: int,
    request: dict,
    store: PedalboardStore = Depends(get_pedalboard_store),
    registry: EffectsRegistry = Depends(get_effects_registry),
    client: ModHostClient = Depends(get_mod_host_client)
):
    """POST /api/v1/pedalboards/{id}/effects - Add effect to pedalboard."""
    pb = store.get(pedalboard_id)
    if not pb:
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}
        }

    effect_uri = request.get("effect_uri")
    if not effect_uri or not registry.get(effect_uri):
        raise HTTPException(
            status_code=404,
            detail={"error": "Effect not available", "code": "EFFECT_NOT_AVAILABLE"}
        )

    # Generate unique instance ID
    instance_id = max((e.id for e in pb.effects), default=0) + 1

    # Add to mod-host
    status = client.add_plugin(effect_uri, instance_id)
    if status < 0:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to add plugin (code: {status})", "code": "PLUGIN_ERROR"}
        )

    # Create effect instance record
    effect_instance = EffectInstance(
        id=instance_id,
        uri=effect_uri,
        name=request.get("name"),
        ports=[p["name"] for p in registry.get(effect_uri).ports],
        parameters={}
    )

    pb.effects.append(effect_instance)
    store._save_pedalboard(pb)

    return JSONResponse(status_code=201, content=effect_instance.model_dump())

@effect_router.get("/pedalboards/{pedalboard_id}/effects")
async def list_effect_instances(
    pedalboard_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store)
):
    """GET /api/v1/pedalboards/{id}/effects - List effects on pedalboard."""
    pb = store.get(pedalboard_id)
    if not pb:
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}
        )

    return {
        "effects": [
            {
                "id": e.id,
                "uri": e.uri,
                "name": e.name,
                "ports": e.ports,
                "parameters": e.parameters
            }
            for e in pb.effects
        ]
    }

@effect_router.delete("/pedalboards/{pedalboard_id}/effects/{effect_id}")
async def remove_effect_instance(
    pedalboard_id: int,
    effect_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store),
    client: ModHostClient = Depends(get_mod_host_client)
):
    """DELETE /api/v1/pedalboards/{id}/effects/{effect_id} - Remove effect."""
    pb = store.get(pedalboard_id)
    if not pb:
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}
        )

    effect = next((e for e in pb.effects if e.id == effect_id), None)
    if not effect:
        raise HTTPException(
            status_code=404,
            detail={"error": "Effect instance not found", "code": "EFFECT_INSTANCE_NOT_FOUND"}
        )

    # Remove from mod-host
    client.remove_plugin(effect_id)

    # Remove effect and related connections
    pb.effects = [e for e in pb.effects if e.id != effect_id]
    pb.connections = [
        c for c in pb.connections
        if effect_id not in [c.input_port_id, c.output_port_id]
    ]

    store._save_pedalboard(pb)
    return JSONResponse(status_code=204)
```

```python
# src/api/routes/connections.py
from fastapi import APIRouter, HTTPException, Depends
from storage.pedalboard_store import PedalboardStore

connection_router = APIRouter(prefix="/api/v1")

@connection_router.post("/pedalboards/{pedalboard_id}/connections")
async def create_connection(
    pedalboard_id: int,
    request: dict,
    store: PedalboardStore = Depends(get_pedalboard_store),
    client: ModHostClient = Depends(get_mod_host_client)
):
    """POST /api/v1/pedalboards/{id}/connections - Create connection."""
    pb = store.get(pedalboard_id)
    if not pb:
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}
        )

    input_port_id = request.get("input_port_id")
    output_port_id = request.get("output_port_id")

    if not input_port_id or not output_port_id:
        raise HTTPException(
            status_code=400,
            detail={"error": "Port IDs required", "code": "INVALID_REQUEST"}
        )

    # Validate ports exist (check both system and effect ports)
    all_ports = set()
    for effect in pb.effects:
        for port in effect.ports:
            all_ports.add(f"effect_{effect.id}:{port}")

    # Add system ports (would need to query JACK for actual ports)
    # For now, assume common system ports exist
    all_ports.add("system:capture_1")
    all_ports.add("system:capture_2")
    all_ports.add("system:playback_1")
    all_ports.add("system:playback_2")

    if input_port_id not in all_ports or output_port_id not in all_ports:
        raise HTTPException(
            status_code=404,
            detail={"error": "Port not found", "code": "PORT_NOT_FOUND"}
        )

    # Create connection in mod-host
    status = client.connect_ports(input_port_id, output_port_id)
    if status < 0:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to connect ports (code: {status})", "code": "CONNECTION_ERROR"}
        )

    # Create connection record
    connection_id = max((c.id for c in pb.connections), default=0) + 1
    connection = Connection(
        id=connection_id,
        input_port_id=input_port_id,
        output_port_id=output_port_id
    )

    pb.connections.append(connection)
    store._save_pedalboard(pb)

    return JSONResponse(status_code=201, content={"id": connection_id})

@connection_router.get("/pedalboards/{pedalboard_id}/connections")
async def list_connections(
    pedalboard_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store)
):
    """GET /api/v1/pedalboards/{id}/connections - List connections."""
    pb = store.get(pedalboard_id)
    if not pb:
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}
        )

    return {"connections": pb.connections}

@connection_router.delete("/pedalboards/{pedalboard_id}/connections/{connection_id}")
async def remove_connection(
    pedalboard_id: int,
    connection_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store),
    client: ModHostClient = Depends(get_mod_host_client)
):
    """DELETE /api/v1/pedalboards/{id}/connections/{connection_id}."""
    pb = store.get(pedalboard_id)
    if not pb:
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}
        )

    connection = next((c for c in pb.connections if c.id == connection_id), None)
    if not connection:
        raise HTTPException(
            status_code=404,
            detail={"error": "Connection not found", "code": "CONNECTION_NOT_FOUND"}
        )

    # Disconnect in mod-host
    client.disconnect_ports(connection.input_port_id, connection.output_port_id)

    # Remove connection record
    pb.connections = [c for c in pb.connections if c.id != connection_id]
    store._save_pedalboard(pb)

    return JSONResponse(status_code=204)
```

```python
# src/api/routes/ports.py
from fastapi import APIRouter, HTTPException, Depends

port_router = APIRouter(prefix="/api/v1")

@port_router.get("/pedalboards/{pedalboard_id}/ports")
async def list_ports(
    pedalboard_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store)
):
    """GET /api/v1/pedalboards/{id}/ports - List all ports."""
    pb = store.get(pedalboard_id)
    if not pb:
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}
        )

    ports = []

    # Add system ports
    # In a real implementation, these would be queried from JACK
    ports.extend([
        {
            "id": "system:capture_1",
            "name": "Input 1",
            "type": "input",
            "owner_type": "system"
        },
        {
            "id": "system:capture_2",
            "name": "Input 2",
            "type": "input",
            "owner_type": "system"
        },
        {
            "id": "system:playback_1",
            "name": "Output 1",
            "type": "output",
            "owner_type": "system"
        },
        {
            "id": "system:playback_2",
            "name": "Output 2",
            "type": "output",
            "owner_type": "system"
        }
    ])

    # Add effect instance ports
    for effect in pb.effects:
        for port_name in effect.ports:
            port_type = "input" if port_name == "input" else "output"
            ports.append({
                "id": f"effect_{effect.id}:{port_name}",
                "name": port_name,
                "type": port_type,
                "owner_type": "effect",
                "effect_instance_id": effect.id
            })

    return {"ports": ports}
```

```python
# src/api/routes/parameters.py
from fastapi import APIRouter, HTTPException, Depends
from storage.pedalboard_store import PedalboardStore
from effects.registry import EffectsRegistry

param_router = APIRouter(prefix="/api/v1")

@param_router.get("/pedalboards/{pedalboard_id}/effects/{effect_id}/parameters")
async def get_parameters(
    pedalboard_id: int,
    effect_id: int,
    store: PedalboardStore = Depends(get_pedalboard_store),
    registry: EffectsRegistry = Depends(get_effects_registry)
):
    """GET /api/v1/pedalboards/{id}/effects/{effect_id}/parameters."""
    pb = store.get(pedalboard_id)
    if not pb:
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}
        )

    effect = next((e for e in pb.effects if e.id == effect_id), None)
    if not effect:
        raise HTTPException(
            status_code=404,
            detail={"error": "Effect instance not found", "code": "EFFECT_INSTANCE_NOT_FOUND"}
        )

    # Return stored parameters with metadata from registry
    effect_info = registry.get(effect.uri)
    return {
        "parameters": [
            {
                "name": param.name,
                "type": param.type,
                "value": effect.parameters.get(param.name, param.default),
                "min": param.min,
                "max": param.max,
                "default": param.default
            }
            for param in effect_info.parameters
        ]
    }

@param_router.get("/pedalboards/{pedalboard_id}/effects/{effect_id}/parameters/{param_name}")
async def get_parameter(
    pedalboard_id: int,
    effect_id: int,
    param_name: str,
    store: PedalboardStore = Depends(get_pedalboard_store),
    registry: EffectsRegistry = Depends(get_effects_registry)
):
    """GET /api/v1/pedalboards/{id}/effects/{effect_id}/parameters/{param_name}."""
    pb = store.get(pedalboard_id)
    if not pb:
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}
        )

    effect = next((e for e in pb.effects if e.id == effect_id), None)
    if not effect:
        raise HTTPException(
            status_code=404,
            detail={"error": "Effect instance not found", "code": "EFFECT_INSTANCE_NOT_FOUND"}
        )

    effect_info = registry.get(effect.uri)
    param_info = next((p for p in effect_info.parameters if p.name == param_name), None)

    if not param_info:
        raise HTTPException(
            status_code=404,
            detail={"error": "Parameter not found", "code": "PARAMETER_NOT_FOUND"}
        )

    return {
        "name": param_info.name,
        "type": param_info.type,
        "value": effect.parameters.get(param_name, param_info.default),
        "min": param_info.min,
        "max": param_info.max,
        "default": param_info.default
    }

@param_router.put("/pedalboards/{pedalboard_id}/effects/{effect_id}/parameters/{param_name}")
async def set_parameter(
    pedalboard_id: int,
    effect_id: int,
    param_name: str,
    request: dict,
    store: PedalboardStore = Depends(get_pedalboard_store),
    registry: EffectsRegistry = Depends(get_effects_registry),
    client: ModHostClient = Depends(get_mod_host_client)
):
    """PUT /api/v1/pedalboards/{id}/effects/{effect_id}/parameters/{param_name}."""
    pb = store.get(pedalboard_id)
    if not pb:
        raise HTTPException(
            status_code=404,
            detail={"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}
        )

    effect = next((e for e in pb.effects if e.id == effect_id), None)
    if not effect:
        raise HTTPException(
            status_code=404,
            detail={"error": "Effect instance not found", "code": "EFFECT_INSTANCE_NOT_FOUND"}
        )

    value = request.get("value")
    if value is None:
        raise HTTPException(
            status_code=400,
            detail={"error": "Value required", "code": "INVALID_REQUEST"}
        )

    effect_info = registry.get(effect.uri)
    param_info = next((p for p in effect_info.parameters if p.name == param_name), None)

    if not param_info:
        raise HTTPException(
            status_code=404,
            detail={"error": "Parameter not found", "code": "PARAMETER_NOT_FOUND"}
        )

    # Validate parameter value
    if param_info.type == ParameterType.NUMBER and param_info.min is not None:
        if isinstance(value, (int, float)) and (value < param_info.min or value > param_info.max):
            raise HTTPException(
                status_code=400,
                detail={"error": "Value out of range", "code": "INVALID_PARAMETER"}
            )

    # Update mod-host
    if param_name == "model":
        # Use patch_set for model files
        property_uri = f"{effect.uri}#model"
        status = client.patch_set(effect.id, property_uri, value)
    else:
        # Use param_set for other parameters
        status = client.param_set(effect.id, param_name, float(value))

    if status < 0:
        raise HTTPException(
            status_code=500,
            detail={"error": f"Failed to set parameter (code: {status})", "code": "PARAMETER_ERROR"}
        )

    # Update local state
    effect.parameters[param_name] = value
    store._save_pedalboard(pb)

    return JSONResponse(status_code=200)
```

### 6. Main Application

```python
# src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.pedalboards import router as pedalboards_router
from api.routes.effects import effect_router
from api.routes.connections import connection_router
from api.routes.ports import port_router
from api.routes.parameters import param_router

app = FastAPI(
    title="Pedalboard API",
    description="REST API for managing pedalboards, effects, and connections",
    version="1.0.0"
)

# CORS for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pedalboards_router)
app.include_router(effect_router)
app.include_router(connection_router)
app.include_router(port_router)
app.include_router(param_router)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
```

### 7. Docker Configuration

```python
# services/pedalboard-api/requirements.txt
fastapi>=0.100.0
uvicorn[standard]>=0.22.0
pydantic>=2.0.0
```

```dockerfile
# services/pedalboard-api/Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "80"]
```

### 8. Deployment Configuration

```yaml
# manifests/partials/pedalboard-api.yaml
x-common: &common
  platform: ${PLATFORM}

services:
  pedalboard-api:
    <<: *common
    image: ghcr.io/rcwbr/nam-box/pedalboard-api:local
    volumes:
      - effects-state:/var/mod/pedalboards
    depends_on:
      - effects
    environment:
      - MOD_HOST_HOST=effects
      - MOD_HOST_PORT=5555
      - PEDALBOARD_DATA_DIR=/var/mod/pedalboards
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.pedalboard-api.rule=PathPrefix(`/api/v1`)"
      - "traefik.http.routers.pedalboard-api.entrypoints=websecure"
      - "traefik.http.routers.pedalboard-api.priority=100"
      - "traefik.http.routers.pedalboard-api.service=pedalboard-api@docker"
      - "traefik.http.services.pedalboard-api.loadbalancer.server.port=80"
    networks:
      - proxy
    restart: unless-stopped
```

## Key Implementation Decisions

### 1. Instance ID Generation

The API uses integer instance IDs (0-9999) consistent with mod-host. During pedalboard loading, these must be mapped appropriately. For NAM effects, the frontend currently uses `nam{timestamp}` format which would need translation.

### 2. Port Identification

- **System ports**: `system:capture_N`, `system:playback_N`
- **Effect ports**: `effect_{instance}:input`, `effect_{instance}:output`

Port IDs are strings, allowing them to identify both system and effect ports.

### 3. Parameter Types

- `number`: Float values with min/max constraints (validated before sending to mod-host)
- `filename`: String paths (used for NAM model files via patch_set)
- `string`: Generic string values

### 4. Error Handling

All errors return JSON with `error` and `code` fields. The implementation maps mod-host error codes to API error codes where appropriate:
- `-102` (instantiation failed) → `500` with `PLUGIN_ERROR`
- `-205` (connection failed) → `500` with `CONNECTION_ERROR`

### 5. Persistence Strategy

Pedalboards are stored as JSON files. On load:
1. Read all JSON files from the data directory
2. Track current pedalboard ID separately
3. On modification, write back to the file

The implementation should also handle loading pedalboards into mod-host:
- When selecting a pedalboard, remove all current plugins
- Re-add plugins from the pedalboard state
- Re-connect ports as defined

### 6. Integration Points

The pedalboard API integrates with existing components:

| Component | Integration |
|-----------|-------------|
| mod-host (TCP 5555) | Real-time plugin control via socket protocol |
| mod-ui (WebSocket) | Receives real-time updates on state changes |
| File API (`/api/model`) | References model files for NAM plugins |
| Web frontend | Consumes REST API for UI state management |

## Endpoint Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/pedalboards` | GET | List all pedalboards |
| `/api/v1/pedalboards` | POST | Create pedalboard |
| `/api/v1/pedalboards/current` | GET | Get current pedalboard |
| `/api/v1/pedalboards/{id}` | GET | Get specific pedalboard |
| `/api/v1/pedalboards/{id}` | DELETE | Delete pedalboard |
| `/api/v1/pedalboards/{id}/select` | PUT | Select as current |
| `/api/v1/pedalboards/{id}/rename` | PUT | Rename pedalboard |
| `/api/v1/effects` | GET | List available effects |
| `/api/v1/effects/{uri}` | GET | Get effect details |
| `/api/v1/pedalboards/{id}/effects` | GET | List effects on pedalboard |
| `/api/v1/pedalboards/{id}/effects` | POST | Add effect to pedalboard |
| `/api/v1/pedalboards/{id}/effects/{effect_id}` | DELETE | Remove effect |
| `/api/v1/pedalboards/{id}/ports` | GET | List all ports |
| `/api/v1/pedalboards/{id}/connections` | GET | List connections |
| `/api/v1/pedalboards/{id}/connections` | POST | Create connection |
| `/api/v1/pedalboards/{id}/connections/{connection_id}` | DELETE | Remove connection |
| `/api/v1/pedalboards/{id}/effects/{effect_id}/parameters` | GET | Get all parameters |
| `/api/v1/pedalboards/{id}/effects/{effect_id}/parameters/{param_name}` | GET | Get specific parameter |
| `/api/v1/pedalboards/{id}/effects/{effect_id}/parameters/{param_name}` | PUT | Set parameter value |

## Testing Considerations

1. **Unit tests**: Mock the ModHostClient for testing API logic without hardware
2. **Integration tests**: Use the exploration stack to test against real mod-host
3. **End-to-end tests**: Full API coverage with pedalboard lifecycle operations

## Future Extensions

1. **Snapshot support**: Implement save/load for pedalboard snapshots (current state under mod-ui control)
2. **MIDI mapping**: Add endpoints for MIDI control mappings
3. **CV control**: Add endpoints for Control Voltage mappings
4. **Websocket events**: Push real-time updates to connected clients when state changes