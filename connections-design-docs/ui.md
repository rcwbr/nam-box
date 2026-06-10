# UI Design: Directional Port Connection System

## Context
Design a UI component for managing connections between input and output "ports" where:
- Ports have directionality (outputs can only connect to inputs)
- Some ports are grouped into units containing any number of input/output ports (shown in a container)
- Units with mixed I/O show both types with the implied internal connection
- Units with only inputs or only outputs follow the same rule
- Small scale: ~10-50 ports visible at once
- Primary interaction: click sequence (click output, then input)
- Horizontal lists show connected ports from unimode units or orphan ports only

## Layout Structure

```
┌───────────────────────────────────────────┐
│  Horizontal Row: Connected Outputs        │
│  (unimode units or orphan ports)          │
│  [OUT1] [OUT2] ...                        │
├───────────────────────────────────────────┤
│                                           │
│  Center Area: Mixed-Mode Units             │
│  (Units containing both input & output)    │
│  ┌─────────────────┐                     │
│  │  ● ○ ○          │                     │
│  │  Input Ports      │                     │
│  │  ...              │                     │
│  │  Pair Label     │                     │
│  │                 │                     │
│  │  ○ ● ●          │                     │
│  │  Output Ports     │                     │
│  │  ...              │                     │
│  └─────────────────┘                      │
│  ...                                      │
├───────────────────────────────────────────┤
│  Horizontal Row: Connected Inputs           │
│  (unimode units or orphan ports)           │
│  [IN1] [IN2] ...                          │
├───────────────────────────────────────────┤
│  Vertical List: Unconnected Units          │
│  (All units with no active connections)     │
│  ┌─────────────────┐                      │
│  │  ○ ○ ○       [+]│  + adds port to unit   │
│  │  Input Ports      │  (name click = rename) │
│  │  Unit A           │                      │
│  │  Output Ports       │                      │
│  └─────────────────┘                      │
│  ...                                      │
├───────────────────────────────────────────┤
│  [Create Unit] button                      │
│  (creates new unit with next clicked port)   │
└───────────────────────────────────────────┘
```

## Visual Design for Unit Containers

### Consistent Vertical Layout (All Boxes)
```
┌─────────────────────────────┐
│  [Port States]            │  ○ = unconnected, ● = connected
│  Input Ports (top)           │
│  Input1  Input2  Input3     │
│                             │
│  Unit Label                 │
│                             │
│  Output Ports (bottom)        │
│  Output1 Output2 Output3     │
└─────────────────────────────┘
```

### Connected Mixed-Mode Unit
```
┌─────────────────┐
│  ● ○ ○          │
│  Audio L/R In     │
│                 │
│  Audio Interface│
│                 │
│  ● ● ○          │
│  Audio L/R Out    │
└─────────────────┘
```

### Unimode Units (single type only)
- Units with ONLY inputs OR ONLY outputs: when connected, individual ports appear in horizontal rows
- When unconnected, these also appear in the unconnected vertical list (showing single-type ports in a simplified box)

## Core Interaction Patterns

### Creating Connections (Click Sequence)

**From Any Output Port:**
1. Click any output port (from orphan list, unconnected pair, or existing connection):
   - Output highlights to show it's the active source
   - Compatible inputs highlight as potential targets
2. Click a compatible input port:
   - Line draws connecting them
   - Both ports show connected state (●)
   - Port moves to connected outputs row if not already there

### Removing Connections
- **Click connection line**: removes connection, ports return to unconnected state
- **Keyboard shortcut**: Delete removes selected connection

### Removing Ports from Units
- **[Remove Port] button on unit box**: Activates remove-port mode
  - Next port clicked (anywhere) gets removed from its unit
  - Port returns to orphan list immediately
  - If no other ports remain in the unit, the unit disappears

### Creating and Editing Units
- **[Create Unit] button**: Activates create mode - next port click creates a new unit containing that port
- **Unit name click**: Activates inline rename mode (text input appears)
- **[+] button next to unit name**: Activates add-port mode - next port click adds that port to the existing unit