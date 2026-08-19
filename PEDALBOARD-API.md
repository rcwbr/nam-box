# Pedalboard Management API

A REST API for managing pedalboards, effect instances, ports, connections, and parameters.

## Overview

- **Base URL**: `/api/v1`
- **Current Pedalboard**: One pedalboard is active at a time; changes apply to it
- **Persistence**: All changes are saved automatically to disk
- **ID Scheme**: Pedalboards, effect instances, and connections use auto-generated integers; ports use string IDs like "system:capture_2"

---

## Pedalboards

### Endpoints

#### `GET /pedalboards`
List all available pedalboards.

**Response**: `200 OK` with `application/json`
```json
{
  "1": {
    "id": 1,
    "name": "Clean Tone",
    "file": "clean-tone.json"
  }
}
```

#### `GET /pedalboards/current`
Get the current pedalboard.

**Response**: `200 OK` with pedalboard details, or `204 No Content` if no pedalboard is currently selected.

**Errors**: None.

#### `GET /pedalboards/{id}`
Get full details of a specific pedalboard.

**Response**: `200 OK` with `application/json`
```json
{
  "id": 1,
  "name": "Clean Tone",
  "effects": [...],
  "connections": [...],
  "parameters": [...]
}
```

**Errors**: 
- `404 Not Found` - `PEDALBOARD_NOT_FOUND` - Pedalboard ID does not exist.

#### `POST /pedalboards`
Create a new pedalboard. Can create empty or as a duplicate of the current board.

**Request Body**:
```json
{
  "name": "New Board Name",
  "duplicate_current": false
}
```

**Response**: `201 Created` with pedalboard details; sets as current.

**Errors**: 
- `400 Bad Request` - `INVALID_REQUEST` - Malformed request body.

#### `DELETE /pedalboards/{id}`
Delete a pedalboard. If it's the current pedalboard, no pedalboard will be current until a new one is selected.

**Response**: `204 No Content`

**Errors**: 
- `404 Not Found` - `PEDALBOARD_NOT_FOUND` - Pedalboard ID does not exist.

#### `PUT /pedalboards/{id}/select`
Select a pedalboard to make it the current one.

**Response**: `200 OK`

**Errors**: 
- `404 Not Found` - `PEDALBOARD_NOT_FOUND` - Pedalboard ID does not exist.

#### `PUT /pedalboards/{id}/rename`
Rename a pedalboard.

**Request Body**:
```json
{ "name": "New Name" }
```

**Response**: `200 OK`

**Errors**: 
- `404 Not Found` - `PEDALBOARD_NOT_FOUND` - Pedalboard ID does not exist.
- `400 Bad Request` - `INVALID_REQUEST` - Missing or invalid name.

---

## Available Effects

Available effects are read-only and sourced from system state. They represent the effect types that can be instantiated on pedalboards.

### Endpoints

#### `GET /effects`
List all available effects in the system.

**Response**: `200 OK` with `application/json`
```json
[
  {
    "uri": "http://example.com/effects/overdrive",
    "name": "Tube Overdrive",
    "ports": [
      { "name": "input", "type": "input" },
      { "name": "output", "type": "output" }
    ],
    "parameters": {
      "drive": {
        "name": "drive",
        "type": "number",
        "min": 0.0,
        "max": 1.0,
        "default": 0.5
      }
    }
  }
]
```

**Errors**: None.

#### `GET /effects/{uri}`
Get details for a specific effect by URI.

**Response**: `200 OK` with effect details.

**Errors**: 
- `404 Not Found` - `EFFECT_NOT_AVAILABLE` - Effect URI not found in system.

---

## Effect Instances

### Endpoints

#### `POST /pedalboards/{id}/effects`
Create an effect instance on a pedalboard.

**Request Body**:
```json
{
  "effect_uri": "http://example.com/effects/overdrive",
  "name": "Optional Human Name"
}
```

**Response**: `201 Created` with effect instance details including generated integer ID.

**Errors**: 
- `404 Not Found` - `PEDALBOARD_NOT_FOUND` - Pedalboard ID does not exist.
- `404 Not Found` - `EFFECT_NOT_AVAILABLE` - Effect URI not found in system.

#### `GET /pedalboards/{id}/effects`
List all effect instances on a pedalboard.

**Response**: `200 OK` with `application/json`
```json
{
  "0": {
    "uri": "http://example.com/effects/overdrive",
    "name": "Optional Human Name",
    "ports": [
      {"name": "input", "type": "input"},
      {"name": "output", "type": "output"}
    ],
    "parameters": {
      "drive": {
        "name": "drive",
        "type": "number",
        "value": 0.7,
        "min": 0.0,
        "max": 1.0,
        "default": 0.5
      }
    }
  }
}
```

**Errors**: 
- `404 Not Found` - `PEDALBOARD_NOT_FOUND` - Pedalboard ID does not exist.

#### `DELETE /pedalboards/{id}/effects/{effect_id}`
Remove an effect instance and all its connections.

**Response**: `204 No Content`

**Errors**: 
- `404 Not Found` - `PEDALBOARD_NOT_FOUND` - Pedalboard ID does not exist.
- `404 Not Found` - `EFFECT_INSTANCE_NOT_FOUND` - Effect instance ID does not exist on pedalboard.

---

## Ports

Ports are read-only and sourced from system state. Each port belongs to either:
- An effect instance (created on the pedalboard)
- The system (representing input/output jacks)

#### `GET /pedalboards/{id}/ports`
List all ports available on the pedalboard (effect instance ports + system ports).

**Response**: `200 OK` with `application/json`
```json
[
  {
    "name": "capture_2",
    "type": "input",
    "owner_type": "system"
  },
  {
    "name": "output",
    "type": "output",
    "owner_type": "effect",
    "effect_instance_id": 1
  }
]
```

**Errors**: 
- `404 Not Found` - `PEDALBOARD_NOT_FOUND` - Pedalboard ID does not exist.

---

## Connections

### Endpoints

#### `POST /pedalboards/{id}/connections`
Create a connection between an input port and an output port. Either port can already have other connections.

**Request Body**:
```json
{
  "input_port_id": "system:capture_2",
  "output_port_id": "overdrive:output_1"
}
```

**Response**: `201 Created` with connection ID.

**Errors**: 
- `404 Not Found` - `PEDALBOARD_NOT_FOUND` - Pedalboard ID does not exist.
- `404 Not Found` - `PORT_NOT_FOUND` - Specified port ID does not exist.
- `400 Bad Request` - `INVALID_REQUEST` - Missing port IDs or malformed body.

#### `GET /pedalboards/{id}/connections`
List all connections on a pedalboard.

**Response**: `200 OK` with `application/json`
```json
{
  "1": {
    "id": 1,
    "input_port_id": "system:capture_2",
    "output_port_id": "overdrive:output_1"
  }
}
```

**Errors**: 
- `404 Not Found` - `PEDALBOARD_NOT_FOUND` - Pedalboard ID does not exist.

#### `DELETE /pedalboards/{id}/connections/{connection_id}`
Remove a connection.

**Response**: `204 No Content`

**Errors**: 
- `404 Not Found` - `PEDALBOARD_NOT_FOUND` - Pedalboard ID does not exist.
- `404 Not Found` - `CONNECTION_NOT_FOUND` - Connection ID does not exist.

---

## Parameters

### Endpoints

#### `GET /pedalboards/{id}/effects/{effect_id}/parameters`
Get all parameter values for an effect instance.

**Response**: `200 OK` with `application/json`
```json
{
  "drive": {
    "name": "drive",
    "type": "number",
    "value": 0.7,
    "min": 0.0,
    "max": 1.0,
    "default": 0.5
  }
}
```

**Errors**: 
- `404 Not Found` - `PEDALBOARD_NOT_FOUND` - Pedalboard ID does not exist.
- `404 Not Found` - `EFFECT_INSTANCE_NOT_FOUND` - Effect instance ID does not exist on pedalboard.

#### `GET /pedalboards/{id}/effects/{effect_id}/parameters/{param_name}`
Get a specific parameter value.

**Response**: `200 OK` with `application/json`
```json
{
  "name": "drive",
  "type": "number",
  "value": 0.7,
  "min": 0.0,
  "max": 1.0,
  "default": 0.5
}
```

**Errors**: 
- `404 Not Found` - `PEDALBOARD_NOT_FOUND` - Pedalboard ID does not exist.
- `404 Not Found` - `EFFECT_INSTANCE_NOT_FOUND` - Effect instance ID does not exist.
- `404 Not Found` - `PARAMETER_NOT_FOUND` - Parameter name not found on effect.

#### `PUT /pedalboards/{id}/effects/{effect_id}/parameters/{param_name}`
Set a parameter value. Follows the effect's declared type and constraints.

**Request Body**:
```json
{ "value": 0.85 }
```

**Response**: `200 OK`

**Errors**: 
- `404 Not Found` - `PEDALBOARD_NOT_FOUND` - Pedalboard ID does not exist.
- `404 Not Found` - `EFFECT_INSTANCE_NOT_FOUND` - Effect instance ID does not exist.
- `404 Not Found` - `PARAMETER_NOT_FOUND` - Parameter name not found.
- `400 Bad Request` - `INVALID_PARAMETER` - Parameter value violates constraints.
- `400 Bad Request` - `INVALID_REQUEST` - Missing value in request body.

---

## Parameter Types

Parameters can have the following types:

### `number`
Numeric values with min/max constraints and a default value.
```json
{
  "name": "drive",
  "type": "number",
  "value": 0.7,
  "min": 0.0,
  "max": 1.0,
  "default": 0.5
}
```

### `filename`
String values representing file paths. No min/max constraints.
```json
{
  "name": "impulse_file",
  "type": "filename",
  "value": "/path/to/impulse.wav",
  "default": ""
}
```

---

## Error Responses

All errors return `application/json` with structure:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

**Error Code Reference**:
- `PEDALBOARD_NOT_FOUND` - Pedalboard ID does not exist
- `EFFECT_INSTANCE_NOT_FOUND` - Effect instance ID does not exist on pedalboard
- `PORT_NOT_FOUND` - Port ID does not exist
- `CONNECTION_NOT_FOUND` - Connection ID does not exist
- `PARAMETER_NOT_FOUND` - Parameter name not found on effect
- `EFFECT_NOT_AVAILABLE` - Effect URI not found in system
- `INVALID_PARAMETER` - Parameter value violates constraints
- `INVALID_REQUEST` - Malformed request body