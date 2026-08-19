/**
 * Port utilities — construct backend port IDs and classify ports.
 *
 * Backend port ID format (see mod-api connections.py / ports.py / mod_host_client.py):
 *   System: `system:${name}`                    (e.g. "system:capture_1")
 *   Effect: `effect_${effect_instance_id}:${name}` (e.g. "effect_0:input")
 */

import type { Port } from '../api/types'

const INPUT_PORT_TYPES = new Set(['input', 'midi_in'])
const OUTPUT_PORT_TYPES = new Set(['output', 'midi_out'])

export interface PortGroups {
  inputs: Port[]
  outputs: Port[]
}

/** Split a port list into input and output groups based on port type. */
export function classifyPorts(ports: Port[]): PortGroups {
  const inputs: Port[] = []
  const outputs: Port[] = []
  for (const port of ports) {
    if (INPUT_PORT_TYPES.has(port.type)) inputs.push(port)
    else if (OUTPUT_PORT_TYPES.has(port.type)) outputs.push(port)
  }
  return { inputs, outputs }
}

/**
 * Construct the backend port ID string from a Port object.
 * This format matches what the mod-api stores in Connection.input_port_id
 * / output_port_id and what mod-host expects for connect/disconnect.
 */
export function portId(port: Port): string {
  if (port.owner_type === 'system') {
    return `system:${port.name}`
  }
  return `effect_${port.effect_instance_id}:${port.name}`
}

export type HandleType = 'source' | 'target'

/**
 * Determine whether a port acts as a signal source ('source') or
 * destination ('target') in the pedalboard DAG.
 *
 * Signal-flow semantics:
 *   Effect ports: "input" ports receive → target; "output" ports send → source.
 *   System ports: the type reflects JACK's physical direction, which is
 *     INVERTED from the pedalboard signal flow:
 *       system:capture_* (type "input")  → signal ORIGIN   → 'source'
 *       system:playback_* (type "output") → signal TERMINAL → 'target'
 */
export function portHandleType(port: Port): HandleType {
  const isEffect = port.owner_type === 'effect'
  const isOutputType = OUTPUT_PORT_TYPES.has(port.type)

  if (isEffect) {
    // Effect: output → source, input → target
    return isOutputType ? 'source' : 'target'
  }
  // System: capture (input type) → source, playback (output type) → target (inverted)
  return isOutputType ? 'target' : 'source'
}

/**
 * Map a backend port ID to the React Flow node that owns it.
 *
 * System ports are individual nodes whose React Flow node ID IS the port ID
 * (e.g. "system:capture_1").  Effect ports belong to the effect node
 * "effect-{id}" (e.g. "effect_0:input" → "effect-0").
 */
export function nodeIdForPortId(pid: string): string {
  if (pid.startsWith('effect_')) {
    const rest = pid.slice('effect_'.length) // "0:input"
    const effectId = rest.split(':')[0]       // "0"
    return `effect-${effectId}`
  }
  // system ports: the port ID is also the node ID
  return pid
}
