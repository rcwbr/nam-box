import type { Port } from '../api/types'

interface PortViewProps {
  port: Port
}

/**
 * Renders a single port (system or effect) as a labeled circle.
 * Static display only — no interactivity.
 */
export default function PortView({ port }: PortViewProps) {
  return (
    <div class="flex flex-col items-center gap-0.5">
      <div class="w-5 h-5 rounded-full bg-lcd-400" />
      <span class="text-lcd-300 text-2xs uppercase">{port.name}</span>
    </div>
  )
}
