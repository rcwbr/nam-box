import { createContext } from 'preact'
import { useContext, useEffect, useState } from 'preact/hooks';
import type { ComponentChildren } from 'preact'
import {
  Button,
  Dialog,
  DialogBackdrop,
  DialogPanel,
  DialogTitle,
  Field,
  Input,
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions
} from '@headlessui/react'

import { SnapshotContext, SaveSnapshotContext } from './ModSocket';
import type { PedalboardInfo } from './types';

interface Pedalboard {
  bundle: string
  title: string
  uri: string
  broken?: boolean
  created_at?: number
  factory?: boolean
  hasTrialPlugins?: boolean
  updated_at?: number
  version?: string
}

export const PedalboardInfoContext = createContext<PedalboardInfo | null>(null)

export default function PedalboardManager({children} : { children: ComponentChildren }) {
  const [pedalboardsState, setPedalboardsState] = useState<Array<Pedalboard>>([])
  // mod-ui API does not provide the last-used/current pedalboard. It could be extracted from the rendered webpage:
  // curl -sk 'https://localhost/api/effects/?v=1781837767' | grep -oP '<h1 class="top bottom blend">\K[^<]+'
  // But to avoid this hack, will instead always start with no selected pedalboard.
  const [currentPedalboardState, setCurrentPedalboardState] = useState<Pedalboard | null>(null)
  const [currentPedalboardInfoState, setCurrentPedalboardInfoState] = useState<PedalboardInfo | null>(null)
  const [createPedalboardOpen, setCreatePedalboardOpen] = useState<boolean>(false)
  const snapshot = useContext(SnapshotContext)
  const saveSnapshot = useContext(SaveSnapshotContext)

  const loadPedalboards = async () => {
    const response = await fetch('/api/effects/pedalboard/list')
    if (!response.ok) throw new Error('Failed to load pedalboards')
    const results = await response.json()
    setPedalboardsState(results as Pedalboard[])
  }

  const setCurrentPedalboard = async (pb: Pedalboard) => {
    const loadResponse = await fetch(`/api/effects/pedalboard/load_bundle/?bundlepath=${encodeURIComponent(pb.bundle)}`, { method: 'POST' })
    if (!loadResponse.ok) throw new Error(`Failed to load pedalboard ${pb.title}`)
    const infoResponse = await fetch(`/api/effects/pedalboard/info/?bundlepath=${encodeURIComponent(pb.bundle)}`)
    if (!infoResponse.ok) throw new Error(`Failed to load pedalboard info ${pb.title}`)
    setCurrentPedalboardState(pb)
    const currentPB = (await infoResponse.json()) as PedalboardInfo
    setCurrentPedalboardInfoState(currentPB)
  }

  const savePedalboard = async () => {
    if (!currentPedalboardState) throw new Error('No current pedalboard to save')
    const response = await fetch(`/api/effects/pedalboard/save?title=${encodeURIComponent(currentPedalboardState.title)}&asNew=0`, { method: 'POST' })
    if (!response.ok) throw new Error(`Failed to save pedalboard ${currentPedalboardState.title}`)
  }

  const createPedalboard = async (newPBName: string) => {
    const response = await fetch(`/api/effects/pedalboard/save?title=${encodeURIComponent(newPBName)}&asNew=1`, { method: 'POST' })
    if (!response.ok) throw new Error('Failed to save new pedalboard')
    const newPB = (await response.json()) as Pedalboard
    setPedalboardsState(pedalboardsState.concat([newPB]))
    setCurrentPedalboard(newPB)
  }

  useEffect(() => {
    loadPedalboards()
  }, [])

  return (
    <PedalboardInfoContext.Provider value={currentPedalboardInfoState}>
      <div class="space-y-2">
        <h2 class="text-xs lcd-text text-center uppercase tracking-widest">Pedalboard</h2>
        <div class="space-y-2 text-xs lcd-select-wrapper w-full">
          <Listbox
            value={currentPedalboardState}
            onChange={(pb: Pedalboard | null) => {
              pb && setCurrentPedalboard(pb)
            }}
          >
            <ListboxButton class="text-xs lcd-select">
              <span class="block truncate">
                {currentPedalboardState ? currentPedalboardState.title : 'Select pedalboard...'}
              </span>
              <svg class="h-4 w-4 text-lcd-300" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 011.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </ListboxButton>
            <ListboxOptions
              class="lcd-select-options"
              anchor="bottom start"
              transition
            >
              <div class="border-t-1 border-lcd-300"></div>
              {pedalboardsState.length < 1 ? (
                <ListboxOption value={null} disabled class="lcd-select-option">
                  Loading...
                </ListboxOption>
              ) : (
                pedalboardsState.map((pedalboard) => (
                  <ListboxOption
                    value={pedalboard}
                    class="lcd-select-option"
                  >
                    {pedalboard.title}
                  </ListboxOption>
                ))
              )}
            </ListboxOptions>
          </Listbox>
        </div>
        <div class="flex gap-2">
          <Button class="lcd-button"
          onClick={() => savePedalboard()}
          >
            SAVE
          </Button>
          <Button
            class="lcd-button"
            onClick={() => setCreatePedalboardOpen(true)}
          >
            NEW
          </Button>
        </div>
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
                <DialogTitle class="text-xs lcd-text uppercase tracking-widest mb-2">Create Pedalboard</DialogTitle>
                <form
                  onSubmit={(event: SubmitEvent) => {
                    event.preventDefault()
                    setCreatePedalboardOpen(false)
                    if (event != null && event.target != null) {
                      const pbFormData = new FormData(event.target as HTMLFormElement)
                      createPedalboard(pbFormData.get('new-pb-name') as string)
                    }
                  }}
                >
                  <Field>
                    <Input name="new-pb-name" placeholder="Pedalboard name" class="lcd-input text-xs w-full mb-3" />
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
      {children}
    </PedalboardInfoContext.Provider>
  )
}
