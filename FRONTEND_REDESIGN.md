# Frontend Redesign: Mod-API State Management

## Summary

**Replace nested context providers with independent hooks** - Each component calls its own TanStack Query hooks, eliminating the wrapping cascade (`ModSocket` → `PedalboardManager` → `EffectsManager`). State is managed at the root (`App.tsx`) and passed as props to children.

## Context

The current frontend has two competing state management approaches:

1. **Legacy mod-ui API** - Used by `PedalboardManager.tsx` for pedalboards via endpoints like `/api/effects/pedalboard/list` and `/api/effects/pedalboard/load_bundle`

2. **Custom WebSocket protocol** - Used by `ModSocket.tsx` for real-time effect updates with hand-rolled message parsing (commands: `add`, `remove`, `param_set`, `patch_set`, `pedal_snapshot`)

The new `mod-api-openapi.json` provides a clean, unified REST API under `/api/v1/` with proper OpenAPI schema types. This redesign maps the frontend entirely to the mod-api.

## Problem Statement

State is fragmented:
- Pedalboards: Old API + separate `PedalboardInfoContext`
- Effects: Mixed WebSocket (active effects) + old API (effect catalog)
- Parameters: Mixed WebSocket (`SetPatchContext`) + old API
- No type safety - frontend types (`PedalboardInfo`, `Plugin`, `ActiveEffect`) don't match API types (`Pedalboard`, `EffectInstance`, `EffectInfo`)

## Proposed Architecture

### State Flow Overview (Flat Architecture)

```
┌─────────────────────────────────────────────────────────────────┐
│              React Components (Independent, No Nesting)           │
├─────────────────────────────────────────────────────────────────┤
│  PedalboardSelector: usePedalboards() hook                       │
│  EffectList: usePedalboard(id) hook                              │
│  EffectItem: useRemoveEffect(), useSetParameter() hooks            │
│  ParameterControl: useParameter(), useSetParameter() hooks        │
├─────────────────────────────────────────────────────────────────┤
│                   TanStack Query (Server State)                   │
├─────────────────────────────────────────────────────────────────┤
│  Query Keys:    ['pedalboards'], ['pedalboard', id], ['effects']  │
│  Mutations:     useCreatePedalboard, useSelectPedalboard, etc.    │
│  Caching:       Automatic deduplication across components           │
├─────────────────────────────────────────────────────────────────┤
│                    mod-api OpenAPI REST API                       │
├─────────────────────────────────────────────────────────────────┤
│  /api/v1/pedalboards         GET, POST, DELETE, PUT              │
│  /api/v1/pedalboards/{id}    GET (full with effects)            │
│  /api/v1/effects               GET (catalog)                     │
│  /api/v1/ports                 GET                               │
│  /api/v1/connections           GET, POST, DELETE                 │
│  /api/v1/parameters            GET, PUT                           │
└─────────────────────────────────────────────────────────────────┘
```

**Note**: Only `QueryClientProvider` wraps the root - no domain-specific context providers needed.

### Component Structure (Flat, Not Nested)

```
src/
├── api/
│   ├── client.ts       # Thin fetch wrapper with OpenAPI types
│   ├── types.ts        # Types from OpenAPI schema (replaces types.ts)
│   └── hooks/
│       ├── usePedalboards.ts
│       ├── usePedalboard.ts    # Fetched independently, not nested
│       ├── useEffects.ts
│       └── useModelFiles.ts
├── components/
│   ├── PedalboardSelector.tsx   # Standalone: calls usePedalboards() + useSelectPedalboard()
│   ├── EffectList.tsx           # Standalone: calls usePedalboard(id)
│   ├── EffectItem.tsx           # One effect with parameter controls
│   ├── ParameterControl.tsx     # Knob/slider for one parameter
│   └── FileUpload.tsx           # Unchanged
├── App.tsx                      # Root with QueryClientProvider only
├── layouts/
│   └── Layout.astro
└── pages/
    └── index.astro
```

**No wrapping providers** - Each component is self-contained with its hook dependencies.

### State Management Layers

#### 1. Server State (TanStack Query) - NO CONTEXT PROVIDERS NEEDED
Each component calls its own hooks. TanStack Query's `QueryClientProvider` at root handles caching and deduplication automatically.
- **usePedalboards()** - fetches all pedalboards list
- **useCurrentPedalboard()** - fetches current pedalboard (or null)
- **usePedalboard(id)** - fetches specific pedalboard detail
- **useEffects()** - fetches effect catalog
- **useModelFiles()** - fetches NAM model files
- Hooks with mutations for all write operations

#### 2. Component State Only (useState)
- Modal open/closed state (useState in components)
- Temporary form input values
- Loading states
- Selected IDs stored in URL params for persistence

**No context providers for server state** - this eliminates the nesting cascade (PedalboardManager wrapping EffectsManager) and makes components independently testable.

### Data Flow Patterns

#### Loading Current Pedalboard
```typescript
// Current pedalboard is derived from selection
const { data: currentPedalboard } = useCurrentPedalboard()
// Internally: usePedalboard(currentId) OR null if none selected
```

#### Effect Parameter Update
```typescript
const setParameterMutation = useSetParameter(pedalboardId, effectId)
setParameterMutation.mutate({ paramName, value })
// Optimistic update + error rollback
```

#### Adding an Effect
```typescript
const addEffectMutation = useAddEffect(pedalboardId)
addEffectMutation.mutate({ effect_uri: namUri }, {
  onSuccess: () => queryClient.invalidateQueries(['pedalboard', pedalboardId])
})
```

#### Port Connection
```typescript
const connectMutation = useConnectPorts(pedalboardId)
connectMutation.mutate({ input_port_id, output_port_id })
```

### OpenAPI Type Mapping

| Frontend Type (old) | OpenAPI Type (new) | Notes |
|---------------------|-------------------|-------|
| `PedalboardInfo` | `Pedalboard` | Direct replacement - has `id`, `name`, `file`, `effects`, `connections` |
| `Plugin` | `EffectInstance` | Direct replacement - has `id`, `uri`, `ports`, `parameters` |
| `Port` | `Port` | Merge - current has extra MIDI properties, use API version |
| `ActiveEffect` | `EffectInstance` | The API includes parameter values directly |

### Component Interactions (Flat Architecture)

#### App State
- Single source of truth: URL query parameter `?pedalboardId=` or empty string
- All components read from URL and call their own hooks

#### PedalboardSelector (self-contained)
1. Calls `usePedalboards()` to get list
2. Calls `useSelectPedalboard().mutate(id)` on selection
3. Selected ID stored in URL (?pedalboardId=123)

#### EffectList (self-contained)
1. Receives `pedalboardId` as prop
2. Calls `usePedalboard(pedalboardId)` if ID exists
3. Renders effect instances inline with parameter controls
4. Uses `useRemoveEffect().mutate()` for removal

#### ParameterControl (self-contained)
1. Receives `pedalboardId`, `effectId`, `paramName` as props
2. Uses `useParameter(pedalboardId, effectId, paramName)` for value
3. Uses `useSetParameter().mutate()` for changes with optimistic update

**Benefits:**
- Components can be placed anywhere in the layout
- Easy to test - no context providers needed
- TanStack Query handles caching deduplication automatically

### Hook Design (Self-Contained Components)

Each hook encapsulates fetching, caching, and mutation logic:

```typescript
// usePedalboards.ts
export function usePedalboards() {
  return useQuery({
    queryKey: ['pedalboards'],
    queryFn: () => fetch('/api/v1/pedalboards').then(r => r.json()),
    staleTime: 5000, // 5 second cache
  })
}

// usePedalboard.ts
export function usePedalboard(id: number | null) {
  return useQuery({
    queryKey: ['pedalboard', id],
    queryFn: () => fetch(`/api/v1/pedalboards/${id}`).then(r => r.json()),
    enabled: id !== null,
  })
}

// useSelectPedalboard.ts
export function useSelectPedalboard() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => 
      fetch(`/api/v1/pedalboards/${id}/select`, { method: 'PUT' }),
    onSuccess: () => queryClient.invalidateQueries(['pedalboard', 'current']),
  })
}

// useSetParameter.ts (with optimistic update)
export function useSetParameter(pedalboardId: number, effectId: number, paramName: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (value: number | string) =>
      fetch(`/api/v1/pedalboards/${pedalboardId}/effects/${effectId}/parameters/${paramName}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value }),
      }),
    onMutate: async (value) => {
      // Cancel ongoing queries
      await queryClient.cancelQueries(['pedalboard', pedalboardId])
      // Snapshot previous value
      const previous = queryClient.getQueryData(['pedalboard', pedalboardId])
      // Optimistically update
      queryClient.setQueryData(['pedalboard', pedalboardId], (old: Pedalboard) => ({
        ...old,
        effects: {
          ...old.effects,
          [effectId]: {
            ...old.effects[effectId],
            parameters: {
              ...old.effects[effectId].parameters,
              [paramName]: { ...old.effects[effectId].parameters[paramName], value },
            },
          },
        },
      }))
      return { previous }
    },
    onError: (err, value, context) => {
      queryClient.setQueryData(['pedalboard', pedalboardId], context?.previous)
    },
    onSettled: () => {
      queryClient.invalidateQueries(['pedalboard', pedalboardId])
    },
  })
}
```

### Migration Strategy

1. **Phase 1: Foundation** (Parallel-safe)
   - Create `src/api/types.ts` from OpenAPI schema
   - Add TanStack Query dependency to package.json
   - Create `src/api/hooks/` directory
   - Create individual hooks that can be used independently

2. **Phase 2: Flat Component Replacement** (Parallel-safe)
   - Create `PedalboardSelector.tsx` - standalone with hook
   - Create `EffectList.tsx` - standalone, reads pedalboardId from URL
   - Create `EffectItem.tsx` - one effect with remove button + parameter controls
   - Create `ParameterControl.tsx` - knob/slider component per parameter
   - Create `ModelSelector.tsx` - dropdown for NAM model files

3. **Phase 3: Update Entry Point**
   - Wrap root with `QueryClientProvider` in `index.astro` or `App.tsx`
   - Replace old nested component tree with flat structure

4. **Phase 4: Cleanup**
   - Remove `ModSocket.tsx` (no longer needed - no WebSocket dependency)
   - Remove `PedalboardManager.tsx` (replaced by `PedalboardSelector.tsx`)
   - Remove `EffectsManager.tsx` (replaced by `EffectList.tsx`)
   - Remove `Mod.tsx` (replaced by `App.tsx`)
   - Remove old `types.ts` (replaced by `api/types.ts`)

## Verification

After implementation:
1. Load pedalboards list - verifies GET /pedalboards
2. Select a pedalboard - verifies PUT /pedalboards/{id}/select
3. Add a NAM effect - verifies POST /pedalboards/{id}/effects
4. Set model parameter - verifies PUT /pedalboards/{id}/effects/{eid}/parameters/{name}
5. Observe all parameters reflected - verifies GET /pedalboards/{id}

## Decisions

Based on user preferences:
1. **Polling only** - HTTP polling for state updates, no WebSocket dependency
2. **Optimistic updates** - Immediate UI feedback with server confirmation and rollback
3. **Keep file uploads separate** - FileUploadManager stays independent
4. **TanStack Query** - Full-featured server state library

## State Sharing Strategy

**Removed URL routing** - Instead, pass `pedalboardId` as props from parent to children:

```typescript
// In App.tsx or index.astro
const [selectedPedalboardId, setSelectedPedalboardId] = useState<number | null>(null)

return (
  <PedalboardSelector 
    selectedId={selectedPedalboardId} 
    onSelect={setSelectedPedalboardId} 
  />
  <EffectList pedalboardId={selectedPedalboardId} />
)
```

This keeps the flat, independent component architecture without adding routing complexity.