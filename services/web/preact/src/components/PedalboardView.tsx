import { useState } from 'preact/hooks'
import type { EffectInfo } from '../api/types'
import { useEffects, useAddEffect } from '../api/hooks/useEffects'
import {
  Button,
  Dialog,
  DialogBackdrop,
  DialogPanel,
  DialogTitle,
} from '@headlessui/react'
import PedalboardDAG from './PedalboardDAG'

interface PedalboardViewProps {
  pedalboardId: number | null
}

/**
 * Pedalboard view component.
 *
 * Renders the pedalboard as an interactive DAG (via PedalboardDAG) and
 * provides the ADD EFFECT dialog. System I/O ports are pinned at the
 * top and bottom of the canvas; effect nodes are stacked in a static
 * column in the centre.
 */
export default function PedalboardView({ pedalboardId }: PedalboardViewProps) {
  const { data: effectCatalog } = useEffects()

  // Early return if no pedalboard selected - don't call hooks that need valid IDs
  if (!pedalboardId) {
    return (
      <div class="space-y-3">
        <h2 class="text-xs lcd-text text-center uppercase tracking-widest">Pedalboard Effects</h2>
        <p class="text-lcd-400 text-xs text-center">Select a pedalboard to manage effects</p>
      </div>
    )
  }

  const addEffectMutation = useAddEffect(pedalboardId)
  const [addEffectOpen, setAddEffectOpen] = useState(false)

  const handleAddEffect = (uri: string) => {
    addEffectMutation.mutate({ effect_uri: uri }, {
      onSuccess: () => setAddEffectOpen(false),
    })
  }

  return (
    <div class="space-y-3">
      <PedalboardDAG pedalboardId={pedalboardId} />

      <Button
        class="lcd-button w-full"
        onClick={() => setAddEffectOpen(true)}
      >
        ADD EFFECT
      </Button>

      <Dialog open={addEffectOpen} onClose={setAddEffectOpen} class="relative z-10">
        <DialogBackdrop
          transition
          class="fixed inset-0 bg-black/80 flex items-center justify-center transition-opacity data-closed:opacity-0 data-enter:duration-300 data-enter:ease-out data-leave:duration-200 data-leave:ease-in"
        />
        <div class="fixed inset-0 z-10 w-screen overflow-y-auto">
          <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <DialogPanel
              transition
              class="relative transform overflow-hidden text-center shadow-xl transition-all data-closed:translate-y-4 data-closed:opacity-0 data-enter:duration-300 data-enter:ease-out data-leave:duration-200 data-leave:ease-in sm:my-8 sm:w-full sm:max-w-lg data-closed:sm:translate-x-0 data-closed:sm:scale-95"
            >
              <div class="lcd-panel p-4">
                <DialogTitle class="text-xs lcd-text uppercase tracking-widest mb-2">
                  Add Effect
                </DialogTitle>

                <div class="max-h-64 overflow-y-auto space-y-1 mb-3 pr-1">
                  {!effectCatalog || effectCatalog.length === 0 ? (
                    <p class="text-lcd-400 text-xs">No effects available</p>
                  ) : (
                    effectCatalog.map((effect: EffectInfo) => (
                      <button
                        key={effect.uri}
                        class="w-full text-left p-2 bg-lcd-700 hover:bg-lcd-600 rounded-sm text-xs"
                        onClick={() => handleAddEffect(effect.uri)}
                      >
                        <span class="text-lcd-200">{effect.name ?? effect.uri}</span>
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
    </div>
  )
}
