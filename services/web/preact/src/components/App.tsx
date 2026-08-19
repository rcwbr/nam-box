import { useState } from 'preact/hooks'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PedalboardSelector from './PedalboardSelector'
import PedalboardView from './PedalboardView'
import FileUploadManager from './FileUploadManager'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      refetchInterval: 5000, // Polling every 5s
    },
  },
})

/**
 * Root application component with QueryClientProvider.
 * Manages selected pedalboard state and passes to children as props.
 */
export default function App() {
  const [selectedPedalboardId, setSelectedPedalboardId] = useState<number | null>(null)

  return (
    <QueryClientProvider client={queryClient}>
      <div class="space-y-4">
        <h1 class="text-2xl lcd-accent tracking-widest uppercase">Effects & Pedalboards</h1>
        <div class="lcd-divider"></div>

        <PedalboardSelector
          selectedId={selectedPedalboardId}
          onSelect={setSelectedPedalboardId}
        />

        <div class="border-t-2 border-lcd-300"></div>

        <PedalboardView pedalboardId={selectedPedalboardId} />

        <div class="border-t-2 border-lcd-300"></div>

        <FileUploadManager />
      </div>
    </QueryClientProvider>
  )
}