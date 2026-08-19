import { Handle, Position } from '@xyflow/react'
import type { EffectInstance, EffectInfo, Port, Parameter, FileInfo } from '../../api/types'
import { portId, portHandleType, classifyPorts, type HandleType } from '../../lib/portUtils'
import ParameterControl from '../ParameterControl'

export interface EffectNodeData {
  pedalboardId: number
  effectId: number
  effect: EffectInstance
  catalogEntry?: EffectInfo
  modelFiles?: FileInfo[]
  onPortClick?: (portId: string, handleType: HandleType) => void
  selectedPortId?: string | null
  onRemoveEffect?: (effectId: number) => void
}

interface PortHandleProps {
  port: Port
  position: Position
  isSelected: boolean
  onClick: () => void
}

/**
 * A single port handle rendered inside an effect node.
 * The invisible <Handle> anchors React Flow edges; the visible circle
 * is what the user clicks for click-to-connect.
 */
function PortHandle({ port, position, isSelected, onClick }: PortHandleProps) {
  const pid = portId(port)
  const handleType = portHandleType(port)

  return (
    <div
      class="relative flex flex-col items-center cursor-pointer"
      onClick={(e) => {
        e.stopPropagation()
        onClick()
      }}
    >
      <Handle
        type={handleType}
        position={position}
        id={pid}
        isConnectable={false}
      />
      <div
        class={`
          w-5 h-5 rounded-full bg-lcd-400
          transition-all
          ${isSelected ? 'ring-2 ring-lcd-300 shadow-[0_0_10px_rgba(234,179,8,0.8)]' : 'shadow-[0_0_6px_rgba(234,179,8,0.4)]'}
        `}
      />
    </div>
  )
}

/**
 * Effect instance node for the pedalboard DAG.
 *
 * Renders the full effect card — name, parameter controls, delete button —
 * with input port handles at the top edge and output port handles at the
 * bottom edge. The node is non-draggable (pinned in a static column by
 * PedalboardDAG).
 */
export default function EffectNode({ data }: { data: EffectNodeData }) {
  const {
    pedalboardId,
    effectId,
    effect,
    catalogEntry,
    modelFiles,
    onPortClick,
    selectedPortId,
    onRemoveEffect,
  } = data

  const { inputs: inputPorts, outputs: outputPorts } = classifyPorts(effect.ports ?? [])

  const handlePortClick = (port: Port) => {
    const pid = portId(port)
    const handleType = portHandleType(port)
    onPortClick?.(pid, handleType)
  }

  return (
    <div class="p-2 bg-black border-2 border-lcd-400 rounded-sm space-y-2 min-w-[200px]">
      {/* Input port handles — top edge of the node */}
      {inputPorts.length > 0 && (
        <div class="flex justify-center gap-3">
          {inputPorts.map((port) => (
            <PortHandle
              key={portId(port)}
              port={port}
              position={Position.Top}
              isSelected={selectedPortId === portId(port)}
              onClick={() => handlePortClick(port)}
            />
          ))}
        </div>
      )}

      {/* Header: effect name + remove button */}
      <div class="flex items-center justify-between">
        <div>
          <p class="text-lcd-200 font-bold text-xs">
            {catalogEntry?.name ?? effect.name ?? 'Unknown Effect'}
          </p>
          <p class="text-lcd-400 text-xs">ID: {effect.id}</p>
        </div>
        <button
          class="text-lcd-300 hover:text-lcd-200 text-xs"
          onClick={() => onRemoveEffect?.(effectId)}
        >
          X
        </button>
      </div>

      <div class="border-t-2 border-lcd-300"></div>

      {/* Parameter controls (sliders / dropdowns) */}
      {Object.keys(effect.parameters).length > 0 && (
        <div class="mt-1 space-y-1">
          {Object.entries(effect.parameters).map(([name, param]) => (
            <ParameterControl
              key={name}
              pedalboardId={pedalboardId}
              effectId={effectId}
              paramName={name}
              param={param as Parameter}
              modelFiles={modelFiles ?? undefined}
            />
          ))}
        </div>
      )}

      {/* Output port handles — bottom edge of the node */}
      {outputPorts.length > 0 && (
        <div class="flex justify-center gap-3">
          {outputPorts.map((port) => (
            <PortHandle
              key={portId(port)}
              port={port}
              position={Position.Bottom}
              isSelected={selectedPortId === portId(port)}
              onClick={() => handlePortClick(port)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
