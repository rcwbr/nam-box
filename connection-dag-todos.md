# TODO: PedalboardView → React Flow DAG

Status: **Implementation Phase 5.** Build succeeds; needs runtime verification.
**Phase 5b (dynamic dagre layout) is designed and documented below; implementation
pending confirmation of the single assumption in "Assumption to confirm".**

References:
- [Plan](https://claudeplan://twinkling-noodling-sifakis.md) — full design & investigation notes
- [React Flow docs](https://reactflow.dev) — `@xyflow/react` package
- `mod-api-openapi.json` — Connection / CreateConnectionRequest schemas
- `services/mod-api/src/mod_api/api/routes/connections.py` — backend connection endpoints

---

## Constraints (from user)
- [x] ALL nodes are **non-draggable** — effects render in a static vertical column
- [x] System input/output ports pinned at top and bottom of the canvas
- [x] Click-to-connect only (select output port → click input port), no drag-to-connect
- [x] All ports (system AND effect) are individually addressable DAG vertices
- [x] Effect ports must be rendered inside the effect node component (as Handles)
- [x] Parameters (sliders, dropdowns) live inside the effect node

## Phase 1 — Setup & Foundation  [DONE]
- [x] Install `@xyflow/react` dependency via Docker (node:22 image)
- [x] Add Vite JSX-runtime aliases in `astro.config.mjs`
      (`react/jsx-runtime` → `preact/jsx-runtime`)
- [x] Add missing `Connection` interface to `src/api/types.ts`
- [x] Create `src/lib/portUtils.ts` — `portId()`, `classifyPorts()`,
      `portHandleType()` (owner-aware), `nodeIdForPortId()`
- [x] Create `src/api/hooks/useConnections.ts` — `useCreateConnection`, `useDeleteConnection`
- [x] Export new hooks in `src/api/hooks/index.ts`

## Phase 2 — Node Components  [DONE]
- [x] `src/components/nodes/SystemPortNode.tsx`
- [x] `src/components/nodes/EffectNode.tsx` (with `PortHandle` sub-component)

## Phase 3 — PedalboardDAG  [DONE]
- [x] `src/components/PedalboardDAG.tsx`
      - Builds nodes from `pedalboard.effects` + `usePorts`
      - Builds edges from `pedalboard.connections`
      - Click-to-connect state machine via `selectedPortId` ref
      - `connectionMode="loose"`, `Background`, LCD-styled amber edges
      - All nodes `draggable: false`, `connectable: false`

## Phase 4 — Integration  [DONE]
- [x] Refactor `src/components/PedalboardView.tsx` — replaced card list + port rows
      with `<PedalboardDAG>`
- [x] Removed inline `classifyPorts` (moved to `portUtils.ts`)
- [x] Kept ADD EFFECT button + Dialog

## Phase 5 — Polish & Verification
- [x] Apply LCD theme (amber handles, edges, node borders)
- [x] **Build succeeded** via `docker run node:22 npm run build`
- [ ] Visual check (dev server):
  - System input ports pinned in a row at top, system output ports at bottom
  - Effects render as cards with parameter controls inside
  - Each effect port appears as an individual Handle (top = inputs, bottom = outputs)
  - Existing connections render as amber edges between correct handles
- [ ] Click-to-connect: output handle → input handle → edge + API POST
- [ ] Connection persistence: reload → edges re-render
- [ ] No-regression: ADD EFFECT dialog, parameter sliders, dropdowns, effect removal

---

## Phase 5b — Dynamic Layout Rework (dagre + measured dimensions)

> **Status:** In design / pending confirmation. Replaces the hardcoded-dimension
> estimates in `src/lib/dagreLayout.ts` with dimensions measured from the actual
> React Flow nodes.

### Problem

`dagreLayout.ts` feeds dagre **estimated** dimensions rather than the real rendered
sizes:

| Constant | Value | What it estimates |
|---|---|---|
| `EFFECT_NODE_BASE_HEIGHT` | `120` | header + handles + divider + padding |
| `PARAM_HEIGHT_NUMBER` | `32` | per slider row (label + range + value) |
| `PARAM_HEIGHT_FILENAME` | `40` | per `Select` dropdown row |
| `SYSTEM_PORT_WIDTH` / `SYSTEM_PORT_HEIGHT` | `40` / `40` | the whole system-port node |

These guesses drift from reality:
- Slider row height depends on the rendered `input[type=range]` + `text-2xs` label
  (actual ≈ 20 px, not 32 px).
- The `Select` (headless UI custom button) is taller than 40 px.
- `SystemPortNode` is a `w-6 h-6` circle + a `text-2xs` label — its **width** is
  driven by the port name length (`capture_1` vs `playback_10_1`), which the fixed
  `40` ignores entirely.
- The canvas width is hardcoded to `300` and `portSpacing` is derived from it, so
  system-port rows don't track real label widths either.

Consequence: dagre mis-stacks effect nodes vertically, mis-spreads system-port
rows, computes an incorrect `canvasHeight` (edges can overlap node bodies, and the
container height is wrong), and `fitView` may clip or over-zoom.

### Mechanism (verified against `@xyflow/react@12.11.2`)

1. React Flow measures each node's DOM via an internal `ResizeObserver` and stores
   the result on the internal node as `measured: { width, height }`.
2. It also emits an `onNodesChange` event of type **`'dimensions'`**:
   ```ts
   type NodeDimensionChange = {
     id: string
     type: 'dimensions'
     dimensions?: { width: number; height: number }
     resizing?: boolean
   }
   ```
   This fires in **both** controlled mode and `useNodesState` mode — confirmed in
   the package type defs (`node_modules/@xyflow/system/dist/esm/types/changes.d.ts`)
   and the React Flow docs.
3. `applyNodeChanges(changes, setNodes)` writes the measured `width`/`height` right
   onto **our** node objects in state. Once that lands, `node.width` / `node.height`
   on our `nodes` array hold the truth — no separate ref/map is required.
4. **Verified in the installed bundle** (`@xyflow/system/dist/esm/index.js`): React
   Flow internally computes
   `dimensionChanged = node.measured.width !== dims.width || node.measured.height !== dims.height`
   and, when a node's rendered size changes, pushes
   `changes.push({ id, type: 'dimensions', setAttributes: true, dimensions: { width, height } })`
   through its middleware — i.e. these are exactly the `'dimensions'` events emitted
   to `onNodesChange`, and they carry the real `dimensions`.
5. `ReactFlowInstance.getInternalNode(id)` returns the internal node whose
   `measured: { width?, height? }` is the source of truth — available as a
   **bulletproof fallback** if the `applyNodeChanges`-on-`nodes` state path doesn't
   surface dims (it should, since `useNodesState` uses `applyNodeChanges`
   internally for exactly this).

> `@xyflow/react@12.11.2`, `@dagrejs/dagre@3.1.0` are installed
> (`services/web/preact/package.json`). `useNodesState`, `applyNodeChanges`, and
> `getNodeDimensions` are all exported.

### Rework design

#### A. `src/lib/dagreLayout.ts`

- **Delete** `computeEffectNodeHeight(...)` and all hard-coded height math
  (`EFFECT_NODE_BASE_HEIGHT`, `PARAM_HEIGHT_NUMBER`, `PARAM_HEIGHT_FILENAME`) and
  the `SYSTEM_PORT_WIDTH` / `SYSTEM_PORT_HEIGHT` constants. Dimensions come
  **only** from React Flow measurement. (Per your call: accept the ~1-frame flash
  where un-measured nodes start at `{x:0,y:0}` before dagre repositions them.)
- `layoutNodes(nodes, edges, options)` now takes a `dimensions` map of **measured**
  sizes:
  ```ts
  interface LayoutDimensions { width: number; height: number }
  interface LayoutOptions {
    centreX?: number
    topRowY?: number
    layoutWidth?: number
    dimensions?: Map<string, LayoutDimensions>   // real measured sizes
  }
  export function layoutNodes(nodes, edges, options?): Node[] | null
  ```
  - Returns `null` when **any** node in the set lacks measured dimensions (so the
    caller keeps rendering placeholder positions and lets React Flow measure first).
    Once all nodes are measured it returns positioned + sized nodes.
  - **Nodes in the dagre graph:** *all* node types — system-port nodes **and** effect
    nodes (system ports are no longer placed in manual rows).
  - **Edges in the dagre graph:** *only real connection edges* from
    `pedalboard.connections` (system→effect, effect→effect, effect→system),
    restricted to pairs where both endpoints are present nodes.
  - **Removed:** the synthetic `effect-0 → effect-1 → …` chain edges (per your call).
    **Not added:** within-effect input→output edges — effect ports are rendered as
    Handles inside one node (constraint #18), so there is no per-port dagre node to
    chain. (`"if using"` → we are not using a split-node/per-port model, so N/A.)
  - dagre `rankdir: 'TB'`. Then a **post-pass forces the pinned-rows constraint**
    (constraint #15): pin every system input port to `topRowY`; pin every system
    output port to just below the last effect (`maxEffectBottom + OUTPUT_GAP`).
  - Effect nodes are pinned to the **centre column** (constraint #14): `x = centreX - w/2`,
    with dagre's `y` (top-aligned: `dagreY - h/2`) kept. If two effects land on the
    same dagre rank (i.e. a branched pedalboard), stagger their `y` by
    `height + gap` so the "static vertical column" constraint still holds and
    effects never overlap.
  - System-port `x` is taken from dagre (natural horizontal spread from real edges +
    measured label widths + `nodesep`); only `y` is pinned.
- `computeCanvasHeight(nodes, dimensions)` derives the container height from the
  layouted positions + measured dims (top row → effects → bottom row), with a
  `TOP_ROW_Y` minimum.

#### B. `src/components/PedalboardDAG.tsx`

Move from the static "compute-once-in-Memo → no-op onNodesChange" model to a
**measure → re-layout** cycle:

```tsx
// 1. Stateful nodes so we can re-position them after measurement.
const [nodes, setNodes] = useState<Node[]>([])
const [canvasHeight, setCanvasHeight] = useState<number>(300)

// 2. Capture React Flow's measurement events and merge measured dims INTO our
//    nodes state (applyNodeChanges writes node.width/height for us).
const onNodesChange = useCallback((changes: NodeChange[]) => {
  applyNodeChanges(changes, setNodes)
}, [])

// 3. Build raw nodes from API data. NOTE: no position/dimension estimation —
//    every node starts at {x:0, y:0} and is sized by React Flow's measurement.
//    A `NodeChange` of `type:'dimensions'` carries the real size into `nodes`.
//    Rebuilds whenever pedalboard/ports/catalog change.
const { rawNodes, edges, nodeIds } = useMemo(() => buildRawNodes(...), [deps])

// 4. Reset node state when the graph identity changes (add/remove effect →
//    fresh node set → must re-measure; stale dims on removed nodes discarded).
const graphKey = useMemo(() => graphSignature(pedalboard, allPorts), [deps])
const lastDimsKeyRef = useRef<string>('')
useEffect(() => {
  setNodes(rawNodes)            // reset: clear dims + positions for the new graph
  lastDimsKeyRef.current = ''   // invalidate the loop guard
  rfInstanceRef.current?.fitView({ padding: 0.2, minZoom: 0.4, maxZoom: 1.5 })
}, [graphKey])

// 5. Authoritative layout pass: runs once every node in the current set has
//    measured dimensions on its node object (applyNodeChanges wrote them via
//    onNodesChange dimension events).
useLayoutEffect(() => {
  if (!pedalboard || !allPorts || nodes.length === 0) return
  const current = nodes.filter((n) => nodeIds.includes(n.id))
  const ready =
    current.length === nodeIds.length &&
    current.every((n) => n.width != null && n.height != null)
  if (!ready) return          // React Flow is still measuring → wait
  const dimsKey = current
    .map((n) => `${n.id}:${n.width}x${n.height}`)
    .join('|')
  if (dimsKey === lastDimsKeyRef.current) return   // dims unchanged → no relayout
  lastDimsKeyRef.current = dimsKey
  const dimensions = new Map(current.map((n) => [n.id, { width: n.width!, height: n.height! }]))
  const layouted = layoutNodes(current, edges, {
    centreX: LAYOUT_WIDTH / 2,        // column centre; layoutNodes does x = centreX - w/2
    topRowY: TOP_ROW_Y,
    dimensions,
  })
  if (!layouted) return       // safety: dimensions map incomplete → skip
  setNodes(layouted)           // positions + (existing) dims
  setCanvasHeight(computeCanvasHeight(layouted, dimensions))
  rfInstanceRef.current?.fitView({ padding: 0.2, minZoom: 0.4, maxZoom: 1.5 })
}, [nodes, graphKey])
```

**Why this is loop-safe:** `setNodes(layouted)` in step 5 only changes `position` —
the measured `width`/`height` are already present and identical — so the
`dimsKey` guard (step 5's `lastDimsKeyRef`) short-circuits any re-entry. React
Flow's `ResizeObserver` will not re-emit `'dimensions'` changes because the DOM
size didn't change. The only thing that resets the cycle is `graphKey` (step 4)
when the effect set changes.

**Key behaviours preserved:**
- All nodes remain `draggable: false`, `connectable: false`.
- Click-to-connect (`handlePortClick`, `selectedPortId`) is unchanged; it still
  mutates via the connection hooks.
- `onPaneClick` clears the pending selection (unchanged).
- `onEdgeDelete` → `deleteConnection` (unchanged).
- `fitView` after each authoritative layout so zoom tracks the new bounds.

### Decisions (resolved per user)

1. **`computeEffectNodeHeight` deleted entirely.** Accept the ~1-frame flash where
   un-measured nodes start at `{x:0,y:0}`; dagre repositions them once React Flow
   has measured. No first-pass scaffold.
2. **System ports are real dagre nodes** (not manual rows). They are wired into the
   dagre graph via *real* connection edges so dagre ranks inputs toward the top and
   outputs toward the bottom. The **pinned-rows constraint (#15)** is enforced as a
   post-pass: pin system inputs to `topRowY`, system outputs to `maxEffectBottom +
   OUTPUT_GAP`. This is the "different component types / forcing" the user allowed.
   Dagre still does the horizontal spread (measured label widths + `nodesep`); only
   `y` is pinned.
3. **Artificial effect-chain edges (`effect-0 → effect-1`) removed.** Ordering is
   driven by real connections only. **No within-effect input→output edges** are
   added — effect ports are Handles inside a single node (constraint #18), so there
   is no per-port dagre node to chain ("if using" → not using a split-node model).
4. **State reset + `fitView`** (no full `<ReactFlow>` remount): `graphKey`-driven
   `setNodes(rawNodes)` clears stale dims when the effect set changes; `fitView`
   runs after the reset and after each authoritative layout.

### Verification plan
- [ ] With N effects of varying param counts, effect cards no longer overlap and
  edges route cleanly between the correct handles (no dim-estimate drift).
- [ ] System-port rows widen/shrink to fit the real label width (no 40-px circle
  cutoff, no label overlap).
- [ ] `canvasHeight` matches the rendered stack (no vertical scrollbar/truncation).
- [ ] Add/remove effect → `graphKey` resets → re-measure → re-lay-out, no stale dims.
- [ ] Linear pedalboard (`capture → ef1 → ef2 → playback`) still renders as a
  vertical effect column (real edges supply the chain).
- [ ] Build still passes; no-regression on click-to-connect + persistence.

### Assumption (confirmed by user)
Branches *can* occur in pedalboards, but effects **must still render in a single
vertical column** (hard constraint #14). Therefore the reworked `layoutNodes`
**must** include the same-rank stagger: effects that dagre places on the same rank
(branch-parallel effects) are offset vertically by `height + gap` so the column
never overlaps. For linear chains this never triggers; it only engages on branches.
