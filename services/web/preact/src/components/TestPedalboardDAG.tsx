/**
 * Test harness for the real PedalboardDAG component.
 *
 * Renders PedalboardDAG directly with a known pedalboard ID, bypassing the
 * PedalboardSelector. Useful for verifying that the React Flow canvas renders
 * nodes/edges from the mock API server.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PedalboardDAG from './PedalboardDAG'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      retry: false,
    },
  },
})

export default function TestPedalboardDAG() {
  return (
    <QueryClientProvider client={queryClient}>
      <PedalboardDAG pedalboardId={1} />
    </QueryClientProvider>
  )
}
