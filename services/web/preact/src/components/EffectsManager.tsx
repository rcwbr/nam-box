import { createContext } from 'preact'
import { useContext, useEffect, useState } from 'preact/hooks';
import {
  Button,
  Dialog,
  DialogBackdrop,
  DialogPanel,
  DialogTitle,
} from '@headlessui/react'

import { ActiveEffectsContext, SetPatchContext } from './ModSocket';
import { PedalboardInfoContext } from './PedalboardManager';
import type { ActiveEffect } from './types';

const NAM_PLUGIN_URI = 'http://github.com/mikeoliphant/neural-amp-modeler-lv2';
const NAM_MODEL_PROPERTY = `${NAM_PLUGIN_URI}#model`;

interface FileInfo {
  name: string
  size: number
  path: string
}

interface Effect {
  uri: string
  name: string
  brand: string
  label: string
  comment: string
  buildEnvironment: string
  category: string[]
  microVersion: number
  minorVersion: number
  release: number
  builder: number
  licensed: number
  iotype: number
  gui?: {
    resourcesDirectory: string
    screenshot: string
    thumbnail: string
  }
}

const EffectsContext = createContext<Array<Effect>>([])

export default function EffectsManager() {
  const [effectsState, setEffectsState] = useState<Array<Effect>>([])
  const [addEffectOpen, setAddEffectOpen] = useState<boolean>(false)
  const [modelFilesState, setModelFilesState] = useState<Array<FileInfo>>([])
  const activeEffectContext = useContext(ActiveEffectsContext)
  const pedalboardInfo = useContext(PedalboardInfoContext)
  const setPatch = useContext(SetPatchContext)

  const loadModelFiles = async () => {
    const response = await fetch('/api/model/all')
    if (!response.ok) throw new Error('Failed to load model files')
    const results = await response.json()
    setModelFilesState(results as FileInfo[])
  }

  // Set model file via patch_set websocket message
  const setModelFile = (id: string, modelName: string) => {
    if (!modelName || !setPatch) return
    const modelPath = `/opt/nam/models/${modelName}`
    // ID format from socket is /nam374, we send it as-is
    setPatch(id, NAM_MODEL_PROPERTY, 'p', modelPath)
  }

  // Set other parameters via the /parameter/set API (for non-model parameters)
  const setParameter = async (id: string, key: string, value: number) => {
    // ID from socket has format /nam374, API expects /graph/nam374
    const cleanId = id.startsWith('/') ? `/graph${id}` : `/graph/${id}`
    const response = await fetch('/api/effects/effect/parameter/set/', {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: `${NAM_PLUGIN_URI}${cleanId}/${key}/${value}`
    })
    if (!response.ok) throw new Error(`Failed to set parameter for ${id}`)
  }

  const addEffect = async (uri: string): Promise<string> => {
    // Use 'nam' as prefix for NAM effects to be consistent with the model setting
    const instance = isNamEffect(uri) ? `nam${Date.now() % 1000}` : Math.floor((Math.random() * (16 ** 8))).toString(16)
    console.log(`Adding effect: instance=${instance}, uri=${uri}`)
    const response = await fetch(`/api/effects/effect/add/${instance}?uri=${encodeURIComponent(uri)}`)
    if (!response.ok) {
      console.error(`Failed to add effect ${uri}:`, response.status, response.statusText)
      throw new Error(`Failed to add effect ${uri}`)
    }
    // The add command returns immediately, but websocket will send 'add <instance> <uri>'
    // Return the instance so the caller can use it
    return instance
  }

  const removeEffect = async (id: string) => {
    console.log(`Removing ${id}`)
    const response = await fetch(`/api/effects/effect/remove${id}`)
  }

  const loadEffects = async () => {
    const response = await fetch('/api/effects/effect/list')
    if (!response.ok) throw new Error('Failed to load effects')
    const results = await response.json()
    setEffectsState(results as Effect[])
  }

  const getEffectByUri = (effects: Effect[], uri: string): Effect | undefined => {
    return effects.find(e => e.uri === uri)
  }

  const isNamEffect = (uri: string): boolean => {
    return uri.includes('neural-amp-modeler-lv2')
  }

  useEffect(() => {
    loadEffects()
    loadModelFiles()
  }, [])

  const pedalboardEffects = Object.fromEntries(
    Object.entries(activeEffectContext).map(([id, activeEffect]) => {
      const effect = getEffectByUri(effectsState, (activeEffect as ActiveEffect).uri)
      return [id, { effect, activeEffect }]
    })
  )

  return (
    <EffectsContext.Provider value={effectsState}>
      <div class="space-y-3">
        {!pedalboardInfo ? (
          <p class="text-lcd-400 text-xs text-center">Select a pedalboard to manage effects</p>
        ) : (
          <>
            <h2 class="text-xs lcd-text text-center uppercase tracking-widest">Pedalboard Effects</h2>
            <div class="space-y-1 pr-1">
              {(Object.keys(pedalboardEffects).length < 1 || effectsState.length < 1) ? (
                <p class="text-lcd-400 text-xs">No active effects</p>
              ) : (
                Object.entries(pedalboardEffects).map(([id, item]) => {
                  const effect = item.effect
                  const activeEffect = item.activeEffect
                  const showModelSelector = effect?.uri && isNamEffect(effect.uri)
                  return (
                    <div class="p-2 bg-lcd-700 rounded-sm space-y-2">
                      <div class="flex items-center justify-between">
                        <div>
                          <p class="text-lcd-200 font-bold text-xs">{effect?.name}</p>
                          <p class="text-lcd-400 text-xs">{id}</p>
                        </div>
                        <button
                          class="text-lcd-300 hover:text-lcd-200 text-xs"
                          onClick={() => { removeEffect(id) }}
                        >
                          X
                        </button>
                      </div>

                      {showModelSelector && (
                        <select
                          class="lcd-select text-2xs w-full"
                          onChange={(e) => {
                            const target = e.target as HTMLSelectElement
                            setModelFile(id, target.value)
                          }}
                        >
                          <option value="">Select model...</option>
                          {modelFilesState.map((file) => (
                            <option key={file.name} value={file.name}>
                              {file.name}
                            </option>
                          ))}
                        </select>
                      )}

                      {Object.entries(activeEffect.params).length > 0 && (
                        <div class="mt-1 space-y-0.5">
                          {Object.entries(activeEffect.params).map(([symbol, value]) => (
                            <p class="text-lcd-400 text-2xs" key={symbol}>
                              {symbol}: {value}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>

            <div class="border-t-1 border-lcd-300"></div>

            <Button
              class="lcd-button w-full"
              onClick={() => setAddEffectOpen(true)}
            >
              ADD EFFECT
            </Button>
          </>
        )}
      </div>

      <Dialog open={addEffectOpen} onClose={setAddEffectOpen} class="relative z-10">
        <DialogBackdrop
          transition
          class="fixed inset-0 bg-black/80 flex items-center justify-center transition-opacity data-closed:opacity-0 data-enter:duration-300 data-enter:ease-out data-leave:duration-200 data-leave:ease-in"
        />
        <div class="fixed inset-0 z-10 w-screen overflow-y-auto">
          <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <DialogPanel
              transition
              class="relative transform overflow-hidden text-center shadow-xl transition-all data-closed:translate-y-4 data-closed:opacity-0 data-enter:duration-300 data-enter:ease-out data-leave:duration-200 data-leave:ease-in sm:my-8 sm:w-full sm:max-w-lg data-closed:sm:translate-y-0 data-closed:sm:scale-95"
            >
              <div class="lcd-panel p-4">
                <DialogTitle class="text-xs lcd-text uppercase tracking-widest mb-2">Add Effect</DialogTitle>

                <div class="max-h-64 overflow-y-auto space-y-1 mb-3 pr-1">
                  {effectsState.length < 1 ? (
                    <p class="text-lcd-400 text-xs">No effects available</p>
                  ) : (
                    effectsState.map((effect: Effect) => (
                      <button
                        key={effect.uri}
                        class="w-full text-left p-2 bg-lcd-700 hover:bg-lcd-600 rounded-sm text-xs"
                        onClick={() => {
                          addEffect(effect.uri)
                          setAddEffectOpen(false)
                        }}
                      >
                        <span class="text-lcd-200">{effect.name}</span>
                      </button>
                    ))
                  )}
                </div>

                <div class="flex gap-2">
                  <Button
                    class="lcd-button"
                    onClick={() => setAddEffectOpen(false)}
                  >
                    CANCEL
                  </Button>
                </div>
              </div>
            </DialogPanel>
          </div>
        </div>
      </Dialog>
    </EffectsContext.Provider>
  )
}

export { EffectsContext }
