# Implemented State: Mod-API Architecture

## State Management Structure

### Flat Architecture (No Nested Context Providers)

```
┌─────────────────────────────────────────────────────────────────┐
│              React Components (Independent)                       │
├─────────────────────────────────────────────────────────────────┤
│  PedalboardSelector  EffectList                                 │
│  (inline ModelSelector for NAM)                                 │
├─────────────────────────────────────────────────────────────────┤
│                    TanStack Query (Server State)                │
├─────────────────────────────────────────────────────────────────┤
│                mod-api OpenAPI REST API                           │
└─────────────────────────────────────────────────────────────────┘
```

**Only `QueryClientProvider` wraps the root. All other components are independent.**

---

## Component Design

### Component Structure

```
src/
├── api/
│   ├── types.ts        # Types from OpenAPI schema
│   └── hooks/
│       ├── index.ts               # Hook exports
│       ├── usePedalboards.ts      # usePedalboards(), useCurrentPedalboard()
│       ├── usePedalboard.ts       # usePedalboard(id)
│       ├── useEffects.ts          # useEffects(), useAddEffect(), useRemoveEffect()
│       ├── usePedalboardMutations.ts  # useCreatePedalboard(), useSelectPedalboard(), useDeletePedalboard()
│       ├── useParameters.ts       # useParameters(), useSetParameter()
│       └── useModelFiles.ts       # useModelFiles()
├── components/
│   ├── App.tsx                     # Root with QueryClientProvider
│   ├── PedalboardSelector.tsx      # Standalone pedalboard selector
│   ├── EffectList.tsx              # Standalone effect list (inline EffectItem)
│   ├── FileUploadManager.tsx         # Unchanged (separate API)
│   └── Select.tsx                  # Reusable select component
└── pages/
    └── index.astro                 # Entry point
```

---

## Hook Design

### Query Hooks (Server State)

| Hook | Query Key | Endpoint | Purpose |
|------|-----------|----------|---------|
| `usePedalboards()` | `['pedalboards']` | GET `/api/v1/pedalboards` | Fetch all pedalboards list |
| `useCurrentPedalboard()` | `['pedalboard', 'current']` | GET `/api/v1/pedalboards/current` | Current selected pedalboard |
| `usePedalboard(id)` | `['pedalboard', id]` | GET `/api/v1/pedalboards/{id}` | Fetch specific pedalboard detail |
| `useEffects()` | `['effects']` | GET `/api/v1/effects` | Fetch effect catalog |
| `useModelFiles()` | `['model-files']` | GET `/api/v1/model-files` | Fetch NAM model files |

### Mutation Hooks

| Hook | Endpoint | Operation |
|------|----------|-----------|
| `useSelectPedalboard()` | PUT `/pedalboards/{id}/select` | Select active pedalboard |
| `useAddEffect(pedalboardId)` | POST `/pedalboards/{id}/effects` | Add effect to pedalboard |
| `useRemoveEffect(pedalboardId)` | DELETE `/pedalboards/{id}/effects/{eid}` | Remove effect from pedalboard |
| `useSetParameter(pedalboardId, effectId, paramName)` | PUT `/pedalboards/{id}/effects/{eid}/parameters/{name}` | Set effect parameter |
| `useConnectPorts(pedalboardId)` | POST `/pedalboards/{id}/connections` | Create port connection |

---

## Data Flow

### Pedalboard Selection

```typescript
// PedalboardSelector receives props: selectedId, onSelect
const { data: pedalboards } = usePedalboards()
const selectMutation = useSelectPedalboard()

// On select: call onSelect(id), which updates App state
// Props flow from App.tsx -> PedalboardSelector
```

### Effect Management

```typescript
// EffectList receives pedalboardId as prop
const { data: pedalboard } = usePedalboard(pedalboardId)

// Inline parameter controls use useSetParameter hook
const setParameterMutation = useSetParameter(pedalboardId, effectId, paramName)
setParameterMutation.mutate(newValue)
```

### Parameter Updates (Optimistic)

```typescript
// ParameterControl receives: pedalboardId, effectId, paramName
const setParamMutation = useSetParameter(pedalboardId, effectId, paramName)

// On change: optimistic update with rollback on error
setParamMutation.mutate(newValue)
```

### Effect Addition Flow

```typescript
// EffectList triggers addition when ADD EFFECT clicked
const addEffectMutation = useAddEffect(pedalboardId)
addEffectMutation.mutate({ effect_uri })
// On success, pedalboard query auto-invalidates via hook's onSuccess
```

### Port Connection

```typescript
// Connection between effect ports
const connectMutation = useConnectPorts(pedalboardId)

connectMutation.mutate({ input_port_id, output_port_id })
```

---

## State Sharing Strategy

**Props-Based State (No URL)**

```typescript
// App.tsx
const [selectedPedalboardId, setSelectedPedalboardId] = useState<number | null>(null)

// PedalboardSelector calls onSelect(id)
<PedalboardSelector selectedId={selectedPedalboardId} onSelect={setSelectedPedalboardId} />

// EffectList receives pedalboardId as prop
<EffectList pedalboardId={selectedPedalboardId} />

// No URL state - simpler for single-page app
```

---

## OpenAPI Type Mapping

| Old Type | New Type | Notes |
|----------|----------|-------|
| `PedalboardInfo` | `Pedalboard` | `id`, `name`, `file`, `effects`, `connections` |
| `Plugin` | `EffectInstance` | `id`, `uri`, `ports`, `parameters` |
| `Port` | `Port` | API version (drop MIDI extras) |
| `ActiveEffect` | `EffectInstance` | Parameters included directly |