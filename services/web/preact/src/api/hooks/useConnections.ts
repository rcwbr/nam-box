import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { Connection, CreateConnectionRequest } from '../types'

const API_BASE = '/api/effects'

/**
 * Create a connection between an output port and an input port.
 *
 * The connection maps to a DAG edge where:
 *   output_port_id → edge source (signal origin)
 *   input_port_id  → edge target (signal destination)
 */
export function useCreateConnection(pedalboardId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (request: CreateConnectionRequest): Promise<Connection> => {
      const response = await fetch(`${API_BASE}/pedalboards/${pedalboardId}/connections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      })
      if (!response.ok) throw new Error('Failed to create connection')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedalboard', pedalboardId] })
    },
  })
}

/**
 * Remove a connection. Invalidates the pedalboard query so edges re-render.
 */
export function useDeleteConnection(pedalboardId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (connectionId: number): Promise<void> => {
      const response = await fetch(
        `${API_BASE}/pedalboards/${pedalboardId}/connections/${connectionId}`,
        { method: 'DELETE' },
      )
      if (!response.ok) throw new Error('Failed to delete connection')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedalboard', pedalboardId] })
    },
  })
}
