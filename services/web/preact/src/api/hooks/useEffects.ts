import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { EffectInfo, EffectInstance, CreateEffectRequest } from '../types'

const API_BASE = '/api/effects'

/**
 * Fetch the catalog of all available effects.
 */
export function useEffects() {
  return useQuery({
    queryKey: ['effects'],
    queryFn: async (): Promise<EffectInfo[]> => {
      const response = await fetch(`${API_BASE}/effects`)
      if (!response.ok) throw new Error('Failed to load effects')
      return response.json()
    },
    staleTime: 30000, // Effects catalog rarely changes
  })
}

/**
 * Add an effect instance to a pedalboard.
 */
export function useAddEffect(pedalboardId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (request: CreateEffectRequest): Promise<EffectInstance> => {
      const response = await fetch(`${API_BASE}/pedalboards/${pedalboardId}/effects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      })
      if (!response.ok) throw new Error('Failed to add effect')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedalboard', pedalboardId] })
    },
  })
}

/**
 * Remove an effect instance from a pedalboard.
 */
export function useRemoveEffect(pedalboardId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (effectId: number): Promise<void> => {
      const response = await fetch(`${API_BASE}/pedalboards/${pedalboardId}/effects/${effectId}`, {
        method: 'DELETE',
      })
      if (!response.ok) throw new Error('Failed to remove effect')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedalboard', pedalboardId] })
    },
  })
}