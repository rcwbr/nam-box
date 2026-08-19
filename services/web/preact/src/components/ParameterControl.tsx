import { useSetParameter } from '../api/hooks/useParameters'
import type { Parameter, FileInfo } from '../api/types'
import Select from './Select'

interface ParameterControlProps {
  pedalboardId: number
  effectId: number
  paramName: string
  param: Parameter
  modelFiles?: FileInfo[]
}

/**
 * Generic parameter control that dispatches on parameter type.
 *
 * - `NumberParameter` (type='number') → slider + numeric readout
 * - `FilenameParameter` (type='filename') → dropdown of available model files
 */
export default function ParameterControl({
  pedalboardId,
  effectId,
  paramName,
  param,
  modelFiles,
}: ParameterControlProps) {
  const setParameterMutation = useSetParameter(pedalboardId, effectId, paramName)

  // Capture value before type narrowing for the fallback case below
  const paramValue = param.value

  if (param.type === 'number') {
    return (
      <div class="mt-1">
        <span class="text-lcd-400 text-2xs uppercase">{paramName}</span>
        <div class="flex items-center gap-2 mt-0.5">
          <input
            type="range"
            min={param.min}
            max={param.max}
            value={param.value}
            step="any"
            class="flex-1 lcd-input"
            onChange={(e) => {
              const target = e.target as HTMLInputElement
              setParameterMutation.mutate(parseFloat(target.value))
            }}
          />
          <span class="text-lcd-200 text-xs w-16 text-right tabular-nums">
            {param.value.toFixed(2)}
          </span>
        </div>
      </div>
    )
  }

  if (param.type === 'filename') {
    const currentPath = param.value
    const currentFile = modelFiles?.find((f) => f.path === currentPath) ?? null

    return (
      <div class="mt-1">
        <span class="text-lcd-400 text-2xs uppercase">{paramName}</span>
        <Select<FileInfo>
          value={currentFile}
          options={modelFiles ?? []}
          onChange={(file) => setParameterMutation.mutate(file.path)}
          placeholder={modelFiles === undefined ? 'Loading...' : (currentPath || 'Select model file...')}
          optionLabel={(file) => file.name}
          optionKey={(file) => file.name}
        />
      </div>
    )
  }

  // Fallback for unknown parameter types — read-only display
  return (
    <div class="flex items-center gap-2">
      <span class="text-lcd-400 text-2xs uppercase w-24">{paramName}</span>
      <span class="text-lcd-200 text-xs">{String(paramValue)}</span>
    </div>
  )
}
