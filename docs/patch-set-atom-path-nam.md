# Sending patch:Set Messages for atom:Path Model Parameter in NAM LV2 via Jalv

This document explains how to send a `patch:Set` message to set the `atom:Path` model parameter in the Neural Amp Modeler LV2 plugin when hosted by Jalv.

## Overview

The Neural Amp Modeler (NAM) LV2 plugin exposes its model parameter as a property-based control using the LV2 Patch extension. Unlike traditional control ports (float values), the model parameter uses `atom:Path` to accept file paths.

## Plugin Definition

From [`neural_amp_modeler.ttl.in`](../neural-amp-modeler-lv2/resources/neural_amp_modeler.ttl.in):

```turtle
<http://github.com/mikeoliphant/neural-amp-modeler-lv2#model>
    a lv2:Parameter;
    mod:fileTypes "nam,nammodel,json,aidax,aidadspmodel";
    rdfs:label "Neural Model";
    rdfs:range atom:Path.

<http://github.com/mikeoliphant/neural-amp-modeler-lv2>
    patch:writable <http://github.com/mikeoliphant/neural-amp-modeler-lv2#model>.
```

The parameter is addressed via the property URI `http://github.com/mikeoliphant/neural-amp-modeler-lv2#model`.

## Jalv Implementation

### Control ID Creation

In [`jalv_control.c:new_property_control()`](../jalv/src/control.c), jalv creates a `ControlID` for property-based parameters:

```c
ControlID*
new_property_control(LilvWorld* const       world,
                     const LilvNode*        property,
                     const JalvNodes* const nodes,
                     LV2_URID_Map* const    map,
                     LV2_Atom_Forge* const  forge)
{
    // ...
    id->value_type = map->map(map->handle, LV2_ATOM__Path);  // For atom:Path range
    // ...
}
```

### Sending Property Values

In [`jalv.c:jalv_set_control()`](../jalv/src/jalv.c:381-411), jalv forges a `patch:Set` message for property controls:

```c
void jalv_set_control(Jalv* jalv, const ControlID* control,
                      uint32_t size, LV2_URID type, const void* body)
{
    LV2_Atom_Forge forge = jalv->forge;
    LV2_Atom_Forge_Frame frame;
    uint8_t buf[MSG_BUFFER_SIZE];
    lv2_atom_forge_set_buffer(&forge, buf, sizeof(buf));

    lv2_atom_forge_object(&forge, &frame, 0, jalv->urids.patch_Set);
    lv2_atom_forge_key(&forge, jalv->urids.patch_property);
    lv2_atom_forge_urid(&forge, control->property);
    lv2_atom_forge_key(&forge, jalv->urids.patch_value);
    lv2_atom_forge_atom(&forge, size, type);
    lv2_atom_forge_write(&forge, body, size);

    const LV2_Atom* atom = lv2_atom_forge_deref(&forge, frame.ref);
    jalv_send_to_plugin(jalv, jalv->control_in,
                        lv2_atom_total_size(atom),
                        jalv->urids.atom_eventTransfer, atom);
}
```

## Plugin Side Response

In [`nam_plugin.cpp`](../neural-amp-modeler-lv2/src/nam_plugin.cpp:232-250), the plugin processes incoming `patch:Set` messages:

```cpp
if (obj->body.otype == uris.patch_Set) {
    const LV2_Atom* property = NULL;
    const LV2_Atom* file_path = NULL;

    lv2_atom_object_get(obj,
                        uris.patch_property, &property,
                        uris.patch_value, &file_path,
                        0);

    // Validation
    if (property && property->type == uris.atom_URID &&
        ((const LV2_Atom_URID*)property)->body == uris.model_Path &&
        file_path && file_path->type == uris.atom_Path &&
        file_path->size > 0 && file_path->size < MAX_FILE_NAME)
    {
        // Path body is located immediately after the atom header
        // copy the path string into the work message
        memcpy(msg.path, file_path + 1, file_path->size);
        schedule->schedule_work(schedule->handle, sizeof(msg), &msg);
    }
}
```

## Usage Guide

### Finding the Control

```c
// Look up the property control by symbol
ControlID* control = jalv_control_by_symbol(jalv, "model");
// The symbol is derived from the property URI fragment
```

### Preparing the Path Value

The `atom:Path` type is semantically identical to `atom:String` - both are null-terminated UTF-8 strings.

```c
const char* path = "/path/to/model.nam";
size_t path_len = strlen(path) + 1;  // Include null terminator in size

// The body passed to jalv_set_control should be the string content only
// (NOT including an atom header - jalv adds that)
```

### Calling jalv_set_control

```c
jalv_set_control(jalv, control, path_len, jalv->urids.atom_Path, path);
```

This results in the following LV2 Atom structure being sent to the plugin (as written to jalv's internal buffer):

```
[LV2_Atom_Object] {
    size: sizeof(LV2_Atom_Object_Body) + 2*8 + path_len + 1
    type: LV2_ATOM__Object
    body: { id: 0, otype: LV2_PATCH__Set }
}
[LV2_Atom_Property] {
    key: LV2_PATCH__property (8 bytes)
    value: LV2_Atom { size: 4, type: LV2_ATOM__URID } + URID value
}
[LV2_Atom_Property] {
    key: LV2_PATCH__value (8 bytes)
    value: LV2_Atom { size: path_len, type: LV2_ATOM__Path } + "path/to/model.nam\0"
}
```

The `LV2_Atom_Forge` functions handle padding to 64-bit alignment automatically.

## Common Pitfalls

1. **Missing null terminator**: The `file_path->size` must include the null terminator. The plugin uses `memcpy` with the exact size to copy into `LV2LoadModelMsg.path`, which is a raw char array. Without the null terminator in the atom body, `msg.path` won't be null-terminated, potentially causing string operations to read beyond the buffer.

2. **Wrong type**: Using `atom:String` instead of `atom:Path` works (they're both strings), but semantically `atom:Path` is correct as it indicates a filesystem path.

3. **Empty or too-long paths**: The plugin checks `file_path->size > 0 && file_path->size < MAX_FILE_NAME` (where `MAX_FILE_NAME` is 1024).

4. **Protocol mismatch**: Property messages must use the `atom:eventTransfer` protocol, not raw float values.

## Python Integration

The lilv bindings in this repository ([`lilv/bindings/python/lilv.py`](../lilv/bindings/python/lilv.py)) provide full access to LV2 plugin introspection and state management.

### 1. Plugin Discovery with python-lilv

```python
import sys
sys.path.insert(0, '/workspaces/nam-box/lilv/bindings/python')
import lilv

# Load LV2 world
world = lilv.World()
world.load_all()

# Find the NAM plugin
plugin_uri = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
plugins = world.get_all_plugins()
plugin = plugins.get_by_uri(plugin_uri)

# Discover the model property
model_property_uri = plugin_uri + "#model"
model_property = world.new_uri(model_property_uri)

# Check if it's patch:writable
is_writable = world.ask(plugin_uri, world.new_uri("http://lv2plug.in/ns/ext/patch#writable"), model_property)
print(f"Model property is writable: {is_writable}")

# Get the property's range (value type)
from lilv import Plugin
model_prop_node = world.new_uri(model_property_uri)
range_nodes = world.find_nodes(model_prop_node, 
                               world.new_uri("http://www.w3.org/2000/01/rdf-schema#range"),
                               None)
for node in range_nodes:
    print(f"Property range: {node}")  # Should be atom:Path
```

### 2. Control Port vs Property Ports

NAM has two types of ports:
- **Control ports (indices 4-6)**: `input_level`, `output_level`, `quality_scale` - float values
- **Property port (index 0 symbol "control")**: Accepts `patch:Set` messages for the model

```python
# List all ports to understand structure
for i in range(plugin.get_num_ports()):
    port = plugin.get_port_by_index(i)
    print(f"Port {i}: {port.get_symbol()} - {port.get_name()}")
    
# Find control input port (for patch messages)
control_port = plugin.get_port_by_designation("http://lv2plug.in/ns/lv2core#InputPort",
                                              "http://lv2plug.in/ns/lv2core#control")
print(f"Control port index: {control_port.get_index()}")
```

### 3. State-Based Model Loading (Recommended)

Use the LV2 State interface to load model paths via preset files:

```python
import lilv
import subprocess
import tempfile
import os

def set_nam_model_via_state(plugin_uri, model_path):
    """
    Create a state preset file and apply it.
    
    This works because NAM implements LV2 state with model path persistence.
    """
    world = lilv.World()
    world.load_all()
    
    plugin = world.new_uri(plugin_uri)
    
    # Create a minimal state.ttl that sets the model path
    # Note: Real implementation needs proper URID mapping and state:mapPath handling
    state_content = f'''@prefix patch: <http://lv2plug.in/ns/ext/patch#> .
@prefix atom: <http://lv2plug.in/ns/ext/atom#> .
@prefix state: <http://lv2plug.in/ns/ext/state#> .
@prefix lv2: <http://lv2plug.in/ns/lv2core#> .

# State containing model path
# The path here needs to be handled through state:mapPath feature
# which maps abstract path to filesystem path at save/restore time
'''
```

### 4. Real-time Control via Custom Host

This approach sends atom messages directly to a running jalv instance. **Important limitations:**

- jalv does not expose any IPC mechanism for external control of property parameters
- The UI-to-plugin ring buffer (`zix_ring`) is in process memory, not shared memory
- To achieve real-time control, you must either:
  1. **Modify jalv** to add a control protocol (OSC, Unix socket, HTTP, etc.)
  2. **Use state files** (the current approach in main.py) - restart jalv with `--load`
  3. **Build your own LV2 host** in Python/C++ using lilv directly

#### Option A: Minimal jalv Extension for Property Control

Add an OSC endpoint or Unix socket control to jalv. Key files to modify:

```c
// In jalv/src/jalv.c or new jalv_control_protocol.c
// Add a thread that listens on a Unix socket for JSON control commands

// Protocol: {"property": "model", "value": "/path/to/model.nam"}
// Then call jalv_set_control() internally:

void
handle_external_property_control(Jalv* jalv, const char* property_symbol, const char* value)
{
    ControlID* control = jalv_control_by_symbol(jalv, property_symbol);
    if (control && control->type == PROPERTY) {
        size_t value_len = strlen(value) + 1;  // Include null terminator
        jalv_set_control(jalv, control, value_len, jalv->urids.atom_Path, value);
    }
}
```

#### Option B: Build Your Own LV2 Host (Using Python-lilv)

For production real-time control, the most robust approach is to build a custom host that exposes a control API:

```python
#!/usr/bin/env python3
"""
Minimal LV2 host for real-time NAM model control.

This demonstrates the atom construction needed to send patch:Set messages.
Requires: liblilv, LV2 URID mapping, and JACK audio backend.
"""

import sys
import ctypes
from ctypes import c_uint32, c_int64, POINTER, c_char_p
import struct

sys.path.insert(0, '/workspaces/nam-box/lilv/bindings/python')
import lilv

# Load LV2 atom helper functions (from lv2/include/lv2/atom/util.h)
def lv2_atom_pad_size(size):
    return (size + 7) & ~7

def lv2_atom_total_size(atom):
    return ctypes.sizeof(ctypes.c_uint32) * 2 + atom.contents.size

# LV2 URID Map wrapper
class URIDMapper:
    """Maps URIs to URIDs using the host's symap."""
    
    def __init__(self, handle):
        # In real implementation, get this from jalv's symap via shared memory
        # or use a fixed mapping established at startup
        pass

def build_patch_set_atom(model_path: str, urid_map: dict) -> bytes:
    """
    Construct binary LV2 atom for patch:Set with atom:Path.
    
    Args:
        model_path: Absolute path to the .nam file
        urid_map: Dict of URID values (must match host's symap)
    
    Returns:
        Complete binary atom ready for atom:eventTransfer protocol
    """
    # Ensure null-terminated
    path_bytes = model_path.encode('utf-8')
    if not path_bytes.endswith(b'\x00'):
        path_bytes += b'\x00'
    path_len = len(path_bytes)
    
    buf = bytearray()
    
    # LV2_Atom_Object header + body
    # atom.size, atom.type (patch_Set), then body: id, otype
    buf.extend(struct.pack('<I', 8 + 16 + 4 + path_len))  # Total body size
    buf.extend(struct.pack('<I', urid_map['patch_Set']))    # type = patch_Set URID
    
    buf.extend(struct.pack('<I', 0))                         # id = 0 (blank)
    buf.extend(struct.pack('<I', urid_map['patch_Set']))      # otype = patch_Set URID
    
    # LV2_Atom_Property for patch:property -> model_Path URID
    # key, context, then value atom
    buf.extend(struct.pack('<I', urid_map['patch_property']))  # key
    buf.extend(struct.pack('<I', 0))                            # context = 0
    buf.extend(struct.pack('<I', 4))                           # value.size = 4 (URID)
    buf.extend(struct.pack('<I', urid_map['atom_URID']))       # value.type = atom_URID
    buf.extend(struct.pack('<I', urid_map['model_Path']))      # URID body
    
    # Pad to 8 bytes (URID value is 4 bytes + 4 bytes padding)
    buf.extend(b'\x00' * 4)
    
    # LV2_Atom_Property for patch:value -> path string
    buf.extend(struct.pack('<I', urid_map['patch_value']))     # key
    buf.extend(struct.pack('<I', 0))                            # context = 0
    buf.extend(struct.pack('<I', path_len - 1))                 # value.size (excludes null)
    buf.extend(struct.pack('<I', urid_map['atom_Path']))       # value.type = atom_Path
    buf.extend(path_bytes)                                      # Path string
    
    # Pad to 8 bytes
    padding = 8 - ((16 + path_len) % 8) if (16 + path_len) % 8 != 0 else 0
    buf.extend(b'\x00' * padding)
    
    return bytes(buf)


# Example: Using lilv to discover and introspect the plugin
def discover_nam_plugin():
    """Find the NAM plugin and its property controls."""
    world = lilv.World()
    world.load_all()
    
    plugin_uri = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
    plugins = world.get_all_plugins()
    plugin = plugins.get(plugin_uri)
    
    if not plugin:
        print(f"Plugin {plugin_uri} not found")
        return None
    
    # Find the control input port (for atom messages)
    control_port = plugin.get_port_by_designation(
        "http://lv2plug.in/ns/lv2core#InputPort",
        "http://lv2plug.in/ns/lv2core#control"
    )
    
    print(f"Control port index: {control_port.get_index()}")
    print(f"Control port symbol: {control_port.get_symbol()}")
    
    # The model property is exposed as patch:writable
    from lilv import Namespace
    patch_ns = Namespace(world, "http://lv2plug.in/ns/ext/patch#")
    
    model_prop_uri = "http://github.com/mikeoliphant/neural-amp-modeler-lv2#model"
    is_writable = world.ask(
        plugin_uri,
        "http://lv2plug.in/ns/ext/patch#writable",
        model_prop_uri
    )
    
    print(f"Model property writable: {is_writable}")
    
    return plugin


def main():
    """Demonstrate the atom construction process."""
    print("Building atom for NAM model control...")
    
    # This is what the URID values would look like after mapping
    # In reality, you need to get these from the running host's symap
    example_urid_map = {
        'patch_Set': 100,          # Actual value from symap_map(LV2_PATCH__Set)
        'patch_property': 101,     # symap_map(LV2_PATCH__property)
        'patch_value': 102,        # symap_map(LV2_PATCH__value)
        'atom_Path': 200,          # symap_map(LV2_ATOM__Path)
        'atom_URID': 201,          # symap_map(LV2_ATOM__URID)
        'model_Path': 300,         # symap_map("...#model")
    }
    
    # Build the atom message
    path = "/opt/nam/models/test.nam"
    atom = build_patch_set_atom(path, example_urid_map)
    
    print(f"Model path: {path}")
    print(f"Atom size: {len(atom)} bytes")
    print(f"Atom hex: {atom.hex()}")
    
    # To actually send this, you would:
    # 1. Instantiate the plugin with lilv
    # 2. Connect to JACK
    # 3. Write the atom to the control port's ring buffer
    # 4. The plugin's process() function would receive it via LV2_ATOM_SEQUENCE_FOREACH


if __name__ == "__main__":
    main()


## Alternative: Non-blocking FIFO Control (Recommended for Existing jalv)

Since modifying jalv is invasive, a practical compromise is to use a polling FIFO approach. jalv can check for new commands without a full reload:

### C Extension to jalv (read_model_fifo.c)

```c
// Add to jalv_update() cycle to check for model changes
static void
check_model_changes(Jalv* jalv)
{
    static int fd = -1;
    static char path[1024] = {0};
    
    if (fd < 0) {
        fd = open("/var/nam/model_change.fifo", O_RDONLY | O_NONBLOCK);
        if (fd < 0) {
            // Create FIFO if it doesn't exist
            if (mkfifo("/var/nam/model_change.fifo", 0666) == 0) {
                fd = open("/var/nam/model_change.fifo", O_RDONLY | O_NONBLOCK);
            }
        }
        if (fd < 0) return;
    }
    
    // Check for new path
    ssize_t n = read(fd, path, sizeof(path) - 1);
    if (n > 0) {
        path[n] = '\0';
        
        // Strip newline
        char* nl = strchr(path, '\n');
        if (nl) *nl = '\0';
        
        // Send patch:Set message
        ControlID* control = jalv_control_by_symbol(jalv, "model");
        if (control && control->type == PROPERTY) {
            jalv_set_control(jalv, control, strlen(path) + 1, 
                           jalv->urids.atom_Path, path);
        }
    }
}
```

### Using the FIFO from Python

```python
def send_model_change(model_path: str) -> None:
    """Send a model change to jalv without restarting."""
    # This appears instantaneous to the user - no restart needed
    # jalv polls the FIFO on each update cycle
    fifo_path = "/var/nam/model_change.fifo"
    
    # Ensure FIFO exists
    import os
    if not os.path.exists(fifo_path):
        os.mkfifo(fifo_path)
    
    # Write to FIFO (will block if jalv not running)
    with open(fifo_path, 'w') as f:
        f.write(model_path + '\n')
```

This approach requires minimal jalv modification (just add the `check_model_changes()` call to `jalv_update()`) and gives true real-time control without state file reloading.

## Related Files

- [`jalv/src/jalv.c`](../jalv/src/jalv.c) - Main jalv implementation, `jalv_set_control()`
- [`jalv/src/control.c`](../jalv/src/control.c) - ControlID creation for properties
- [`neural-amp-modeler-lv2/src/nam_plugin.cpp`](../neural-amp-modeler-lv2/src/nam_plugin.cpp) - Plugin patch:Set handling
- [`neural-amp-modeler-lv2/src/nam_plugin.h`](../neural-amp-modeler-lv2/src/nam_plugin.h) - Plugin definition
- [`lv2/include/lv2/patch/patch.h`](../lv2/include/lv2/patch/patch.h) - Patch extension URIDs
- [`lv2/include/lv2/atom/forge.h`](../lv2/include/lv2/atom/forge.h) - Atom forge API
- [`neural-amp-modeler-lv2/resources/neural_amp_modeler.ttl.in`](../neural-amp-modeler-lv2/resources/neural_amp_modeler.ttl.in) - Plugin TTL definition