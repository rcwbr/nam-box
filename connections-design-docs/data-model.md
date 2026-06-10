# Data Model Design: Port Properties and Port Units

## Overview

This document describes the data model changes needed to support:
1. **Port properties** - Including input/output directionality read from `jack_lsp -p`
2. **Port units** - Dynamic grouping of ports managed via API endpoints
3. **Unit naming** - Configurable unit names via API

## Current State Analysis

The current `PortList` model in [services/effects/main.py](services/effects/main.py) provides:
```python
class PortList(BaseModel):
    ports: List[str]
```

The `list_ports()` method runs `jack_lsp` without the `-p` flag, returning only port names.

## Proposed Data Model Changes

### 1. Enhanced Port Model

Replace simple string-based port list with a rich port object that includes direction properties:

```python
class Port(BaseModel):
    """Represents a JACK port with its properties."""
    name: str                    # Full port name (e.g., "system:capture_1")
    direction: str               # "input" or "output" - derived from jack_lsp -p properties
    is_physical: bool = False    # True for hardware ports (physical property)
    is_terminal: bool = False    # True for terminal ports (terminal property)
```

### 2. Port Unit Model

New model for dynamically configurable port groupings:

```python
class PortUnit(BaseModel):
    """A unit representing a group of related ports."""
    id: str                      # Unique identifier for the unit
    name: str                    # Human-readable name (configurable via API)
    port_names: List[str] = []   # List of port names in this unit
    created_at: Optional[float] = None
    updated_at: Optional[float] = None
```

### 3. Updated State Model

Extend `AppState` to include port units:

```python
class AppState(BaseModel):
    current_model: Optional[str] = None
    connections: List[JackConnection] = []
    devices: List[str] = []
    jackd_args: List[str] = []
    stereo: bool = False
    port_units: Dict[str, PortUnit] = {}  # keyed by unit_id
```

### 4. Port List Response

Update endpoint response to include units:

```python
class PortListResponse(BaseModel):
    ports: List[Port]
    units: List[PortUnit]        # All defined port units
```

## API Endpoint Design

### Port Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ports` | GET | List all ports with their input/output properties (enhanced response) |

### Port Unit Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/port-units` | GET | List all port units |
| `/port-units` | POST | Create a new port unit (body: `{"name": "My Unit"}`) |
| `/port-units/{unit_id}` | GET | Get specific unit details |
| `/port-units/{unit_id}` | PUT | Update unit (body: `{"name": "New Name", "port_names": [...]}`) |
| `/port-units/{unit_id}` | DELETE | Delete a unit |
| `/port-units/{unit_id}/ports/{port_name}` | POST | Add a port to a unit |
| `/port-units/{unit_id}/ports/{port_name}` | DELETE | Remove a port from a unit |
| `/port-units/{unit_id}/name` | PUT | Update just the unit name |

### Request/Response Models

```python
# Create/Update Unit requests
class PortUnitCreate(BaseModel):
    name: str

class PortUnitUpdate(BaseModel):
    name: Optional[str] = None
    port_names: Optional[List[str]] = None
```

## Implementation Details

### Parsing `jack_lsp -p` Output

The `-p` flag outputs port properties in a key-value format:

```
system:capture_1
	properties: output,physical,terminal,
system:capture_2
	properties: output,physical,terminal,
mod-host:midi_in
	properties: input,
```

Parse logic in `NamAudioManager.list_ports()`:
1. Run `jack_lsp -p` and capture output
2. Parse each port entry: extract port name and properties
3. Determine direction from properties (input vs output)
4. Set boolean flags based on property presence
5. Do NOT embed unit reference in port object - units are separate entities

### Port-Unit Relationship Management

- Ports are listed independently without unit references
- Units maintain their own `port_names` list
- Clients can correlate ports to units by matching port names
- This separation keeps Port objects simple and unit-agnostic

### State Persistence

Port units should be persisted to `state.json` alongside existing state. The `port_units` dictionary maps unit_id to PortUnit objects.

## Migration Considerations

### Initial State Load

On API startup:
1. Load existing state (may lack `port_units`)
2. Initialize empty `port_units` if missing
3. No port modification needed - units are separate from ports

### Default Units

Consider auto-creating units for:
- **Mod-host NAM ports**: Group L/R pairs automatically if stereo mode is enabled
- **System ports**: Group by card/device when detectable

This is optional and could be a future enhancement.

## Response Examples

### GET /ports

```json
{
  "ports": [
    {
      "name": "system:capture_1",
      "direction": "output",
      "is_physical": true,
      "is_terminal": true
    },
    {
      "name": "mod-host-01:audio_out_1",
      "direction": "output",
      "is_physical": false,
      "is_terminal": false
    },
    {
      "name": "mod-host-01:audio_in_1",
      "direction": "input",
      "is_physical": false,
      "is_terminal": false
    }
  ],
  "units": [
    {
      "id": "nam-stereo",
      "name": "NAM Audio Stereo Pair",
      "port_names": ["mod-host-01:audio_out_1", "mod-host-01:audio_in_1"],
      "created_at": 1234567890.0,
      "updated_at": 1234567890.0
    }
  ]
}
```

### POST /port-units

```json
// Request
{
  "name": "My Custom Unit"
}

// Response
{
  "id": "unit_a1b2c3",
  "name": "My Custom Unit",
  "port_names": [],
  "created_at": 1234567890.0,
  "updated_at": 1234567890.0
}
```

## Files to Modify

| File | Changes |
|------|---------|
| `services/effects/main.py` | Add `Port`, `PortUnit`, `PortUnitCreate`, `PortUnitUpdate` models; Update `PortList` to `PortListResponse`; Add unit management methods to `NamAudioManager`; Add port unit API endpoints; Modify `list_ports()` to parse `-p` output |

## Implementation Order

1. Add new Pydantic models (`Port`, `PortUnit`, etc.)
2. Modify `list_ports()` to parse `jack_lsp -p` and return enhanced data
3. Add port unit management methods to `NamAudioManager`
4. Add API endpoints for port unit CRUD operations
5. Update `AppState` to include `port_units` and persist to state.json
6. Handle backward compatibility for missing `port_units` in state file