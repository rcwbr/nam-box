# Controller Design: Port, Unit, and Connection Management

## Overview

The controller layer manages the state and logic for the directional port connection system, bridging the UI presentation layer with the backend API data model. It handles three core concerns: **ports** (individual connection points), **units** (port groupings), and **connections** (established links between outputs and inputs).

## Core Data Structures

### PortController
Manages individual port representations and their state:

```typescript
interface Port {
  name: string;
  direction: 'input' | 'output';
  is_physical: boolean;
  is_terminal: boolean;
  connection_id?: string | null;  // null if unconnected, string if connected
  unit_id?: string | null;       // null if orphan (not in any unit)
}
```

### UnitController
Manages port groupings and their derived properties:

```typescript
interface PortUnit {
  id: string;
  name: string;
  input_ports: Port[];    // Ports belonging to this unit (sorted)
  output_ports: Port[];   // Ports belonging to this unit (sorted)
  created_at: number;
  updated_at: number;
}
```

Derived properties computed at runtime:
- `is_unimode`: true if unit has only inputs OR only outputs (not both)
- `is_connected`: true if any port in the unit has an active connection
- `port_count`: total number of ports in the unit

### ConnectionController
Manages established connections between ports:

```typescript
interface Connection {
  id: string;
  output_port: string;  // Full port name
  input_port: string;   // Full port name
}
```

### ApplicationController
Root state container orchestrating all controllers:

```typescript
interface AppState {
  ports: Map<string, Port>;              // Keyed by full port name
  units: Map<string, PortUnit>;          // Keyed by unit id
  connections: Map<string, Connection>;  // Keyed by connection id
  active_output?: string | null;         // Currently selected output for connection
  create_mode: boolean;                 // Unit creation mode active flag
  add_port_mode: {                      // Add port to unit mode
    unit_id: string;
    active: boolean;
  } | null;
}
```

## State Management

### Initialization Flow

1. **Load Ports**: Fetch `/ports` endpoint, create Port objects for each result
2. **Load Units**: Fetch `/port-units` endpoint, populate units map
3. **Correlate Ports to Units**: For each port, assign `unit_id` based on matching `port_names` in units
4. **Load Connections**: Fetch `/connections`, assign connection references to ports
5. **Categorize Units**: Classify units as unimode/mixed-mode and connected/unconnected

### Derived State Computation

The controller maintains computed view state for UI rendering:

```typescript
// Ports categorized by connection state
const connected_outputs: Port[] = [];
const connected_inputs: Port[] = [];
const unconnected_ports: Port[] = [];

// Units categorized by mode and connection state
const connected_unimode_outputs: PortUnit[] = [];  // For horizontal row
const connected_unimode_inputs: PortUnit[] = [];   // For horizontal row
const unconnected_units: PortUnit[] = [];          // For vertical list
const mixed_mode_units: PortUnit[] = [];           // For center area
```

## UI Rendering Coordination

### Layout Section 1: Connected Outputs Row - Cytoscape Horizontal Layout
- **Source**: Connected output ports from unimode units and orphan output ports
- **Render**: Part of a shared cytoscape.js DAG rendered with horizontal list constraints
- **Visual**: Each port node positioned in a horizontal row (top), with ● state indicator, edges connect to nodes in sections 2/3

### Layout Section 2: Mixed-Mode Units (Center) - Cytoscape Grid Layout
- **Source**: All connected mixed-mode units, rendered as part of the shared DAG object
- **Render**: cytoscape.js DAG with grid layout configuration (center positioning)
- **Visual**: 
  - Mixed-mode unit nodes display container box with inputs (top), label (center), outputs (bottom)
  - Connected ports shown with ● state indicators
  - Edges draw connection lines with directional arrows (output → input)
- **Note**: Shares a single DAG object with Sections 1 and 3, but with different layout constraints to position nodes in the center area

### Cytoscape DAG Assembly for Sections 1-3
- All three horizontal/center sections are rendered from a single DAG object passed to cytoscape.js
- Each node includes a `layout_section` property to guide positioning
- Uses cytoscape.js standard elements format (nodes/edges with `data` objects containing `id`, `source`/`target`)
- The controller assembles nodes and edges as follows:

```typescript
interface DagNode {
  data: {
    id: string;                    // Unique node identifier
    label: string;                 // Display label
    type: 'unit' | 'orphan-port';  // Node type
    layout_section: 'top-row' | 'bottom-row' | 'center-grid';
    // For units - the ports are rendered inside the container
    ports?: {
      inputs: Port[];
      outputs: Port[];
    };
    // For orphan ports
    port?: Port;
  };
}

interface DagEdge {
  data: {
    id: string;
    source: string;  // Source node id (output)
    target: string;  // Target node id (input)
  };
}

interface DagGraph {
  nodes: DagNode[];
  edges: DagEdge[];
}

// Controller assembles the complete DAG for cytoscape rendering
function assembleDagGraph(): DagGraph {
  const nodes: DagNode[] = [];
  const edges: DagEdge[] = [];
  
  // Add mixed-mode unit nodes to center-grid
  for (const [unitId, unit] of state.units) {
    const classification = classifyUnit(unit);
    if (classification.mode === 'mixed') {
      nodes.push({
        data: {
          id: `unit-${unitId}`,
          label: unit.name,
          type: 'unit',
          layout_section: 'center-grid',
          ports: {
            inputs: unit.input_ports,
            outputs: unit.output_ports
          }
        }
      });
    }
  }
  
  // Add connected ports from unimode units to top/bottom rows
  for (const [unitId, unit] of state.units) {
    const classification = classifyUnit(unit);
    if (classification.is_unimode && unit.is_connected) {
      // Add individual port nodes for unimode units
      for (const port of unit.output_ports) {
        nodes.push({
          data: {
            id: `port-${port.name}`,
            label: port.name,
            type: 'orphan-port',
            layout_section: 'top-row',
            port
          }
        });
      }
      for (const port of unit.input_ports) {
        nodes.push({
          data: {
            id: `port-${port.name}`,
            label: port.name,
            type: 'orphan-port',
            layout_section: 'bottom-row',
            port
          }
        });
      }
    }
  }
  
  // Add orphan port nodes (connected ports not in any unit)
  for (const [portName, port] of state.ports) {
    if (!port.unit_id && port.connection_id) {
      const section = port.direction === 'output' ? 'top-row' : 'bottom-row';
      nodes.push({
        data: {
          id: `port-${portName}`,
          label: portName,
          type: 'orphan-port',
          layout_section: section,
          port
        }
      });
    }
  }
  
  // Add edges for ALL connections
  for (const [connId, conn] of state.connections) {
    const sourcePort = state.ports.get(conn.output_port);
    const targetPort = state.ports.get(conn.input_port);
    
    // Determine node ids based on whether ports are in units
    const sourceNode = sourcePort?.unit_id
      ? `unit-${sourcePort.unit_id}`
      : `port-${conn.output_port}`;
    
    const targetNode = targetPort?.unit_id
      ? `unit-${targetPort.unit_id}`
      : `port-${conn.input_port}`;
    
    edges.push({
      data: {
        id: `conn-${connId}`,
        source: sourceNode,
        target: targetNode
      }
    });
  }
  
  return { nodes, edges };
}

// Cytoscape layout configuration - uses custom positioning based on layout_section
const cytoscapeLayoutConfig = {
  name: 'grid',
  rows: 3,
  cols: undefined, // auto
  // Cytoscape's grid layout will respect node positions if pre-set
  // Or we can use the 'rows' constraint to arrange in horizontal bands
  animate: false,
  padding: 10,
  // Alternative: use 'preset' layout with manually positioned nodes
  // based on layout_section: top-row (y=50), center (y=300), bottom-row (y=550)
  
  // For the cytoscape instance to render edges:
  // cy.elements().style('line-color', '#00ff9d').style('target-arrow-color', '#00ff9d')
  // .style('target-arrow-shape', 'triangle').style('curve-style', 'bezier')
};

// Cytoscape instance integration
function renderDagGraph(dagGraph: DagGraph): void {
  // Convert to cytoscape elements format
  const elements = {
    nodes: dagGraph.nodes.map(n => ({ data: n.data })),
    edges: dagGraph.edges.map(e => ({ data: e.data }))
  };
  
  // Pass to cytoscape instance
  // cy.json({ elements });
  // cy.layout(cytoscapeLayoutConfig).run();
}
```

### Layout Section 3: Connected Inputs Row - Cytoscape Horizontal Layout
- **Source**: Connected input ports from unimode units and orphan input ports
- **Render**: Part of a shared cytoscape.js DAG rendered with horizontal list constraints (bottom row)
- **Visual**: Each port node positioned in a horizontal row (bottom), with ● state indicator, edges connect from nodes in sections 1/2

### Layout Section 4: Unconnected Units (Vertical List)
- **Source**: Units with no active connections
- **Render**: Vertical list of simplified unit containers
- **Visual**: Compact box showing ○ for all unconnected ports

## Interaction Handlers

### Creating Connections

```typescript
function handlePortClick(portName: string): void {
  const port = state.ports.get(portName);
  
  if (state.active_output) {
    // Second click - attempt connection to input
    if (canConnect(state.active_output, portName)) {
      createConnection(state.active_output, portName);
      state.active_output = null;
    }
  } else if (port.direction === 'output' && !port.connection_id) {
    // First click - select output for new connection
    state.active_output = portName;
  }
}
```

**Validation Rules:**
- Only outputs can be connection sources
- Only inputs can be connection targets
- Prevent duplicate connections between same port pair
- Highlight compatible inputs when output is selected

### Removing Connections

```typescript
function handleConnectionClick(connectionId: string): void {
  const conn = state.connections.get(connectionId);
  removeConnection(conn.id);
}
```

### Creating Units

When `[Create Unit]` is clicked:
1. Enter create mode (`state.create_mode = true`)
2. Next port click triggers unit creation with inferred name

**Name Inference Algorithm:**

```typescript
function inferUnitName(portName: string): string {
  // Extract base name from full port identifier
  // Handle patterns like:
  // - "system:capture_1" → "System Capture"
  // - "mod-host-01:audio_out_1" → "Audio"
  // - "interface:input_L" → "Interface"
  
  const patterns = [
    /(\d+)$/,           // Strip trailing numbers
    /(_in|_out)$/,      // Strip _in/_out suffixes
    /(_input|_output)$/, // Strip _input/_output suffixes
    /(In|Out)$/,        // Strip In/Out suffixes
    /(L|R)$/,          // Strip L/R channel suffixes
    /^system:(.+)$/,    // Handle system: prefix
    /^(.+?)[:-_].*$/,  // Split on first separator
  ];
  
  let name = portName;
  for (const pattern of patterns) {
    name = name.replace(pattern, '$1') || name;
  }
  
  // Handle prefix removal
  if (name.startsWith('system:')) {
    name = name.replace('system:', '');
  }
  
  // Convert snake_case to Title Case
  name = name
    .replace(/_/g, ' ')
    .replace(/-/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
  
  return name.trim();
}
```

### Adding Ports to Units

When `[+]` button is clicked on a unit:
1. Store target `unit_id` in `state.add_port_mode`
2. Next port click adds port to unit
3. Port is removed from orphan list and added to unit
4. Unit classification may change (e.g., unconnected → connected)

### Renaming Units

When unit label is clicked:
1. Enable inline text input for the unit name
2. On commit, call `PUT /port-units/{unit_id}/name`
3. Update local state on success

## Port-Unit Classification Logic

### Determining Unit Mode

```typescript
function classifyUnit(unit: PortUnit): { is_unimode: boolean; mode: 'input' | 'output' | 'mixed' } {
  const has_inputs = unit.input_ports.length > 0;
  const has_outputs = unit.output_ports.length > 0;
  
  if (has_inputs && has_outputs) {
    return { is_unimode: false, mode: 'mixed' };
  }
  return { 
    is_unimode: true, 
    mode: has_outputs ? 'output' : 'input' 
  };
}
```

### Moving Between Sections

When a unit's state changes (ports added/removed/connected):
1. Re-classify the unit
2. Remove from old section arrays
3. Add to appropriate new section arrays
4. Trigger UI re-render

## API Integration

### Sync Strategies

**Full Refresh (on app load):**
```typescript
async function loadInitialState(): Promise<void> {
  const [ports, units, connections] = await Promise.all([
    api.getPorts(),
    api.getPortUnits(),
    api.getConnections()
  ]);
  // Populate state maps
  computeDerivedState();
}
```

**Incremental Updates (WebSocket or polling):**
- Listen for port/unit/connection events
- Apply targeted updates to state maps
- Recompute only affected derived state

### Error Handling

- **Connection failure**: Show error state on affected ports/units
- **Validation error**: Reject interaction, show tooltip with reason
- **API error on unit creation**: Exit create mode, notify user

## UI Component Interface

### Controller Hooks for UI Components

```typescript
// For Port components
function usePort(portName: string) {
  return {
    port: state.ports.get(portName),
    isConnected: !!state.ports.get(portName)?.connection_id,
    isHighlighted: state.active_output === portName,
    onClick: () => handlePortClick(portName)
  };
}

// For Unit components
function useUnit(unitId: string) {
  const unit = state.units.get(unitId);
  return {
    unit,
    classification: classifyUnit(unit),
    portsByDirection: {
      inputs: unit.input_ports,
      outputs: unit.output_ports
    },
    onAddPort: () => enterAddPortMode(unitId),
    onRename: (name) => renameUnit(unitId, name)
  };
}
```

## State Persistence Considerations

The controller does NOT persist state directly - it reads/writes through the API layer which handles `state.json` persistence. The controller's responsibility is:
1. Maintaining consistent in-memory state
2. Computing derived views for efficient rendering
3. Coordinating CRUD operations with appropriate API endpoints

## Event Flow Summary

```
User Click → Controller Handler → API Request → State Update → Assemble DAG → UI Re-render

1. Click output port:
   → Set active_output
   → Highlight compatible inputs
   
2. Click input port (with active_output):
   → Create connection
   → Clear active_output
   → Update port connection_ids
   → assembleDagGraph() recomputes node/edge sets
   
3. Click connection line:
   → Remove connection
   → Clear port connection_ids
   → assembleDagGraph() recomputes node/edge sets
   
4. Create Unit button:
   → Enter create_mode
   
5. Click port (in create_mode):
   → Infer name from port
   → POST /port-units
   → Add port to new unit
   → assembleDagGraph() recomputes node/edge sets
   
6. [+] Add port:
   → Enter add_port_mode
   
7. Click orphan port (in add_port_mode):
   → POST /port-units/{id}/ports/{port}
   → Update unit membership
   → assembleDagGraph() recomputes node/edge sets
```

### DAG Assembly Trigger Points
The DAG must be reassembled whenever:
- A connection is created or removed
- A port is added to or removed from a unit
- A unit's connection state changes (any port in unit connects/disconnects)
- The initial state is loaded