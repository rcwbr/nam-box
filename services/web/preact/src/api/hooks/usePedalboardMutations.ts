import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { Pedalboard, CreatePedalboardRequest, RenamePedalboardRequest } from '../types'

const API_BASE = '/api/effects'

/**
 * Create a new pedalboard.
 */
export function useCreatePedalboard() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (request: CreatePedalboardRequest): Promise<Pedalboard> => {
      const response = await fetch(`${API_BASE}/pedalboards`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      })
      if (!response.ok) throw new Error('Failed to create pedalboard')
      return response.json()
    },
    onSuccess: (newPedalboard) => {
      // Optimistically write the new pedalboard to the cache so consumers
      // (e.g. PedalboardSelector) see it immediately, avoiding a flash where
      // the selected pedalboard id exists but the cached data doesn't yet
      // contain that pedalboard — which triggers React controlled/uncontrolled
      // warnings on the Select component.
      queryClient.setQueryData(['pedalboards'], (old: Record<number, Pedalboard> | undefined) => {
        if (!old) return old
        return { ...old, [newPedalboard.id]: newPedalboard }
      })
      queryClient.invalidateQueries({ queryKey: ['pedalboards'] })
    },
  })
}

/**
 * Select a pedalboard as current.
 */
export function useSelectPedalboard() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: number): Promise<void> => {
      const response = await fetch(`${API_BASE}/pedalboards/${id}/select`, {
        method: 'PUT',
      })
      if (!response.ok) throw new Error('Failed to select pedalboard')
    },
    onSuccess: (_data, id) => {
      // Invalidate the specific pedalboard
      queryClient.invalidateQueries({ queryKey: ['pedalboard', id] })
      queryClient.invalidateQueries({ queryKey: ['pedalboard', 'current'] })
    },
  })
}

/**
 * Rename a pedalboard.
 */
export function useRenamePedalboard(pedalboardId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (request: RenamePedalboardRequest): Promise<Pedalboard> => {
      const response = await fetch(`${API_BASE}/pedalboards/${pedalboardId}/rename`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      })
      if (!response.ok) throw new Error('Failed to rename pedalboard')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedalboards'] })
      queryClient.invalidateQueries({ queryKey: ['pedalboard', pedalboardId] })
    },
  })
}

/**
 * Delete a pedalboard.
 */
export function useDeletePedalboard() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (pedalboardId: number): Promise<void> => {
      const response = await fetch(`${API_BASE}/pedalboards/${pedalboardId}`, {
        method: 'DELETE',
      })
      if (!response.ok) throw new Error('Failed to delete pedalboard')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedalboards'] })
      queryClient.invalidateQueries({ queryKey: ['pedalboard', 'current'] })
    },
  })
}