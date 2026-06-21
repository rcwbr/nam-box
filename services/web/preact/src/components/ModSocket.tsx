import { createContext } from 'preact'
import { useEffect, useState } from 'preact/hooks'
import type { ComponentChildren } from 'preact'
import type { ActiveEffect } from './types'

interface Snapshot {
  name: string
  id: number
}

export const ActiveEffectsContext = createContext<{ [effectId: string]: ActiveEffect }>({})
export const SnapshotContext = createContext<Snapshot | null>(null)
export const SaveSnapshotContext = createContext<{(): void} | null>(null)

/**
 * Send a patch_set message through the websocket.
 * Format: "patch_set <instance> <parameteruri> <valuetype> <valuedata>"
 * - instance: effect instance identifier (e.g., "0" or "/nam374")
 * - parameteruri: full parameter URI (e.g., "http://github.com/mikeoliphant/neural-amp-modeler-lv2#model")
 * - valuetype: "p"=path, "s"=string, "f"=float, etc.
 * - valuedata: the value to set
 */
export const SetPatchContext = createContext<{
  (instance: string, parameterUri: string, valueType: string, valuedata: string | number): void
} | null>(null)

export default function ModSocket({children} : { children: ComponentChildren }) {
  const [snapshotState, setSnapshotState] = useState<Snapshot | null>(null)
  const [activeEffectsState, setActiveEffectsState] = useState<{ [effectId: string]: ActiveEffect }>({})
  const [socketRef, setSocketRef] = useState<WebSocket | null>(null)

  const setPatch = (instance: string, parameterUri: string, valueType: string, valuedata: string | number) => {
    if (socketRef && socketRef.readyState === WebSocket.OPEN) {
      // Format: patch_set <instance> <parameteruri> <valuetype> <valuedata>
      const message = `patch_set ${instance} ${parameterUri} ${valueType} ${valuedata}`
      console.log('Sending:', message)
      socketRef.send(message)
    }
  }

  const setSnapshotStateFromID = async (snapshotID: number) => {
    const response = (await fetch(`/api/effects/snapshot/name?id=${snapshotID}`))
    if (!response.ok) throw new Error(`Failed to load snapshot name for ${snapshotID}`)
    const name = (await response.json())['name']
    const currentSnapshot: Snapshot = { name: name, id: snapshotID }
    setSnapshotState(currentSnapshot)
  }

  const saveSnapshot = async () => {
    // const listResponse = await fetch('/api/effects/snapshot/list')
    // if (!listResponse.ok) throw new Error('Failed to load snapshot list')
    // const snapshots: Snapshot[] = Object.entries(await listResponse.json()).map(
    //   ([id, name]) => ({ name: name as string, id: parseInt(id) })
    // )
    if (!snapshotState) throw new Error('Could not save a new snapshot while missing the current snapshot.')
    const saveResponse = await fetch(`/api/effects/snapshot/saveas?title=${snapshotState.name}`)
    if (!saveResponse.ok) throw new Error(`Failed to save new snapshot ${snapshotState.name}`)
    setSnapshotStateFromID((await saveResponse.json()).id)
  }

  useEffect(() => {
    const socket = new WebSocket(`wss://${window.location.host}/api/effects/websocket`)
    setSocketRef(socket)

    socket.onopen = () => {
      console.log('ModSocket: Connected')
    }

    socket.onmessage = (event) => {
      // Parse space-separated format: "<command> <arg1> <arg2> ..."
      // Note: Messages may have null terminator \0 which we strip from the entire message
      const rawData = event.data.toString()
      const message = rawData.replace(/\0/g, '').trim()
      const parts = message.split(/\s+/)
      const command = parts[0]

      console.log('WebSocket received:', message)

      if (command) {
        if (command === 'loading_end') {
          setSnapshotStateFromID(parts[1])
        } else if (command === 'pedal_snapshot') {
          setActiveEffectsState({})
          setSnapshotStateFromID(parts[1])
        } else if (command === 'add') {
          console.log('add command parts:', parts)
          setActiveEffectsState(activeEffects => ({
            ...activeEffects,
            [parts[1]]: { uri: parts[2], params: {} }
          }))
        } else if (command === 'param_set') {
          console.log('param_set command parts:', parts)
          // Format: "param_set <id> <symbol> <value>"
          setActiveEffectsState(activeEffects => {
            const effectId = parts[1]
            const symbol = parts[2]
            const value = parts[3]
            const existing = activeEffects[effectId] as ActiveEffect | undefined
            return {
              ...activeEffects,
              [effectId]: existing
                ? { ...existing, params: { ...existing.params, [symbol]: value } }
                : { params: { [symbol]: value } }
            }
          })
        } else if (command === 'patch_set') {
          // Response format: "patch_set <instance> <writable> <parameteruri> <valuetype> <valuedata>"
          // (input format for sending is 4 args: instance, parameteruri, vtype, valuedata)
          console.log('patch_set response parts:', parts, 'length:', parts.length)
          if (parts.length >= 6) {
            setActiveEffectsState(activeEffects => {
              const effectId = parts[1]
              const parameterUri = parts[3]
              const valueType = parts[4]
              const valuedata = valueType === 'p' || valueType === 's' ? parts[5] : parseFloat(parts[5])
              const existing = activeEffects[effectId] as ActiveEffect | undefined
              return {
                ...activeEffects,
                [effectId]: existing
                  ? { ...existing, params: { ...existing.params, [parameterUri]: valuedata } }
                  : { uri: '', params: { [parameterUri]: valuedata } }
              }
            })
          } else {
            console.warn('patch_set response with unexpected format:', parts)
          }
        } else if (command === 'error') {
          console.error('WebSocket error response:', parts)
        } else if (command === 'sys_stats') {
          // System stats notification - ignore during patch_set wait
          console.log('sys_stats (ignoring):', parts[1])
        } else if (command === 'remove') {
          setActiveEffectsState(activeEffects => {
            const newActiveEffects = Object.assign({}, activeEffects)
            delete newActiveEffects[parts[1]]
            return newActiveEffects
          })
        } else {
          console.log('Unknown websocket command:', command, parts)
        }
      }
    }

    socket.onclose = (event) => {
      console.log('ModSocket: Disconnected', event.code, event.reason)
    }

    socket.onerror = (error) => {
      console.error('ModSocket error:', error)
    }

    return () => {
      socket.close()
    }
  }, [])

  return (
    <ActiveEffectsContext.Provider value={activeEffectsState}>
      <SaveSnapshotContext.Provider value={saveSnapshot}>
        <SetPatchContext.Provider value={setPatch}>
          <SnapshotContext.Provider value={snapshotState}>
            {children}
          </SnapshotContext.Provider>
        </SetPatchContext.Provider>
      </SaveSnapshotContext.Provider>
    </ActiveEffectsContext.Provider>
  )
}
