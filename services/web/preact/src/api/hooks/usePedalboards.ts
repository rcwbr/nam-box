import { useQuery } from '@tanstack/react-query'
import type { Pedalboard } from '../types'

const API_BASE = '/api/effects'

/**
 * Fetch all pedalboards list.
 */
export function usePedalboards() {
  return useQuery({
    queryKey: ['pedalboards'],
    queryFn: async (): Promise<Record<number, Pedalboard>> => {
      const response = await fetch(`${API_BASE}/pedalboards`)
      if (!response.ok) throw new Error('Failed to load pedalboards')
      return response.json()
    },
    staleTime: 5000, // 5 second cache
  })
}

/**
 * Fetch the current pedalboard (null if none selected).
 */
export function useCurrentPedalboard() {
  return useQuery({
    queryKey: ['pedalboards', 'current'],
    queryFn: async (): Promise<Pedalboard | null> => {
      const response = await fetch(`${API_BASE}/pedalboards/current`)
      if (!response.ok) throw new Error('Failed to load current pedalboard')
      return response.json()
    },
    staleTime: 3000,
  })
}