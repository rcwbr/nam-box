import { useQuery } from '@tanstack/react-query'
import type { Pedalboard } from '../types'

const API_BASE = '/api/effects'

/**
 * Fetch a specific pedalboard by ID.
 */
export function usePedalboard(pedalboardId: number) {
  return useQuery({
    queryKey: ['pedalboard', pedalboardId],
    queryFn: async (): Promise<Pedalboard> => {
      const response = await fetch(`${API_BASE}/pedalboards/${pedalboardId}`)
      if (!response.ok) throw new Error('Failed to load pedalboard')
      return response.json()
    },
    staleTime: 3000,
  })
}