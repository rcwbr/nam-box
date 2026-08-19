# React Flow + Dagre Layout Guide (Preact/Compat)

> Practical guide for implementing a React Flow DAG with dagre layout in a Preact/compat environment. This document captures the implementation decisions, pitfalls, and working patterns discovered during development.

## 1. Core Architecture

### 1.1 Node/Edge State Management

**Required pattern**: Use `useNodesState` and `useEdgesState` from `@xyflow/react`.

**Why not `useState`?** — In Preact/compat, the `StoreUpdater` component's `useEffect`-based prop→store sync uses reference equality on `fieldsToTrack` (`nodes`, `edges`). When you pass `nodes={nodes}` from `useState`, the `StoreUpdater`'s `useEffect` fires and calls `setNodes` on the internal store. But in Preact, this effect doesn't reliably trigger a store re-render that cascades to edge handle registration. Result: nodes may render, but edges don't find their handles → "Couldn't create edge for handle id: …" warnings.

**Working pattern:**

```tsx
const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
```

These hooks write directly to the internal Zustand store, bypassing the broken prop→store sync path.

### 1.2 Node Types Registration

Register custom node types via the `nodeTypes` prop on `<ReactFlow>`. Use `useMemo` to keep the object reference stable (Preact/compat may otherwise trigger unnecessary re-renders):

```tsx
const nodeTypes = useMemo(() => ({
  systemPort: SystemPortNode,
  effectNode: EffectNode,
}), [])
```

### 1.3 React Flow Instance

Use `onInit` to capture a ref to the `ReactFlowInstance` for programmatic operations (fitView, getInternalNode):

```tsx
const rfInstanceRef = useRef<ReactFlowInstance<Node, Edge> | null>(null)
// ...
<ReactFlow onInit={(instance) => { rfInstanceRef.current = instance }} />
```

**Important**: `onInit` fires asynchronously (via `setTimeout`), so `rfInstanceRef.current` may be `null`
when effects first run. The dimension fallback must handle this by checking inside the polling loop
rather than as a guard at the effect level.

## 2. Handle Registration (Critical)

### 2.1 The Problem

React Flow renders edges in an SVG pane by looking up `sourceHandle` and `targetHandle` positions from the internal node's `internals.handleBounds`. These bounds are populated by:

1. The internal `ResizeObserver` callback (fires when node DOM elements resize)
2. `updateNodeInternals()` calls (manually triggered)

In Preact/compat, the `ResizeObserver` callback may not fire reliably after node dimensions change (especially when dimensions are set programmatically rather than through DOM measurement). If `handleBounds` are never set, edges can't find their handles → "error#008" warnings and no edge paths in the DOM.

### 2.2 The Solution

**`useUpdateNodeInternals` requires ReactFlow context** — it cannot be called from the parent component level (outside `<ReactFlow>`). The `ReactFlowInstance` returned by `onInit` does NOT expose `updateNodeInternals` as a method.

In practice, the dimension fallback (Section 3.2) that sets node widths/heights via `setNodes` triggers React Flow's own internal measurement cycle, which sets `handleBounds` correctly. The `updateNodeInternals` hook is only needed as a safety net when measurement fails — in which case it should be called from within custom node components (which run inside the ReactFlow context):

```tsx
// Inside a custom node component:
import { useUpdateNodeInternals } from '@xyflow/react'
function EffectNode({ data }: { data: EffectNodeData }) {
  const updateNodeInternals = useUpdateNodeInternals()
  const nodeId = useNodeId()
  // ...after dimension changes:
  updateNodeInternals(nodeId)
}
```

If edges still don't render, the root cause is likely **handle ID mismatch** (Section 4), not missing `updateNodeInternals` calls.

## 3. Two-Pass Layout: Measure → Position

### 3.1 The Flow

```tsx
// Pass 1: Nodes render at {x:0, y:0}; React Flow measures their DOM dimensions
// via ResizeObserver and emits onNodesChange({ type: 'dimensions', dimensions: {width, height} })
// These dimensions land in our nodes state via useNodesState's applyNodeChanges.

// Pass 2: Once all nodes have width/height, run dagre layout
useLayoutEffect(() => {
  const current = nodes.filter(n => nodeIds.includes(n.id))
  const ready = current.length === nodeIds.length &&
    current.every(n => n.width != null && n.height != null)
  if (!ready) return

  const dimensions = new Map(
    current.map(n => [n.id, { width: n.width!, height: n.height! }]),
  )
  const layouted = layoutNodes(current, edges, { centreX, topRowY, dimensions })
  if (!layouted) return

  setNodes(layouted)
  setCanvasHeight(computeCanvasHeight(layouted, dimensions))
}, [nodes, graphKey, nodeIds.length])
```

### 3.2 Preact/Compat Dimension Pitfall

**Critical**: `onNodesChange` dimension events may NOT fire in Preact/compat. The `useSyncExternalStore` shim that `@xyflow/react` bundles checks for `window.useSyncExternalStore` — if Preact provides it, it uses Preact's implementation. The reference equality in the `StoreUpdater` may prevent updates from propagating.

**Workaround**: Implement a DOM-based dimension fallback that polls for measured dimensions:

```tsx
useEffect(() => {
  if (!pedalboard || !allPorts || !graphKey) return
  
  const pollDims = () => {
    // Guard inside the loop — onInit fires async, so instance may be null initially
    if (!rfInstanceRef.current) return
    
    const allHaveDims = nodes.every(n => n.width != null && n.height != null)
    if (allHaveDims) return
    
    let updated = false
    setNodes((prev) => prev.map((n) => {
      if (n.width != null && n.height != null) return n
      // Try internal store first
      const internal = rfInstanceRef.current?.getInternalNode(n.id)
      if (internal) {
        const { width, height } = internal.measured ?? {}
        if (width && height && width > 0 && height > 0) {
          updated = true
          return { ...n, width, height }
        }
      }
      // Fall back to DOM
      const el = document.querySelector<HTMLElement>('[data-id="' + n.id + '"]')
      if (!el) return n
      const rect = el.getBoundingClientRect()
      if (rect.width > 0 && rect.height > 0 && rect.width < 5000 && rect.height < 5000) {
        updated = true
        return { ...n, width: rect.width, height: rect.height }
      }
      return n
    }))
  }

  const interval = window.setInterval(pollDims, 50)
  pollDims()
  return () => clearInterval(interval)
}, [graphKey, pedalboard?.id, nodes.length])
```

### 3.3 Deps Array Discipline

**DO NOT** put `rawNodes`/`rawEdges` in `useLayoutEffect` deps. The `useMemo` that builds them re-runs every render (because it depends on callbacks like `handlePortClick`), creating new array references. This triggers infinite re-render loops.

**DO** use stable primitives:
```tsx
// ✅ Correct deps
}, [nodes, graphKey, nodeIds.length, pedalboard, allPorts])

// ❌ Causes infinite loop
}, [nodes, graphKey, nodeIds, rawEdges, pedalboard, allPorts])
```

## 4. Port ID Consistency

### 4.1 The Problem

The pedalboard API (`/api/effects/pedalboards/{id}`) returns effect ports with `effect_instance_id: null`. The `/ports` endpoint (`/api/effects/pedalboards/{id}/ports`) returns the same ports with `effect_instance_id` correctly set.

If you use the effect's ports from the pedalboard response, `portId()` produces `effect_null:input` — which won't match the edge's `sourceHandle: "effect_1:input"`.

### 4.2 The Solution: Enrich Port Data

When building effect nodes, enrich the ports with the correct `effect_instance_id` from the `/ports` endpoint:

```tsx
const effectEntries = Object.entries(pedalboard.effects)
const effectNodes = effectEntries.map(([id, effect]) => {
  const effectId = Number(id)
  
  // Enrich ports with effect_instance_id from the /ports endpoint
  const effectPorts = allPorts.filter(
    (p) => p.owner_type === 'effect' && p.effect_instance_id === effectId,
  )
  const enrichedEffect = {
    ...effect,
    ports: effectPorts.length > 0 ? effectPorts : effect.ports,
  }
  
  return {
    id: `effect-${effectId}`,
    type: 'effectNode',
    data: { effect: enrichedEffect, ... },
  }
})
```

## 5. Edge Construction

Edges must reference:
- `source`: The **node ID** of the source (e.g., `"effect-1"` or `"system:capture_1"`)
- `target`: The **node ID** of the target
- `sourceHandle`: The **port ID** (e.g., `"effect_1:output"` or `"system:capture_1"`)
- `targetHandle`: The **port ID** (e.g., `"effect_1:input"` or `"system:playback_1"`)

Use a `nodeIdForPortId()` helper to map port IDs to node IDs:

```tsx
const edgeList = Object.values(pedalboard.connections).map((conn) => ({
  id: `e-${conn.id}`,
  source: nodeIdForPortId(conn.output_port_id),
  target: nodeIdForPortId(conn.input_port_id),
  sourceHandle: conn.output_port_id,
  targetHandle: conn.input_port_id,
  // ...
}))
```

## 6. Graph Key Pattern (Reset on Structure Change)

Use a composite key to trigger a full reset of nodes+edges when the pedalboard structure changes (add/remove effect, add/remove connection):

```tsx
const graphKey = useMemo(() => {
  if (!pedalboard || !allPorts) return ''
  return `${pedalboard.id}:${Object.keys(pedalboard.effects).join(',')}:${Object.keys(pedalboard.connections).join(',')}`
}, [pedalboard, allPorts])

// Reset state only when graphKey changes (not when rawNodes/rawEdges change)
useEffect(() => {
  if (!graphKey) return
  setNodes(rawNodes)
  setEdges(rawEdges)
  lastDimsKeyRef.current = ''
}, [graphKey])
```

## 7. Viewport Management

### 7.1 Fit View

Call `fitView` after layouted nodes have non-zero positions:

```tsx
useEffect(() => {
  if (rfInstanceRef.current && nodes.length > 0) {
    const laidOut = nodes.some(n => n.position.x !== 0 || n.position.y !== 0)
    if (laidOut) {
      rfInstanceRef.current.fitView({ padding: 0.2, minZoom: 0.4, maxZoom: 1.5 })
    }
  }
}, [nodes])
```

### 7.2 Canvas Height

Compute the total canvas height from laid-out node positions + dimensions, and use it for container sizing.

## 8. Dagre Layout Best Practices

### 8.1 Use Real Measured Dimensions

Pass measured dimensions to dagre via the `dimensions` map. Never use hard-coded estimates — they cause layout mis-stacks, incorrect canvas heights, and edge overlap.

```tsx
function layoutNodes(nodes, edges, { centreX, topRowY, dimensions }) {
  // ...
  for (const node of nodes) {
    const dims = dimensions.get(node.id)
    graph.setNode(node.id, { width: dims.width, height: dims.height })
  }
  // ...
}
```

### 8.2 Pinning Positions

After dagre computes layout, override specific node positions:
- **System inputs**: Pin Y to the top row (`y: topRowY`)
- **System outputs**: Pin Y to the bottom row (just below lowest effect)
- **Effect nodes**: Pin X to the column centre (`x: centreX - width/2`)

Dagre's own positioning is used for the initial rank computation (drives the topological ordering), but final positions are pinned to satisfy the layout constraints.

### 8.3 Handle `layoutNodes` Returning `null`

If any node lacks measured dimensions, `layoutNodes` should return `null` to signal the caller to wait:

```tsx
for (const node of nodes) {
  const dims = dimensions.get(node.id)
  if (!dims || dims.width <= 0 || dims.height <= 0) return null
}
```

## 9. Replacing Dagre with a Simple Topological Sort Layout

For pedalboard DAGs (essentially linear signal chains), full graph layout algorithms
like dagre are overkill. A simple topological sort + vertical stacking is sufficient
and eliminates the `@dagrejs/dagre` + `@dagrejs/graphlib` dependencies entirely.

### 9.1 The Simple Layout

```tsx
function layoutNodes(nodes, edges, { centreX, topRowY, dimensions }) {
  // 1. Partition: system inputs, system outputs, effects
  // 2. Topological sort effects using Kahn's algorithm on effect-to-effect edges
  // 3. Stack effects vertically at centreX (x = centreX - width/2)
  // 4. Pin system inputs to topRowY (distributed horizontally)
  // 5. Pin system outputs just below lowest effect (distributed horizontally)
  // 6. Return nodes with positions (spread preserves width/height)
}
```

### 9.2 Topological Sort (Kahn's Algorithm)

```tsx
function topologicalSort(effectNodeIds, edges) {
  const idSet = new Set(effectNodeIds)
  const adj = new Map()  // source -> [targets]
  const inDegree = new Map()

  for (const id of effectNodeIds) {
    adj.set(id, [])
    inDegree.set(id, 0)
  }

  // Build adjacency only for effect-to-effect edges
  for (const edge of edges) {
    if (idSet.has(edge.source) && idSet.has(edge.target)) {
      adj.get(edge.source).push(edge.target)
      inDegree.set(edge.target, inDegree.get(edge.target) + 1)
    }
  }

  // Kahn's algorithm — process nodes with in-degree 0 first
  const order = []
  const queue = effectNodeIds.filter(id => inDegree.get(id) === 0)

  while (queue.length > 0) {
    const current = queue.shift()
    order.push(current)
    for (const next of adj.get(current)) {
      inDegree.set(next, inDegree.get(next) - 1)
      if (inDegree.get(next) === 0) queue.push(next)
    }
  }

  // Cycle fallback: append remaining nodes in insertion order
  for (const id of effectNodeIds) {
    if (!order.includes(id)) order.push(id)
  }
  return order
}
```

### 9.3 When to Use Each Approach

| Constraint | Dagre | Simple Sort |
|---|---|---|
| Branches (parallel effects) | Handles via rank assignment | Topological sort handles via queue order |
| Wide graphs (multiple columns) | ✅ Automatic multi-column | ❌ Single column only |
| Complex hierarchies | ✅ Rank-based grouping | ❌ Linear order |
| Signal chain (linear) | ✅ Overkill | ✅ Sufficient |
| Circular references | N/A (DAGs don't cycle) | Falls back to insertion order |
| Dependencies | `@dagrejs/dagre`, `@dagrejs/graphlib` | None (stdlib only) |

**Recommendation**: For pedalboard signal chains (linear with possible branch points),
the simple topological sort is the better choice — same visual result with zero extra dependencies
+and no dagre-specific bugs.

## Debug Overlay (Recommended)

Add a visible debug panel during development:

```tsx
<div class="fixed bottom-2 right-2 bg-black/80 text-xs font-mono p-2 rounded pointer-events-none z-50">
  <div>nodes: {nodes.length} | edges: {edges.length} | measured: {nodes.filter(n => n.width != null && n.height != null).length}/{nodes.length}</div>
  <div>graphKey: {graphKey}</div>
</div>
```

This immediately reveals whether the measurement cycle is completing.

## 10. Common Pitfalls & Gotchas

| Issue | Cause | Fix |
|---|---|---|
| "Loading pedalboard…" forever | Runtime error crashes the component | Add error boundaries; check console for ReferenceErrors |
| Nodes render but `visibility: hidden` | `onNodesChange` dims not reaching state | Use `useNodesState` + DOM dimension fallback |
| 0 edges in DOM, no handle errors | `handleBounds` not set | Dimension fallback sets widths/heights → triggers RF measurement cycle |
| "Couldn't create edge for handle id: X" | Handle ID mismatch (e.g. `effect_null:` vs `effect_1:`) | Enrich ports from `/ports` endpoint with `effect_instance_id` |
| Infinite re-renders | `rawNodes`/`rawEdges` in deps array | Only use `graphKey` + primitive deps |
| `dimsFallbackRef is not defined` | Dangling reference after code edit | Audit all references when removing code |
| `StoreUpdater` effect doesn't fire | Preact/compat `useSyncExternalStore` shim | Use `useNodesState`/`useEdgesState` instead of prop-passing |

## 11. Astro + Preact/Compat Config

```js
// astro.config.mjs
export default defineConfig({
  preact: {
    compat: true,
    globals: true,
    renderToString: true,
  },
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

This makes all React components (including third-party React Flow dependencies) use Preact under the hood.
