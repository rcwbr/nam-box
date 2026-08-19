import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { Parameter, SetParameterRequest, Pedalboard } from '../types'

const API_BASE = '/api/effects'

/**
 * Get all parameter values for an effect instance.
 */
export function useParameters(
  pedalboardId: number,
  effectId: number
) {
  return useQuery({
    queryKey: ['parameters', pedalboardId, effectId],
    queryFn: async (): Promise<Record<string, Parameter>> => {
      const response = await fetch(`${API_BASE}/pedalboards/${pedalboardId}/effects/${effectId}/parameters`)
      if (!response.ok) throw new Error('Failed to load parameters')
      return response.json()
    },
  })
}

/**
 * Set a parameter value with optimistic update.
 */
export function useSetParameter(
  pedalboardId: number,
  effectId: number,
  paramName: string
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (value: number | string): Promise<void> => {
      const response = await fetch(
        `${API_BASE}/pedalboards/${pedalboardId}/effects/${effectId}/parameters/${paramName}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ value } as SetParameterRequest),
        }
      )
      if (!response.ok) {
        const body = await response.text()
        throw new Error(`Failed to set parameter (${response.status}): ${body}`)
      }
    },
    onMutate: async (value) => {
      // Cancel ongoing queries
      await queryClient.cancelQueries({ queryKey: ['pedalboard', pedalboardId] })

      // Snapshot previous value
      const previous = queryClient.getQueryData<Pedalboard>(['pedalboard', pedalboardId])

      // Optimistically update pedalboard
      if (previous && previous.effects[effectId]) {
        queryClient.setQueryData(['pedalboard', pedalboardId], {
          ...previous,
          effects: {
            ...previous.effects,
            [effectId]: {
              ...previous.effects[effectId],
              parameters: {
                ...previous.effects[effectId].parameters,
                [paramName]: {
                  ...previous.effects[effectId].parameters[paramName],
                  value,
                } as Parameter,
              },
            },
          },
        })
      }

      return { previous }
    },
    onError: (_err, _value, context) => {
      // Rollback on error
      if (context?.previous) {
        queryClient.setQueryData(['pedalboard', pedalboardId], context.previous)
      }
    },
    onSettled: () => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: ['pedalboard', pedalboardId] })
    },
  })
}