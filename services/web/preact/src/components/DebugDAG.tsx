/**
 * Debug test page that logs React Flow state to the page for inspection.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PedalboardDAG from '../components/PedalboardDAG'
import { usePedalboard } from '../api/hooks/usePedalboard'
import { usePorts } from '../api/hooks/usePorts'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      retry: false,
    },
  },
})

export default function DebugDAG() {
  return (
    <QueryClientProvider client={queryClient}>
      <PedalboardDAG pedalboardId={1} />
      <DebugPanel pedalboardId={1} />
    </QueryClientProvider>
  )
}

function DebugPanel({ pedalboardId }: { pedalboardId: number }) {
  const { data: pedalboard } = usePedalboard(pedalboardId)
  const { data: allPorts } = usePorts(pedalboardId)

  if (!pedalboard || !allPorts) return null

  return (
    <div style={{ position: 'fixed', top: 0, right: 0, width: '300px', background: '#111', color: '#0f0', padding: '10px', fontSize: '10px', zIndex: 9999, maxHeight: '100vh', overflow: 'auto' }}>
      <pre>
        {JSON.stringify({
          pedalboardId,
          effects: Object.keys(pedalboard.effects),
          connections: pedalboard.connections,
          allPorts: allPorts.map(p => ({
            id: p.name,
            owner: p.owner_type,
            effectId: p.effect_instance_id,
            type: p.type
          })),
        }, null, 2)}
      </pre>
    </div>
  )
}
