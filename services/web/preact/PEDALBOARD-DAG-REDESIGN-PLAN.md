# Pedalboard DAG Redesign Plan

## Status: Draft for review (implement in fresh worktree)

---

## 1. Objective

Redesign the pedalboard effect DAG rendering to use **fully static, predefined dimensions** and **even port spreading**, eliminating all runtime dimension measurement, dagre dependency, and the two-pass measure-then-position cycle. The design scraps the current implementation and starts from scratch with a simpler approach.

---

## 2. Key Assumptions

| # | Assumption | Impact |
|---|---|---|
| 1 | **All effects are static** — predefined fixed dimensions | No DOM measurement, no `onNodesChange('dimensions')`, no fallback polling |
| 2 | **EffectNode shows only: name, status line, ports** — no inline parameter controls | Fixed `220×72px` height; parameters moved to a side panel via selection |
| 3 | **Ports spread evenly** — top edge for inputs, bottom edge for outputs | New `spreadPortsEvenly()` utility; handles positioned at computed X offsets |
| 4 | **System ports divide available width evenly** | `systemPortWidth(count) = LAYOUT_WIDTH / count` |
| 5 | **Handles are invisible** but functional for edge routing | `width:0, height:0, opacity:0` — edges attach to specific port positions, no visual clutter |
| 6 | **All nodes non-draggable** — static canvas | Constraints preserved from current implementation |
| 7 | **Parameters adjusted via click-to-select → side panel** | Click effect node → ParameterPanel appears with sliders/dropdowns |

---

## 3. Current State Analysis

### What exists today

| File | Role | Issues addressed by redesign |
|---|---|---|
| `src/lib/layout.ts` | Topological sort + stacking | Uses `dimensions` Map for measured sizes; `distributeHorizontally` with fixed node width |
| `src/components/PedalboardDAG.tsx` | Main DAG component | 523 lines; two-pass measure→position cycle; dimension-fallback polling; debug overlay; viewport transform math for row blocks |
| `src/components/nodes/EffectNode.tsx` | Effect card with params | Has inline `ParameterControl` (sliders/dropdowns); height varies per param count |
| `src/components/nodes/SystemPortNode.tsx` | System I/O port | Fixed `w-6 h-6` circle; width not tracked for layout |
| `src/components/ParameterControl.tsx` | Slider/dropdown controls | Reused — will move to side panel |
| `src/lib/portUtils.ts` | Port ID utilities | `portId()`, `classifyPorts()`, `portHandleType()`, `nodeIdForPortId()` — **unchanged** |
| Mock API (`mock-api.js`) | Test data | Pedalboard #1: 2 effects, 3 connections, 4 system ports |

### Current problems being fixed

1. **Preact/compat dimension sync failure** — `onNodesChange('dimensions')` events don't reliably reach component state in Preact/compat, causing `node.width`/`node.height` to stay `null` → nodes invisible (`visibility: hidden`) → layout never triggers
2. **StoreUpdater prop→store sync failure** — edges passed as `useMemo` props don't trigger Zustand store updates reliably → edges never render
3. **Dimensional estimate drift** — hardcoded height estimates don't match actual rendered sizes of sliders/dropdowns/labels
4. **Over-engineered** — viewport transform math, overlay divs, 523-line component, dimension-fallback polling cycle

---

## 4. New Architecture

### 4.1 Data Flow (One-Pass, No Measurement)

```
API Data (pedalboard + ports + catalog + modelFiles)
    ↓
useMemo → build rawNodes (FIXED dimensions baked in) + rawEdges
    ↓
useEffect[graphKey] → setNodes(rawNodes), setRfEdges(rawEdges)
    ↓
useLayoutEffect[graphKey, nodes.length] → layoutNodes(nodes, rfEdges)
    → returns layouted nodes with positions
    → setNodes(layouted) → fitView()
```

**Why this works without measurement:**
- Every node's `width` and `height` are known constants at construction time
- `layoutNodes` can immediately compute positions — no waiting for ResizeObserver
- No `dimsKey` guard needed — there's only one layout pass
- No polling, no refs for dimension state, no debug overlay

**Preact/compat edge decision:** We use `useEdgesState` (writes directly to internal store, bypassing broken `StoreUpdater` prop→store sync) for edges. Plain `useState` is sufficient for nodes since node changes are full-array replacements on `graphKey` changes (new reference every time), which the `StoreUpdater` reliably detects.

### 4.2 Component Hierarchy

```
PedalboardView
├── ADD EFFECT Button + Dialog (unchanged)
├── ParameterPanel (NEW — side panel for selected effect)
└── PedalboardDAG
    ├── ReactFlow (static canvas)
    │   ├── Background (LCD amber grid)
    │   ├── EffectNode × N (220×72, invisible evenly-spread handles)
    │   ├── SystemPortNode × M (even-width, invisible handle)
    │   └── Edges (amber, animated, route to invisible handles)
    └── (debug overlay removed)
```

---

## 5. File-by-File Changes

### 5.1 `src/lib/layout.ts` — REWRITE

**Replace** the current measurement-driven layout with a static one.

#### New constants:
```ts
export const LAYOUT_WIDTH = 300
export const EFFECT_NODE_WIDTH = 220
export const EFFECT_NODE_HEIGHT = 72       // ← STATIC, no param-based calculation
export const TOP_ROW_Y = 30
export const EFFECT_NODE_GAP = 32
const OUTPUT_GAP = 40
const INPUT_ROW_CLEARANCE = 16
const MAX_CANVAS_HEIGHT = 720
```

#### New/removed functions:

| Function | Status | Notes |
|---|---|---|
| `layoutNodes(nodes, edges, options)` | **Keep** | No longer takes `dimensions` Map; reads `node.width`/`node.height` (baked at construction) |
| `computeCanvasHeight(nodes, maxHeight)` | **Keep** | Uses `node.height` directly |
| `topologicalSort(ids, edges)` | **Keep** | Same Kahn's algorithm |
| `spreadPortsEvenly(count, containerWidth)` | **ADD** | Returns evenly-spaced X offsets for handles |
| `systemPortWidth(countInRow)` | **ADD** | Returns `LAYOUT_WIDTH / count` |
| `effectNodeDimensions()` | **ADD** | Returns `{ width: 220, height: 72 }` |
| `distributeHorizontally()` | **Remove** | Replaced by `systemPortWidth` + index-based positioning |
| `LayoutDimensions` interface | **Remove** | Not needed |
| `LayoutOptions.dimensions` field | **Remove** | No measurement needed |

#### `layoutNodes` signature change:
```ts
// AFTER (new):
export function layoutNodes(
  nodes: Node[],
  edges: Array<{ source: string; target: string }>,
  options: LayoutOptions = {},  // NO dimensions Map
): Node[] | null
```

**No `null` return for missing dimensions** — all dimensions are constants, always present. Only returns `null` when `nodes.length === 0` as a safety guard.

#### Layout logic:
```
1. Partition: systemInputs, systemOutputs, effects
2. Topological sort effect IDs
3. Stack effects vertically:
   cursorY = TOP_ROW_Y + INPUT_ROW_CLEARANCE
   for id in topoOrder:
     x = centreX - EFFECT_NODE_WIDTH/2
     y = cursorY
     cursorY += EFFECT_NODE_HEIGHT + EFFECT_NODE_GAP
4. System inputs: evenly divided width
   inputW = LAYOUT_WIDTH / inputs.length
   each: x = idx * inputW, y = TOP_ROW_Y
5. System outputs: same, at outputRowY = cursorY + OUTPUT_GAP
6. Return nodes with positions set
```

### 5.2 `src/components/nodes/EffectNode.tsx` — REWRITE

**Scrap** the current parameter-controls-in-node approach. Replace with a simplified card.

#### Props / Data:
```ts
export interface EffectNodeData {
  pedalboardId: number
  effectId: number
  effect: EffectInstance
  catalogEntry?: EffectInfo
  modelFiles?: FileInfo[]
  isSelected: boolean              // ← NEW — for selection highlighting
  onSelect: (effectId: number) => void  // ← NEW — opens side panel
  onPortClick: (portId: string, handleType: HandleType) => void
  selectedPortId: string | null    // ← for port highlight during click-to-connect
  onRemoveEffect: (effectId: number) => void
}
```

#### Rendering (fixed 220×72 layout):
```
┌────────────────────────────────────── (220px wide, 72px tall)
│ [in●  in●]                        X │  ← input handles (invisible, evenly spread) + remove btn
│                                    │
│ Effect Name          Status: OK    │  ← name (text-xs) + single-line status
│                                    │
│ [out● out●]                       │  ← output handles (invisible, evenly spread)
└──────────────────────────────────────
```

**Details:**
- Input handles: `Position.Top`, invisible (`0×0, opacity:0, pointerEvents:none`), X offset from `spreadPortsEvenly(inputCount, 220)`
- Output handles: `Position.Bottom`, same technique
- Visible port circles: 5px, `bg-lcd-400`, positioned at same X offsets via inline `style={{ left: offset - 2.5 }}` — these are the clickable elements that call `onPortClick` for click-to-connect UX. The invisible `<Handle>` components sit behind them for edge attachment.
- The entire node is clickable for selection (calls `onSelect(effectId)`) — except the port circles and remove button which stop propagation.
- No `ParameterControl` imports. No sliders/dropdowns inside.

#### Status line:
A simple single-line status derived from the effect's parameters. For now: `Status: OK` (placeholder — can show param count or a model status). This is a text-only line, no interactive controls.

### 5.3 `src/components/nodes/SystemPortNode.tsx` — MODIFY

Make the `<Handle>` invisible (same technique as EffectNode). Width/height set externally by layout.

```tsx
<Handle
  type={handleType}
  position={handlePosition}
  id={pid}
  isConnectable={false}
  style={{ width: 0, height: 0, opacity: 0, pointerEvents: 'none' }}
/>
```

The visible circle (`w-6 h-6`) + label remain visible and clickable. Width is set externally by the layout (`LAYOUT_WIDTH / count`). The node component itself uses `w-full` so it fills the assigned slot.

### 5.4 `src/components/PedalboardDAG.tsx` — REWRITE

**Scrap** the 523-line current implementation. Replace with a ~180-line component.

#### Imports (added/removed):
- **ADD**: `useEdgesState` from `@xyflow/react`
- **ADD**: `useState` for `canvasHeight` and `selectedEffectId`
- **REMOVE**: `useLayoutEffect` dimension guards, `lastDimsKeyRef`, all position refs

#### State (simplified):
```tsx
const [nodes, setNodes] = useState<Node[]>([])
const [rfEdges, setRfEdges, onRfEdgesChange] = useEdgesState<Edge>([])
const [canvasHeight, setCanvasHeight] = useState<number>(300)
const [selectedPortId, setSelectedPortId] = useState<string | null>(null)
const [selectedEffectId, setSelectedEffectId] = useState<number | null>(null)
const rfInstanceRef = useRef<ReactFlowInstance | null>(null)
```

#### Build raw nodes with FIXED dimensions (useMemo):
```tsx
const { rawNodes, rawEdges, nodeIds } = useMemo(() => {
  if (!pedalboard || !allPorts) return { rawNodes: [], rawEdges: [], nodeIds: [] }

  // System ports: fixed height=44, width=LAYOUT_WIDTH/count
  const inputW = systemPortWidth(sysInputs.length)
  const outputW = systemPortWidth(sysOutputs.length)

  const inputNodes = sysInputs.map(port => ({
    id: portId(port),
    type: 'systemPort',
    position: { x: 0, y: 0 },
    width: inputW,
    height: 44,
    data: { port, isSelected: false, onClick: handlePortClick },
    draggable: false,
    connectable: false,
  }))

  // Effect nodes: fixed 220×72
  const effectNodes = Object.entries(pedalboard.effects).map(([id, effect]) => ({
    id: `effect-${effectId}`,
    type: 'effectNode',
    position: { x: 0, y: 0 },
    width: EFFECT_NODE_WIDTH,
    height: EFFECT_NODE_HEIGHT,
    data: {
      pedalboardId,
      effectId,
      effect: enrichedEffect,
      catalogEntry,
      modelFiles,
      isSelected: effectId === selectedEffectId,
      selectedPortId,
      onSelect: setSelectedEffectId,
      onPortClick: handlePortClick,
      onRemoveEffect: handleRemoveEffect,
    },
    draggable: false,
    connectable: false,
  }))

  // Edges from real connections (unchanged)
  const edgeList = Object.values(pedalboard.connections).map(conn => ({
    id: `e-${conn.id}`,
    source: nodeIdForPortId(conn.output_port_id),
    target: nodeIdForPortId(conn.input_port_id),
    sourceHandle: conn.output_port_id,
    targetHandle: conn.input_port_id,
    animated: true,
    style: { stroke: AMBER, strokeWidth: 2 },
  }))

  return { rawNodes: [...inputNodes, ...effectNodes, ...outputNodes], rawEdges: edgeList, nodeIds: [...] }
}, [pedalboard, allPorts, effectCatalog, modelFiles, selectedPortId, selectedEffectId])
```

#### graphKey (unchanged):
```tsx
const graphKey = useMemo(() => {
  if (!pedalboard || !allPorts) return ''
  return `${pedalboard.id}:${Object.keys(pedalboard.effects).sort().join(',')}:${Object.keys(pedalboard.connections).sort().join(',')}`
}, [pedalboard, allPorts])
```

#### Reset on graphKey change (simplified):
```tsx
useEffect(() => {
  if (!graphKey) return
  setNodes(rawNodes)
  setRfEdges(rawEdges)
  setSelectedEffectId(null)
  setSelectedPortId(null)
}, [graphKey])
```

#### ONE layout pass (dimensions are known):
```tsx
useLayoutEffect(() => {
  if (!graphKey || nodes.length === 0) return
  const layouted = layoutNodes(nodes, rfEdges, {
    centreX: LAYOUT_WIDTH / 2,
    topRowY: TOP_ROW_Y,
  })
  if (!layouted) return
  setNodes(layouted)
  setCanvasHeight(computeCanvasHeight(layouted))
  rfInstanceRef.current?.fitView({ padding: 0.2, minZoom: 0.4, maxZoom: 1.5 })
}, [graphKey, nodes.length])
```

#### React Flow render (simplified):
```tsx
return (
  <div className="border-2 border-lcd-400 rounded-sm bg-black overflow-hidden mx-auto relative"
       style={{ width: `${LAYOUT_WIDTH}px`, height: `${canvasHeight}px` }}>
    <ReactFlow
      nodes={nodes}
      edges={rfEdges}
      onEdgesChange={onRfEdgesChange}
      nodeTypes={nodeTypes}
      onInit={(instance) => { rfInstanceRef.current = instance }}
      onPaneClick={() => { setSelectedPortId(null); setSelectedEffectId(null) }}
      onEdgeDelete={onEdgeDelete}
      connectionMode="loose"
      fitView
      fitViewOptions={{ padding: 0.2, minZoom: 0.4, maxZoom: 1.5 }}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      panOnDrag={false}
      panOnScroll={false}
      zoomOnScroll={false}
      zoomOnPinch={false}
      zoomOnDoubleClick={false}
      preventScrolling={true}
      proOptions={{ hideAttribution: true }}
    >
      <Background color={AMBER} gap={20} />
    </ReactFlow>
  </div>
)
```

**Removed:**
- `onNodesChange` prop (no `onNodesChangeHandler` — no dynamic node changes)
- Dimension-fallback polling (`setInterval`, `getInternalNode`, `getBoundingClientRect`)
- `lastDimsKeyRef` checksum guard
- All position refs (`inputRowYRef`, `outputRowYRef`, `inputRowBoxRef`, `outputRowBoxRef`)
- Viewport transform math (`tf()` function, row block overlay `<div>`s)
- Debug overlay `<div>`

**Kept:**
- `useEdgesState` hook (Preact/compat store sync safety for edges)
- Click-to-connect state machine (`selectedPortId`, `handlePortClick`)
- `onEdgeDelete` → `deleteConnection`
- `onPaneClick` clears selection
- `graphKey`-driven reset
- `fitView` after layout and on graphKey reset

### 5.5 `src/components/ParameterPanel.tsx` — NEW

Side panel showing parameter controls for the selected effect. Reuses `ParameterControl`.

```tsx
export default function ParameterPanel({
  selectedEffectId,
  pedalboard,
  effectCatalog,
  modelFiles,
  onClose,
}: ParameterPanelProps) {
  if (!selectedEffectId || !pedalboard) return null

  const effect = pedalboard.effects[selectedEffectId]
  if (!effect) return null

  const catalogEntry = effectCatalog?.find((e) => e.uri === effect.uri)
  const paramCount = Object.keys(effect.parameters).length

  return (
    <div className="fixed top-16 right-4 w-64 lcd-panel p-3 z-40 max-h-[calc(100vh-80px)] overflow-y-auto">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lcd-200 text-xs font-bold">
          {catalogEntry?.name ?? effect.name ?? 'Effect'} — Params
        </h3>
        <button
          className="text-lcd-300 hover:text-lcd-200 text-xs"
          onClick={onClose}
        >
          ✕
        </button>
      </div>

      {paramCount === 0 ? (
        <p className="text-lcd-400 text-xs">No parameters</p>
      ) : (
        <div className="space-y-2">
          {Object.entries(effect.parameters).map(([name, param]) => (
            <ParameterControl
              key={name}
              pedalboardId={pedalboard.id}
              effectId={selectedEffectId}
              paramName={name}
              param={param as Parameter}
              modelFiles={modelFiles ?? undefined}
            />
          ))}
        </div>
      )}
    </div>
  )
}
```

### 5.6 `src/components/PedalboardView.tsx` — MODIFY

Add `ParameterPanel` and fetch hooks for pedalboard + model files.

```tsx
// Add imports:
import { usePedalboard } from '../api/hooks/usePedalboard'
import { useModelFiles } from '../api/hooks/useModelFiles'
import ParameterPanel from './ParameterPanel'

// In component body:
const [selectedEffectId, setSelectedEffectId] = useState<number | null>(null)
const { data: pedalboard } = usePedalboard(pedalboardId)
const { data: modelFiles } = useModelFiles()

// In render:
<PedalboardDAG
  pedalboardId={pedalboardId}
  selectedEffectId={selectedEffectId}
  onSelectEffect={setSelectedEffectId}
/>
<ParameterPanel
  selectedEffectId={selectedEffectId}
  pedalboard={pedalboard}
  effectCatalog={effectCatalog}
  modelFiles={modelFiles}
  onClose={() => setSelectedEffectId(null)}
/>
```

### 5.7 `src/lib/portUtils.ts` — NO CHANGE

All port ID utilities remain identical.

### 5.8 Files NOT touched

| File | Reason |
|---|---|
| Mock API (`mock-api.js`) | Test data is correct |
| `src/api/types.ts` | Types are correct |
| All API hooks | Unchanged |
| `src/components/Select.tsx` | Reused by ParameterControl → ParameterPanel |
| `src/components/TestPedalboardDAG.tsx` | Still renders `<PedalboardDAG>` |
| `src/components/DebugDAG.tsx` | Still renders `<PedalboardDAG>` |
| `src/pages/test-pedalboard-dag.astro` | Unchanged |
| `test-pedalboard-dag-render.cjs` | Verification script — still valid |
| `astro.config.mjs` / `astro.config.dev.mjs` | No dependency changes |
| `package.json` | No dep changes (dagre already removed) |

---

## 6. Constants Summary

```ts
// layout.ts
LAYOUT_WIDTH = 300        // Canvas width
EFFECT_NODE_WIDTH = 220   // All effect nodes (fixed)
EFFECT_NODE_HEIGHT = 72   // All effect nodes (fixed — no param-based calc)
TOP_ROW_Y = 30            // Y for system input row
EFFECT_NODE_GAP = 32      // Vertical gap between stacked effects
OUTPUT_GAP = 40           // Gap between last effect and output row
INPUT_ROW_CLEARANCE = 16  // Gap between input row and first effect
MAX_CANVAS_HEIGHT = 720   // Cap on canvas height

// SystemPortNode
SYSTEM_PORT_HEIGHT = 44   // Circle (24px) + label + padding
SYSTEM_PORT_WIDTH = LAYOUT_WIDTH / count_in_row  // Even division
```

---

## 7. Constraints Checklist

| Constraint | Status | How |
|---|---|---|
| System input ports pinned to top row | ✅ | `layoutNodes` pins to `TOP_ROW_Y` |
| System output ports pinned to bottom | ✅ | `layoutNodes` pins to `outputRowY` |
| Effects in single centered column | ✅ | `centreX - EFFECT_NODE_WIDTH/2` |
| Effects ordered by signal-flow topology | ✅ | `topologicalSort` of real edges |
| All nodes non-draggable | ✅ | `nodesDraggable={false}` |
| All nodes non-connectable via drag | ✅ | `nodesConnectable={false}`, `connectionMode="loose"` |
| Click-to-connect only | ✅ | `handlePortClick` state machine |
| Effects non-deletable via keyboard | ✅ | `deleteKeyCode={null}` |
| Branches don't overlap | ✅ | Same-rank effects stagger via topo sort FIFO |
| No dagre dependency | ✅ | Topological sort replaces it |
| No runtime measurement | ✅ | All dimensions are constants |
| No two-pass measure→position cycle | ✅ | One-pass layout after raw node set |
| Handles invisible, no visual clutter | ✅ | `width:0, height:0, opacity:0, pointerEvents:none` |
| Edges route to specific ports | ✅ | Invisible handles at port positions |
| Parameters in side panel, not inline | ✅ | `ParameterPanel` triggered by effect selection |

---

## 8. Preact/Compat Risk Mitigation

The redesign **eliminates** the root causes of all known Preact/compat failures documented in `docs/react-flow-dagre-reference.md`:

| Old Problem | Root Cause | Eliminated By |
|---|---|---|
| Nodes render but `visibility: hidden` | Dimensions never set on nodes | Dimensions are constants, set at construction |
| 0 edges, no handle errors | `handleBounds` not set (ResizeObserver not firing) | Fixed width/height on nodes lets RF compute handleBounds from initial render; invisible handles still register |
| "Couldn't create edge for handle id" | Handle ID mismatch | Same portUtils logic — unchanged |
| Infinite re-renders | `rawNodes`/`rawEdges` in deps | `useLayoutEffect` deps are only `[graphKey, nodes.length]` |
| `onNodesChange` not firing | Preact compat dim events lost | Not listening for dim events at all — no `onNodesChange` / `onNodesChangeHandler` |
| `rfInstanceRef` not ready | Async `onInit` | `fitView` in `useLayoutEffect` guards with `rfInstanceRef.current` check |
| `StoreUpdater` prop→store sync failure (edges) | Reference equality check doesn't fire for prop-passed edges | **Use `useEdgesState`** hook (writes directly to internal store) |

**Edge store sync decision:** The reference doc confirms that `useEdgesState` from `@xyflow/react` writes directly to the internal Zustand store, bypassing the broken `StoreUpdater` prop→store sync. Since edges are a known failure mode in Preact/compat, we use `useEdgesState` for edges. For nodes, plain `useState` is sufficient because node changes are full-array replacements on `graphKey` changes (new reference every time), and the `StoreUpdater` reliably detects reference changes for full-array replacements.

**Implementation note:** `useEdgesState` returns `[edges, setEdges, onEdgesChange]`. We use `setEdges` for the graphKey reset and `onEdgesChange` is passed to `<ReactFlow>` for edge deletion handling (the `onEdgeDelete` callback fires through `onEdgesChange`).

---

## 9. Implementation Order

1. **`src/lib/layout.ts`** — rewrite with static constants, `spreadPortsEvenly`, `systemPortWidth`, `effectNodeDimensions`
2. **`src/components/nodes/EffectNode.tsx`** — rewrite as simplified card with invisible evenly-spread handles
3. **`src/components/nodes/SystemPortNode.tsx`** — modify handle to invisible
4. **`src/components/ParameterPanel.tsx`** — create side panel
5. **`src/components/PedalboardDAG.tsx`** — rewrite as one-pass static layout
6. **`src/components/PedalboardView.tsx`** — integrate ParameterPanel + selection callbacks + fetch hooks
7. **Build + verify** in Docker (`node:22 npm run build`)
8. **Runtime test** — Playwright against mock API dev server

---

## 10. Verification Plan

### Build check
```bash
cd services/web/preact
DOCKER_API_VERSION=1.43 docker run --rm -v "$PWD:/app" -w /app node:22 npm run build
```

### Runtime test (if Docker available)
```bash
# Start mock API + dev server
node mock-api.js &    # port 8001
ASTRO_CONFIG_FILE=astro.config.dev.mjs npx astro dev --host 0.0.0.0 --port 4322 &

# Run Playwright test
node test-pedalboard-dag-render.cjs http://localhost:4322/test-pedalboard-dag
```

### Expected results
- 6 nodes render (2 effects + 4 system ports)
- 3 edges render as SVG paths
- 8 handles (invisible but present in DOM)
- No console errors
- Canvas height properly computed (no scrollbar/clipping)

### Notes
- Node/Docker runtime is NOT available in this environment (see memory)
- Build verification must run on a machine with `node:22`
- The `test-pedalboard-dag-render.cjs` script expects 6 nodes, 3 edges — it reports handles count but doesn't assert on 12

---

## 11. Rollback Plan

If the new design fails:
- All changes are in a fresh worktree — the main workspace is untouched
- Simply remove the worktree directory to discard
- Original implementation remains intact in the main worktree at `services/web/preact/src/`
