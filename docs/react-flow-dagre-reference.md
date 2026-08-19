# React Flow + Dagre: Functionality, Limitations & Usage

> Comprehensive reference for the React Flow + dagre integration in this Preact/compat
> project. Based on real development findings — not theoretical best practices.

---

## Table of Contents

1. [What Each Engine Does](#1-what-each-engine-does)
2. [Why Dagre Alone Is Insufficient](#2-why-dagre-alone-is-insufficient)
3. [Preact/Compat Integration](#3-preactcompat-integration)
4. [The Two-Pass Layout Pattern](#4-the-two-pass-layout-pattern)
5. [Handle Registration](#5-handle-registration)
6. [Port ID Consistency](#6-port-id-consistency)
7. [Replacing Dagre with Simple Topological Sort](#7-replacing-dagre-with-simple-topological-sort)
8. [Viewport & Coordinate Space](#8-viewport--coordinate-space)
9. [Common Pitfalls](#9-common-pitfalls)
10. [Working Configuration](#10-working-configuration)

---

## 1. What Each Engine Does

### React Flow (`@xyflow/react` v12)

Provides the **rendering engine** for node/edge diagrams:

- **Node rendering**: Renders custom React/Preact components at X/Y positions
  inside a viewport `<div>` with CSS transforms (pan, zoom)
- **Edge rendering**: Draws SVG `<path>` elements (Bezier curves) between
  handle positions, computed from the DOM
- **Handle system**: `<Handle>` components register connection points on nodes;
  edges look up handle positions via `internals.handleBounds`
- **Dimension measurement**: Internal `ResizeObserver` measures DOM node sizes
  and reports `onNodesChange({ type: 'dimensions' })` events
- **Store management**: Internal Zustand store holds nodes, edges, viewport,
  and handle bounds
- **Interaction**: Panning, zooming, selection, connection drawing, node dragging
- **Background grid**: `<Background>` component renders animated grid SVG
- **Viewport API**: `fitView()`, `getViewport()`, `setCenter()`, etc.

### Dagre (`@dagrejs/dagre` v3)

Provides **pure graph layout computation** — nothing more:

- Takes a `graphlib.Graph` with nodes (id, width, height) and edges (source, target)
- Computes X/Y positions using a Sugiyama-style hierarchical layout
- Returns positions; does NOT touch the DOM
- No rendering, no handles, no viewport, no interaction

### The Partnership

```
API Data (pedalboard, ports, connections)
    ↓
Build raw Nodes + Edges (id, type, data, sourceHandle, targetHandle)
    ↓
React Flow renders nodes at {0,0} → measures DOM → onNodesChange dims
    ↓                    ↘
Two-pass cycle:          → Layout engine (dagre/topo-sort) computes positions
  1. Measure  →          → setNodes(layouted)
  2. Position →          → fitView
```

---

## 2. Why Dagre Alone Is Insufficient

Dagre is a **layout algorithm**, not a UI library. You can't build a visual pedalboard
UI with dagre alone because:

| UI Requirement | Dagre Provides | Need From Elsewhere |
|---|---|---|
| Visual nodes on screen | ❌ | React Flow (or vanilla SVG) |
| Bezier curve edges | ❌ | React Flow (or manual SVG paths) |
| Handle/connection points | ❌ | React Flow (or manual DOM queries) |
| DOM dimension measurement | ❌ | React Flow's ResizeObserver (or manual polling) |
| Viewport pan/zoom | ❌ | React Flow (or CSS transforms) |
| Background grid | ❌ | React Flow's `<Background>` |
| Click-to-connect UX | ❌ | React Flow's connection mode |
| Node drag/drop | ❌ | React Flow interactions |

**Conclusion**: You need React Flow (or equivalent rendering layer) **plus** a layout
engine (dagre, topo-sort, or manual positioning). The layout engine only computes
numbers; the rendering layer draws pixels.

---

## 3. Preact/Compat Integration

### The Core Problem

This project uses Astro with Preact in **compat mode** (`react` is aliased to
`preact/compat`). React Flow v12 was built for React. The compatibility layer
has specific failure modes:

### StoreUpdater Prop→Store Sync Failure

React Flow's `StoreUpdater` component uses `useEffect` to sync props (`nodes`, `edges`)
to the internal Zustand store:

```javascript
// In StoreUpdater.jsx
useEffect(() => {
  if (fieldValue !== previousFieldValue) {
    store.setState({ nodes: fieldValue })  // reference equality check
  }
}, [fieldValue])
```

In Preact/compat, the `useSyncExternalStore` shim behaves differently, and the
reference equality check may prevent updates from propagating when `setNodes`
from `useState` creates new arrays but the store sync doesn't fire reliably.

**Fix**: Use `useNodesState`/`useEdgesState` hooks instead of `useState`:

```typescript
// ❌ Broken: useState + prop-passing
const [nodes, setNodes] = useState<Node[]>([])
<ReactFlow nodes={nodes} onNodesChange={onNodesChange} />

// ✅ Working: hooks write directly to the internal store
const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
<ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} />
```

### onNodesChange Dimension Events May Not Fire

React Flow measures DOM nodes via `ResizeObserver` and emits
`onNodesChange({ type: 'dimensions', ... })` events. In Preact/compat, these
events may not reach the component's state reliably, leaving `node.width`/`node.height`
as `null` indefinitely.

**Fix**: Implement a DOM-based dimension fallback using polling:

```typescript
useEffect(() => {
  if (!graphKey) return

  const pollDims = () => {
    if (!rfInstanceRef.current) return  // onInit fires async!
    
    const allHaveDims = nodes.every(n => n.width != null && n.height != null)
    if (allHaveDims) return

    setNodes((prev) => prev.map((n) => {
      if (n.width != null && n.height != null) return n
      const internal = rfInstanceRef.current?.getInternalNode(n.id)
      if (internal?.measured?.width && internal?.measured?.height) {
        const { width, height } = internal.measured
        if (width > 0 && height > 0) return { ...n, width, height }
      }
      // DOM fallback
      const el = document.querySelector('[data-id="' + n.id + '"]')
      if (!el) return n
      const rect = el.getBoundingClientRect()
      if (rect.width > 0 && rect.height > 0 && rect.width < 5000 && rect.height < 5000) {
        return { ...n, width: rect.width, height: rect.height }
      }
      return n
    }))
  }

  const interval = window.setInterval(pollDims, 50)
  pollDims()
  return () => clearInterval(interval)
}, [graphKey, nodes.length])
```

**Key insight**: The `rfInstanceRef.current` guard must be **inside** `pollDims`, not
in the effect's outer guard. Because `onInit` fires asynchronously (via `setTimeout`),
the instance may be `null` when the effect first runs but available on the next poll.

---

## 4. The Two-Pass Layout Pattern

### Phase 1: Measure

1. Nodes are rendered at `{x: 0, y: 0}` with no dimensions
2. React Flow's `ResizeObserver` measures DOM elements
3. Dimensions arrive via `onNodesChange` → `useNodesState` updates
4. **In Preact/compat**: events may not fire → dimension fallback polls `getInternalNode`

### Phase 2: Position

```typescript
// useLayoutEffect fires after every render
useLayoutEffect(() => {
  if (!pedalboard || !allPorts) return
  
  // Check all nodes have dimensions
  const current = nodes.filter(n => nodeIds.includes(n.id))
  const ready = current.length === nodeIds.length &&
    current.every(n => n.width != null && n.height != null)
  if (!ready) return  // Wait for measurement

  // Checksum to prevent re-entry
  const dimsKey = current.map(n => `${n.id}:${n.width}x${n.height}`).join('|')
  if (dimsKey === lastDimsKeyRef.current) return
  lastDimsKeyRef.current = dimsKey

  // Run layout
  const dimensions = new Map(current.map(n => [n.id, { width: n.width!, height: n.height! }]))
  const layouted = layoutNodes(current, edges, { centreX, topRowY, dimensions })
  if (!layouted) return

  setNodes(layouted)
  setCanvasHeight(computeCanvasHeight(layouted, dimensions))
}, [nodes, graphKey, nodeIds.length, pedalboard, allPorts])
```

**Critical**: `layoutNodes` must return `null` if any node lacks dimensions, so the
caller waits for the next measurement cycle.

### Deps Array Discipline

```typescript
// ✅ Correct: stable primitives only
}, [nodes, graphKey, nodeIds.length, pedalboard, allPorts])

// ❌ Infinite loop: rawNodes/rawEdges change every render
}, [nodes, graphKey, nodeIds, rawEdges, pedalboard, allPorts])
```

---

## 5. Handle Registration

### How Edges Find Their Handles

1. `<Handle id="effect_1:input" position={Position.Top} />` renders a DOM element
   with `data-handleid="effect_1:input"` inside the node
2. React Flow's `ResizeObserver` measures the handle and stores its position in
   `node.internals.handleBounds`
3. When rendering an edge, React Flow looks up `handleBounds[sourceNodeId][sourceHandleId]`
   to get the X/Y position for the Bezier curve start/end

### The ID Mapping Problem

**Node IDs** use hyphens: `effect-1`, `effect-8`
**Port IDs** use underscores: `effect_1:input`, `effect_8:output`

```typescript
// Node ID: built from effect_instance_id
id: `effect-${effectId}`  // "effect-1"

// Handle ID: built from portId(port)
portId(port)  // "effect_1:input" (underscore!)

// Edge: source = node ID, sourceHandle = port ID
{
  source: 'effect-1',        // node ID
  sourceHandle: 'effect_1:output',  // port ID
  target: 'effect-8',
  targetHandle: 'effect_8:input',
}
```

### The enrichment problem

The pedalboard API (`/api/effects/pedalboards/1`) returns effects with
`ports[].effect_instance_id = null`. React Flow can't match edges to handles.

**Fix**: Enrich ports from the `/ports` endpoint:

```typescript
const effectPorts = allPorts.filter(
  (p) => p.owner_type === 'effect' && p.effect_instance_id === effectId,
)
const enrichedEffect = {
  ...effect,
  ports: effectPorts.length > 0 ? effectPorts : effect.ports,
}
```

---

## 6. Port ID Consistency

The pedalboard API returns two different port data:

| Source | `effect_instance_id` | Used For |
|---|---|---|
| `/api/effects/pedalboards/{id}` | `null` | Building effect nodes (EffectNode) |
| `/api/effects/pedalboards/{id}/ports` | Correct (e.g., `1`) | Building edges, handle registration |

**If you use pedalboard API ports for Handle IDs, they'll be `effect_null:input`**
and won't match edge `sourceHandle: "effect_1:output"`.

**Always enrich**: Filter `allPorts` (from the `/ports` endpoint) and pass the
enriched ports to the EffectNode component.

---

## 7. Replacing Dagre with Simple Topological Sort

For pedalboard signal chains (essentially linear with possible branches),
dagre's hierarchical layout is overkill. A topological sort + vertical stacking
is sufficient and removes two npm dependencies.

### When to use each:

| Scenario | Dagre | Simple Sort |
|---|---|---|
| Linear signal chain (input → effect → output) | ✅ Works but overkill | ✅ Sufficient |
| Parallel branches (A → B, A → C) | ✅ Handles via rank assignment | ✅ Topological sort handles via queue |
| Multiple columns needed | ✅ Automatic | ❌ Single column only |
| Complex hierarchies | ✅ Rank-based grouping | ❌ Linear order |
| Dependencies | `@dagrejs/dagre`, `@dagrejs/graphlib` | None |

### Simple topological sort (Kahn's algorithm):

```typescript
function topologicalSort(nodeIds: string[], edges: Array<{ source: string; target: string }>): string[] {
  const idSet = new Set(nodeIds)
  const adj = new Map<string, string[]>()
  const inDegree = new Map<string, number>()

  for (const id of nodeIds) { adj.set(id, []); inDegree.set(id, 0) }
  for (const edge of edges) {
    if (idSet.has(edge.source) && idSet.has(edge.target)) {
      adj.get(edge.source)!.push(edge.target)
      inDegree.set(edge.target, (inDegree.get(edge.target) ?? 0) + 1)
    }
  }

  const order: string[] = []
  const queue = nodeIds.filter(id => (inDegree.get(id) ?? 0) === 0)
  while (queue.length > 0) {
    const current = queue.shift()!
    order.push(current)
    for (const next of adj.get(current)!) {
      inDegree.set(next, (inDegree.get(next) ?? 0) - 1)
      if (inDegree.get(next) === 0) queue.push(next)
    }
  }
  // Cycle fallback
  for (const id of nodeIds) if (!order.includes(id)) order.push(id)
  return order
}
```

### Layout positions:

- **System inputs**: `x = distributeHorizontally(count, LAYOUT_WIDTH, ~100)`, `y = TOP_ROW_Y`
- **Effects**: Stacked vertically at `x = centreX - width/2`, `y = cumulative (height + gap)`
- **System outputs**: `x = distributeHorizontally(...)`, `y = below lowest effect`

---

## 8. Viewport & Coordinate Space

### The Coordinate Problem

There are **three coordinate systems** at play:

1. **Flow coordinates**: X/Y stored in React Flow's node `position` (e.g., `{x: 33, y: 30}`)
2. **Viewport coordinates**: Flow coords transformed by viewport's `transform`
3. **DOM/visual coordinates**: Position on screen (from `getBoundingClientRect`)

### The Viewport Transform

`ReactFlowInstance.getViewport()` returns `{ x: panX, y: panY, zoom }`.
The CSS transform on `.react-flow__viewport` is `matrix(zoom, 0, 0, zoom, panX, panY)`.

**Key insight**: The pan values in a CSS matrix are **NOT scaled** by zoom.
The formula to convert flow → visual is:

```
visualX = containerOffsetX + flowX * zoom + panX
visualY = containerOffsetY + flowY * zoom + panY
```

NOT `(flowX + panX) * zoom` — that would incorrectly scale the pan.

### Overlay Elements

To position overlay divs (like visual row blocks) at flow coordinates:

```typescript
const viewport = rfInstanceRef.current.getViewport()
const tf = (x: number, y: number) => ({
  x: x * viewport.zoom + viewport.x,  // flow → viewport coords
  y: y * viewport.zoom + viewport.y,
})
const visualLeft = tf(flowX, flowY).x
const visualWidth = flowWidth * viewport.zoom
```

---

## 9. Common Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| "Loading pedalboard…" forever | Runtime crash (ReferenceError, null ref) | Check browser console; add error boundaries |
| Nodes render but `visibility: hidden` | Dimensions never set on nodes | Use `useNodesState` + dimension fallback polling |
| 0 edges in DOM, 0 handle errors | `handleBounds` not set (ResizeObserver not firing) | Dimension fallback triggers RF's internal measurement |
| "Couldn't create edge for handle id: X" | Handle ID mismatch | Enrich ports from `/ports` endpoint with `effect_instance_id` |
| Infinite re-renders | `rawNodes`/`rawEdges` in `useLayoutEffect` deps | Only use `graphKey` + primitive deps |
| `updateNodeInternals is not a function` | Called on `ReactFlowInstance` (not on hook) | Use `useUpdateNodeInternals()` hook, or rely on dimension fallback |
| `ReactFlowProvider` error #001 | `useUpdateNodeInternals` called outside RF context | Move the hook to a child component inside `<ReactFlow>` |
| `dimsFallbackRef is not defined` | Dangling reference after code edit | Audit all references when removing code |
| Row blocks misaligned with nodes | Incorrect viewport transform math | Formula is `flowX * zoom + panX`, NOT `(flowX + panX) * zoom` |
| `onInit` not fired | Async `setTimeout` — instance not ready | Move the `rfInstanceRef` guard inside the polling loop |

---

## 10. Working Configuration

### Astro + Preact/Compat (`astro.config.mjs`)

```js
import { defineConfig } from 'astro/config'
import preact from '@astrojs/preact'

export default defineConfig({
  integrations: [preact({
    compat: true,
    globals: true,
    renderToString: true,
  })],
  vite: {
    resolve: {
      alias: {
        react: 'preact/compat',
        'react/jsx-runtime': 'preact/jsx-runtime',
        'react-dom': 'preact/compat',
      },
    },
  },
})
```

### Docker Development (`test-dev-web-1`)

- Source mounted at `/workspace/services/web/preact/src:/app/src` (live-loads)
- No rebuild needed for code changes
- Port 80 via Traefik
- `DOCKER_API_VERSION=1.43` required for docker commands

### Data Flow Summary

```
PedalboardSelector
  → usePedalboards()        [GET /api/effects/pedalboards]
  → useCurrentPedalboard()  [GET /api/effects/pedalboards/current]
  → select mutation         [PUT /api/effects/pedalboards/{id}/select]
    ↓
PedalboardView(pedalboardId)
  → usePedalboard(id)       [GET /api/effects/pedalboards/{id}]
  → usePorts(id)            [GET /api/effects/pedalboards/{id}/ports]
  → useEffects()            [GET /api/effects]
    ↓
PedalboardDAG(pedalboardId)
  → Builds rawNodes + rawEdges (useMemo)
  → useNodesState / useEdgesState (React Flow hooks)
  → Dimension fallback (polling getInternalNode + DOM)
  → layoutNodes (simple topo sort) → setNodes(layouted)
  → fitView (after layout)
  → Renders <ReactFlow> + <Background> + visual row blocks
```
