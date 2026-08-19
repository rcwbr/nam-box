import { useQuery } from '@tanstack/react-query'
import type { FileInfo } from '../types'

/**
 * Load NAM model files for selection in effect parameters.
 * Uses /api/model/all endpoint (not part of mod-api).
 */
export function useModelFiles() {
  return useQuery({
    queryKey: ['model-files'],
    queryFn: async (): Promise<FileInfo[]> => {
      const response = await fetch('/api/model/all')
      if (!response.ok) throw new Error('Failed to load model files')
      return response.json()
    },
    staleTime: 30000,
  })
}