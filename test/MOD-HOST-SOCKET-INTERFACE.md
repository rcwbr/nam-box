# mod-host Socket Interface Documentation

This document describes the TCP socket protocol provided by `mod-host` for controlling LV2 plugins.

## Source Repository

- **Repository**: https://github.com/mod-audio/mod-host
- **Reference Clone**: `/tmp/mod-host-original` (cloned for analysis)

## Connection Details

- **Protocol**: TCP Socket
- **Default Port**: 5555 (configurable via `-p` or `--socket-port`)
- **Feedback Port**: 5556 (configurable via `-f` or `--feedback-port`, optional)
- **Address Binding**: `INADDR_ANY` (all interfaces) on Linux, `INADDR_LOOPBACK` on MOD Devices hardware

## Protocol Format

All commands are sent as newline-terminated ASCII strings. Responses follow the format:
```
resp <status> [value]
```

Where:
- `status` is an integer (non-negative = success, negative = error)
- `value` is optional and only present for `param_get` commands

### Command Format (from mod-host.h)

```c
#define EFFECT_ADD           "add %s %i"
#define EFFECT_REMOVE        "remove %i"
#define EFFECT_PRESET_LOAD   "preset_load %i %s"
#define EFFECT_PRESET_SAVE   "preset_save %i %s %s %s"
#define EFFECT_PRESET_SHOW   "preset_show %s"
#define EFFECT_CONNECT       "connect %s %s"
#define EFFECT_DISCONNECT    "disconnect %s %s"
#define EFFECT_BYPASS        "bypass %i %i"
#define EFFECT_PARAM_SET     "param_set %i %s %s"
#define EFFECT_PARAM_GET     "param_get %i %s"
#define EFFECT_PARAM_MON     "param_monitor %i %s %s %f"
#define EFFECT_PATCH_GET     "patch_get %i %s"
#define EFFECT_PATCH_SET     "patch_set %i %s %s"
```

## Available Commands

### Plugin Management

#### `add <lv2_uri> <instance_number>`
Add an LV2 plugin as a JACK client.

**Arguments:**
- `lv2_uri`: Full URI of the LV2 plugin (e.g., `http://github.com/mikeoliphant/neural-amp-modeler-lv2`)
- `instance_number`: Integer 0-9999

**Example:**
```
add "http://github.com/mikeoliphant/neural-amp-modeler-lv2" 0
```

**Response:**
- Success: `resp 0` (the instance number)
- Error: `resp -101` (invalid URI) or `resp -102` (instantiation failed)

**Notes:**
- Creates JACK client named `effect_<instance_number>`
- Plugin ports follow: `effect_<instance>/input`, `effect_<instance>/output`

#### `remove <instance_number>`
Remove an LV2 plugin instance.

**Arguments:**
- `instance_number`: Integer, or `-1` to remove all plugins

**Example:**
```
remove 0
remove -1
```

**Response:** `resp 0` on success

### Parameter Control

#### `param_set <instance_number> <param_symbol> <param_value>`
Set a control port value.

**Arguments:**
- `instance_number`: Plugin instance number
- `param_symbol`: Parameter symbol/name (can include prefix like `input_level`)
- `param_value`: Numeric value (float)

**Example:**
```
param_set 0 input_level 0.0
param_set 0 output_level 0.0
```

**Response:** `resp 0` on success

#### `param_get <instance_number> <param_symbol>`
Get a control port value.

**Arguments:**
- `instance_number`: Plugin instance number
- `param_symbol`: Parameter symbol/name

**Example:**
```
param_get 0 input_level
```

**Response:**
```
resp 0 <value>
```

#### `param_monitor <instance_number> <param_symbol> <cond_op> <value>`
Monitor a control port with condition.

**Arguments:**
- `instance_number`: Plugin instance number
- `param_symbol`: Parameter symbol/name
- `cond_op`: Condition operator (`>`, `>=`, `<`, `<=`, `==`, `!=`)
- `value`: Threshold value (float)

**Example:**
```
param_monitor 0 gain > 2.5
```

### Patch Property Control (for NAM model files)

#### `patch_set <instance_number> <property_uri> <value>`
Set a property value using LV2 Patch protocol.

**Arguments:**
- `instance_number`: Plugin instance number
- `property_uri`: URI of the property (e.g., model parameter URI)
- `value`: Property value (string for paths, numeric for other types)

**Example (setting NAM model file):**
```
patch_set 0 http://github.com/mikeoliphant/neural-amp-modeler-lv2#model /opt/nam/models/silktone_classic.nam
```

**Response:** `resp 0` on success

**Notes:**
- This is the correct method for setting NAM model files (not `param_set`)
- The property URI is suffixed with `#model` for the model parameter
- For NAM plugin: `http://github.com/mikeoliphant/neural-amp-modeler-lv2#model`

#### `patch_get <instance_number> <property_uri>`
Get a property value using LV2 Patch protocol.

**Arguments:**
- `instance_number`: Plugin instance number
- `property_uri`: URI of the property

**Example:**
```
patch_get 0 http://github.com/mikeoliphant/neural-amp-modeler-lv2#model
```

**Response:** `resp 0` (success) - property values are sent via the feedback port, not the control socket response.

**Note:** For NAM model verification, use `param_get` with the parameter symbol to read back values, or monitor the feedback port for patch responses.

### Audio Routing

#### `connect <origin_port> <destination_port>`
Connect two JACK ports.

**Arguments:**
- `origin_port`: Source port name
- `destination_port`: Destination port name

**Example:**
```
connect "system:capture_1" "effect_0:input"
connect "effect_0:output" "system:playback_1"
```

**Response:** `resp 0` on success

#### `disconnect <origin_port> <destination_port>`
Disconnect two JACK ports.

**Arguments:**
- `origin_port`: Source port name
- `destination_port`: Destination port name

**Response:** `resp 0` on success

### Bypass Control

#### `bypass <instance_number> <bypass_value>`
Toggle effect processing.

**Arguments:**
- `instance_number`: Plugin instance number
- `bypass_value`: `1` to bypass, `0` to process

**Example:**
```
bypass 0 1
```

**Response:** `resp 0` on success

### Preset Management

#### `preset_load <instance_number> <preset_uri>`
Load a preset state.

**Arguments:**
- `instance_number`: Plugin instance number
- `preset_uri`: Full URI of the preset

**Response:** `resp 0` on success

#### `preset_save <instance_number> <preset_name> <dir> <file_name>`
Save a preset state.

**Response:** `resp 0` on success

#### `preset_show <preset_uri>`
Show preset information.

### MIDI Control

#### `midi_learn <instance_number> <param_symbol> <minimum> <maximum>`
Start MIDI learn for a control port.

**Example:**
```
midi_learn 0 gain 0.0 1.0
```

#### `midi_map <instance_number> <param_symbol> <midi_channel> <midi_cc> <minimum> <maximum>`
Map a MIDI controller to a parameter.

**Example:**
```
midi_map 0 gain 0 7 0.0 1.0
```

**Note:** MIDI CC value of `131` (0x83) is used for pitchbend.

#### `midi_unmap <instance_number> <param_symbol>`
Remove MIDI mapping.

**Example:**
```
midi_unmap 0 gain
```

### Control Chain

#### `cc_map <instance> <symbol> <device_id> <actuator_id> <label> <value> <min> <max> <steps> <extraflags> <unit> <scalepoints_count> ...`
Map a Control Chain actuator to a control port.

#### `cc_value_set <instance> <symbol> <value>`
Set the value of a mapped Control Chain actuator.

#### `cc_unmap <instance> <symbol>`
Remove Control Chain actuator mapping.

### CV (Control Voltage)

#### `cv_map <instance> <symbol> <port_name> <min> <max> <op_mode>`
Map a CV source port to a control port.

**Arguments:**
- `op_mode`: One of `-`, `+`, `b`, or `=` (operational mode)

**Example:**
```
cv_map 0 gain "AMS CV Source:CV Out 1" -24.0 3.0 =
```

#### `cv_unmap <instance> <symbol>`
Remove CV source port mapping.

### HMI (Hardware UI)

#### `hmi_map <instance> <symbol> <hw_id> <page> <subpage> <caps> <flags> <label> <min> <max> <steps>`
Map a hardware UI control to a parameter.

### Monitoring

#### `monitor <addr> <port> <status>`
Open a socket port for monitoring parameter changes.

**Arguments:**
- `addr`: IP address for monitoring client (e.g., `localhost`)
- `port`: Port number for monitoring connection
- `status`: `1` to start monitoring, `0` to stop

**Example:**
```
monitor localhost 12345 1
```

#### `monitor_output <instance_number> <param_symbol>`
Request monitoring of an output parameter on the feedback port.

**Example:**
```
monitor_output 0 meter
```

#### `monitor_midi_program <midi_channel> <enable>`
Listen to MIDI program change messages.

**Example:**
```
monitor_midi_program 0 1
```

#### `licensee <instance_number>`
Get the licensee name for a commercial plugin.

#### `cpu_load`
Get current JACK CPU load.

**Response:**
```
resp 0 <load_value>
```

### Transport Control

#### `transport <rolling> <beats_per_bar> <beats_per_minute>`
Change the global transport state.

**Example:**
```
transport 1 4 120
```

#### `transport_sync <mode>`
Change the transport sync mode.

**Arguments:**
- `mode`: `none`, `link`, or `midi`

**Example:**
```
transport_sync "midi"
```

#### `set_bpm <beats_per_minute>`
Set global BPM.

**Example:**
```
set_bpm 120.0
```

#### `set_bpb <beats_per_bar>`
Set global beats per bar.

**Example:**
```
set_bpb 4.0
```

### State Management

#### `state_load <file_path>`
Load pedalboard state from a file.

#### `state_save <file_path>`
Save current pedalboard state to a file.

#### `state_tmpdir <directory>`
Set temporary directory for state operations.

### External UI

#### `show_external_ui <instance_number>`
Show the external UI for a plugin.

#### `output_data_ready`
Report that the feedback port is ready for more messages.

### Bundle Management

#### `bundle_add <bundle_path>`
Add a bundle to the LV2 world.

#### `bundle_remove <bundle_path> <resource>`
Remove a bundle from the LV2 world.

### Features

#### `feature_enable <feature> <enable>`
Enable/disable a feature.

**Feature options:**
- `aggregated-midi`
- `freewheeling`
- `processing`

## Error Codes

| Status | Error | Description |
|--------|-------|-------------|
| -1 | ERR_INSTANCE_INVALID | Invalid instance number |
| -2 | ERR_INSTANCE_ALREADY_EXISTS | Instance already exists |
| -3 | ERR_INSTANCE_NON_EXISTS | Instance does not exist |
| -4 | ERR_INSTANCE_UNLICENSED | Commercial plugin not licensed |
| -101 | ERR_LV2_INVALID_URI | Invalid plugin/parameter URI |
| -102 | ERR_LV2_INSTANTIATION | Plugin instantiation failed |
| -103 | ERR_LV2_INVALID_PARAM_SYMBOL | Invalid parameter symbol |
| -104 | ERR_LV2_INVALID_PRESET_URI | Invalid preset URI |
| -105 | ERR_LV2_CANT_LOAD_STATE | Cannot load state |
| -201 | ERR_JACK_CLIENT_CREATION | JACK client creation error |
| -202 | ERR_JACK_CLIENT_ACTIVATION | JACK client activation error |
| -203 | ERR_JACK_CLIENT_DEACTIVATION | JACK client deactivation error |
| -204 | ERR_JACK_PORT_REGISTER | JACK port register error |
| -205 | ERR_JACK_PORT_CONNECTION | JACK port connection error |
| -206 | ERR_JACK_PORT_DISCONNECTION | JACK port disconnection error |
| -207 | ERR_JACK_VALUE_OUT_OF_RANGE | Value out of range |
| -301 | ERR_ASSIGNMENT_ALREADY_EXISTS | Assignment already exists |
| -302 | ERR_ASSIGNMENT_INVALID_OP | Invalid assignment operation |
| -303 | ERR_ASSIGNMENT_LIST_FULL | Assignment list full |
| -304 | ERR_ASSIGNMENT_FAILED | Assignment failed |
| -401 | ERR_CONTROL_CHAIN_UNAVAILABLE | Control Chain unavailable |
| -402 | ERR_LINK_UNAVAILABLE | Link unavailable |
| -403 | ERR_HMI_UNAVAILABLE | HMI unavailable |
| -404 | ERR_EXTERNAL_UI_UNAVAILABLE | External UI unavailable |
| -901 | ERR_MEMORY_ALLOCATION | Memory allocation error |
| -902 | ERR_INVALID_OPERATION | Invalid operation |

## NAM Plugin Specific Usage

### Full Workflow

1. **Start JACK** (usually done before mod-host):
   ```
   jackd -d dummy
   ```

2. **Start mod-host**:
   ```
   mod-host -n -p 5555
   ```

3. **Add NAM plugin**:
   ```
   add "http://github.com/mikeoliphant/neural-amp-modeler-lv2" 0
   ```

4. **Set model file**:
   ```
   patch_set 0 http://github.com/mikeoliphant/neural-amp-modeler-lv2#model /opt/nam/models/model.nam
   ```

5. **Connect audio ports**:
   ```
   connect "system:capture_1" "effect_0:input"
   connect "effect_0:output" "system:playback_1"
   ```

6. **Set input/output levels**:
   ```
   param_set 0 input_level 0.0
   param_set 0 output_level 0.0
   ```

7. **Verify settings**:
   ```
   param_get 0 input_level
   param_get 0 output_level
   ```
   Response: `resp 0 <value>` (e.g., `resp 0 0.0000`)

## Socket Implementation Details

From `socket.c`:
- Uses `SOCK_STREAM` (TCP)
- Buffer size: 1024 bytes (configurable)
- Supports message sizes larger than buffer via reallocation
- Single client connection at a time (blocking accept)
- Responses include null terminator in sent data

From `protocol.c`:
- Commands are space-separated tokens
- Supports wildcard matching for variable arguments (`...`)
- Response sent back via `socket_send()` to the client socket

## Testing Notes

- The socket blocks on `accept()`, meaning only one client can connect at a time
- In the `effects:local` image, mod-ui connects first and owns the socket
- For standalone testing, run mod-host with `-n` flag without mod-ui

## Feedback Port

The feedback port (default 5556, configurable via `-f`) provides asynchronous notifications:

### Messages Received on Feedback Port

| Message | Description |
|---------|-------------|
| `patch_set <inst> <uri> p` | Patch set notification with path type (`p`) |
| `data_finish` | End of binary data transmission |
| `log <inst> <message>` | Log messages from plugins (e.g., NAM model loading) |

### Testing Feedback Port

Use `explore_mod_host_with_feedback.py` to monitor both sockets:

```python
# Connect to both control (5555) and feedback (5556) ports
# Start feedback listener BEFORE sending patch_get
# patch_get responses arrive as LV2 Patch messages on the feedback port
```

## Test Results

The following commands were verified working via the exploration stack:

| Command | Example | Response |
|---------|---------|----------|
| `add` | `add "http://...neural-amp-modeler-lv2" 0` | `resp 0` |
| `patch_get` | `patch_get 0 http://...#model` | `resp 0` (property values via feedback port) |
| `patch_set` | `patch_set 0 http://...#model /path/to/file.nam` | `resp 0` |
| `param_set` | `param_set 0 input_level 0.5` | `resp 0` |
| `param_get` | `param_get 0 input_level` | `resp 0 <value>` (e.g., `resp 0 0.5000`) |
| `bypass` | `bypass 0 1` | `resp 0` |
| `connect` | `connect "system:capture_1" "effect_0:input"` | `resp 0` |
| `remove` | `remove 0` | `resp 0` |
| `cpu_load` | `cpu_load` | `resp 0 <load>` (e.g., `resp 0 0.3670`) |

## Checking Model Load Status

### Using the Feedback Port

The feedback port (5556) receives log messages confirming model loading:

```bash
docker compose -f docker-compose.explore.yaml exec explorer python3 /scripts/check_model_loaded.py
```

Success indicator on feedback port:
```
log 0 Staging model change: `/opt/nam/models/test.nam`
```

### Feedback Port Utility

The `check_model_loaded.py` script:
1. Connects to both control (5555) and feedback (5556) sockets
2. Adds the NAM plugin
3. Sends `patch_set` to set the model file
4. Monitors feedback port for `log` messages indicating model staging
5. Reports whether model load confirmation was received

## References

### Prerequisites

1. The `effects:local` Docker image must be built:
   ```bash
   cd /workspaces/nam-box
   docker buildx bake effects
   ```

2. Navigate to the test directory:
   ```bash
   cd /workspaces/nam-box/test
   ```

### Starting the Test Stack

```bash
docker compose -f docker-compose.explore.yaml up -d
```

This starts:
- `mod-host` container: mod-host running with JACK dummy driver
- `explorer` container: Python environment for running scripts

### Running the Exploration Script

```bash
docker compose -f docker-compose.explore.yaml exec explorer python3 /scripts/explore_mod_host.py
```

Or start a shell in the explorer container and run interactively:

```bash
docker compose -f docker-compose.explore.yaml exec explorer bash
# Inside container:
python3 -c "
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('mod-host', 5555))
sock.sendall(b'cpu_load\n')
print(sock.recv(4096).decode())
sock.close()
"
```

### Stopping the Stack

```bash
docker compose -f docker-compose.explore.yaml down -v
```

The `-v` flag removes the named volumes for a clean state on next run.