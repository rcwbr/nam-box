import { Handle, Position } from '@xyflow/react'
import type { Port } from '../../api/types'
import { portId, portHandleType, type HandleType } from '../../lib/portUtils'

export interface SystemPortNodeData {
  port: Port
  onClick?: (portId: string, handleType: HandleType) => void
  isSelected?: boolean
}

/**
 * Renders a single system I/O port (capture/playback) as a small circular node.
 *
 * System ports are pinned to the top (inputs/capture) or bottom (outputs/playback)
 * of the React Flow canvas by the parent PedalboardDAG — this component only
 * draws the circle + label and exposes a Handle for edges to attach.
 */
export default function SystemPortNode({ data }: { data: SystemPortNodeData }) {
  const { port, onClick, isSelected = false } = data
  const pid = portId(port)
  const handleType = portHandleType(port)

  // Position the handle so edges connect naturally:
  //   source (capture) handle at Bottom → edges flow downward to effects
  //   target (playback) handle at Top    → edges flow upward from effects
  const handlePosition = handleType === 'source' ? Position.Bottom : Position.Top

  return (
    <div
      class={`
        relative flex flex-col items-center gap-0.5 cursor-pointer
        transition-shadow
        ${isSelected ? 'ring-2 ring-lcd-300 shadow-[0_0_10px_rgba(234,179,8,0.7)]' : ''}
      `}
      onClick={(e) => {
        e.stopPropagation()
        onClick?.(pid, handleType)
      }}
    >
      <Handle type={handleType} position={handlePosition} id={pid} isConnectable={false} />
      <div class="w-6 h-6 rounded-full bg-lcd-400 shadow-[0_0_8px_rgba(234,179,8,0.5)]" />
      <span class="text-lcd-300 text-2xs uppercase">{port.name}</span>
    </div>
  )
}
