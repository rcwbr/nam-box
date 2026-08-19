import { useState, useEffect } from 'preact/hooks'
import { usePedalboards, useCurrentPedalboard } from '../api/hooks/usePedalboards'
import { useCreatePedalboard, useSelectPedalboard, useDeletePedalboard } from '../api/hooks/usePedalboardMutations'
import {
  Button,
  Dialog,
  DialogBackdrop,
  DialogPanel,
  DialogTitle,
  Field,
  Input,
} from '@headlessui/react'
import Select from './Select'

interface PedalboardSelectorProps {
  selectedId: number | null
  onSelect: (id: number | null) => void
}

/**
 * Standalone pedalboard selector component.
 * Does not require wrapping contexts - uses hooks directly.
 */
export default function PedalboardSelector({ selectedId, onSelect }: PedalboardSelectorProps) {
  const { data: pedalboards } = usePedalboards()
  const { data: currentPedalboard } = useCurrentPedalboard()
  const createMutation = useCreatePedalboard()
  const selectMutation = useSelectPedalboard()
  const deleteMutation = useDeletePedalboard()

  // Auto-select the current pedalboard when it loads on page load.
  // Only fires when the server returns a different pedalboard than the
  // currently selected one, so manual selections are not overridden.
  useEffect(() => {
    if (currentPedalboard && currentPedalboard.id !== selectedId) {
      onSelect(currentPedalboard.id)
    }
  }, [currentPedalboard, selectedId, onSelect])

  const [createPedalboardOpen, setCreatePedalboardOpen] = useState(false)

  const handleSelect = (id: number | null) => {
    if (id !== null) {
      selectMutation.mutate(id)
    }
    onSelect(id)
  }

  const handleCreate = (name: string) => {
    createMutation.mutate({ name }, {
      onSuccess: (newPedalboard) => {
        onSelect(newPedalboard.id)
      },
    })
  }

  const handleDelete = (id: number) => {
    if (confirm('Delete this pedalboard?')) {
      deleteMutation.mutate(id)
      if (selectedId === id) {
        onSelect(null)
      }
    }
  }

  // Convert pedalboards record to array for Select component
  const pedalboardList = pedalboards ? Object.values(pedalboards) : []

  // Find currently selected pedalboard
  const selectedPedalboard = selectedId !== null && pedalboards ? pedalboards[selectedId] : null

  return (
    <div class="space-y-2">
      <h2 class="text-xs lcd-text text-center uppercase tracking-widest">Pedalboard</h2>

      <div class="space-y-2 text-xs lcd-select-wrapper w-full">
        <Select
          value={selectedPedalboard}
          options={pedalboardList}
          onChange={(pb: { id: number } | null) => handleSelect(pb?.id ?? null)}
          placeholder="Select pedalboard..."
          optionLabel={(pb: { name: string }) => pb.name ?? 'Untitled'}
          optionKey={(pb: { id: number }) => pb.id}
          renderOption={(pb: { id: number; name: string }) => (
            <div class="flex justify-between items-center">
              <span>{pb.name ?? 'Untitled'}</span>
              <button
                class="text-lcd-400 hover:text-red-400 text-xs"
                onClick={(e: Event) => {
                  e.stopPropagation()
                  handleDelete(pb.id)
                }}
              >
                Delete
              </button>
            </div>
          )}
        />
      </div>

      <div class="flex gap-2">
        <Button
          class="lcd-button"
          onClick={() => setCreatePedalboardOpen(true)}
        >
          NEW
        </Button>
      </div>

      <Dialog open={createPedalboardOpen} onClose={setCreatePedalboardOpen} class="relative z-10">
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
                <DialogTitle class="text-xs lcd-text uppercase tracking-widest mb-2">
                  Create Pedalboard
                </DialogTitle>
                <form
                  onSubmit={(event: SubmitEvent) => {
                    event.preventDefault()
                    setCreatePedalboardOpen(false)
                    if (event.target) {
                      const formData = new FormData(event.target as HTMLFormElement)
                      const name = formData.get('new-pb-name') as string
                      if (name) handleCreate(name)
                    }
                  }}
                >
                  <Field>
                    <Input
                      name="new-pb-name"
                      placeholder="Pedalboard name"
                      class="lcd-input text-xs w-full mb-3"
                    />
                    <div class="flex gap-2">
                      <Button
                        class="lcd-button"
                        onClick={() => setCreatePedalboardOpen(false)}
                      >
                        CANCEL
                      </Button>
                      <Button class="lcd-button" type="submit">
                        CREATE
                      </Button>
                    </div>
                  </Field>
                </form>
              </div>
            </DialogPanel>
          </div>
        </div>
      </Dialog>
    </div>
  )
}