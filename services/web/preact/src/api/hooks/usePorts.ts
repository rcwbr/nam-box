import { useQuery } from '@tanstack/react-query'
import type { Port } from '../types'

const API_BASE = '/api/effects'

/**
 * Fetch all ports (system + effect) for a pedalboard.
 */
export function usePorts(pedalboardId: number) {
  return useQuery({
    queryKey: ['ports', pedalboardId],
    queryFn: async (): Promise<Port[]> => {
      const response = await fetch(`${API_BASE}/pedalboards/${pedalboardId}/ports`)
      if (!response.ok) throw new Error('Failed to load ports')
      return response.json()
    },
    staleTime: 5000,
  })
}
