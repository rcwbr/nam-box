# Re-implementation Plan: React Flow + Manual Layout (no dagre)

## Objective

Replace `@dagrejs/dagre` with a simple manual layout engine that leverages the same
two-pass measure-then-position pattern, but computes node positions using a
straightforward topological sort + column stacking instead of dagre's graph layout.

This eliminates the dagre dependency and its complexity while satisfying the
project's layout constraints:
- System input ports pinned to a top row
- System output ports pinned to a bottom row
- Effect nodes stacked in a single centered column (ordered by signal-flow topology)

## Rationale: Why Dagre Alone Is Insufficient

Dagre is a **pure graph layout computation engine**. It computes X/Y coordinates
given node dimensions and edges, but provides **zero rendering**. React Flow
provides the rendering canvas, edge path drawing (Bezier curves), handle
registration, dimension measurement, fitView, background grid, and event handling
(all disabled but still wired up). Removing dagre loses only the layout
computation — React Flow still does everything else.

The key insight: the pedalboard DAG is **almost linear** — a signal chain flowing
from system inputs → effects → system outputs. Dagre's full graph layout
algorithm is overkill for a structure that's essentially a linear chain with
possible branch points. A simple topological sort + vertical stacking achieves
the same visual result.

## Scope of Changes

### Files to modify:

1. **`src/lib/dagreLayout.ts`** → Rename to `src/lib/dagreLayout.ts` (keep filename for
   minimal import changes, or create `src/lib/layout.ts`)
   - Replace `layoutNodes()` with `simpleLayout()` using topological sort + column stacking
   - Remove `@dagrejs/dagre` and `@dagrejs/graphlib` imports
   - Keep the `{ width, height }` dimensions map input
   - Keep `computeCanvasHeight()` and layout constants

2. **`src/components/PedalboardDAG.tsx`**
   - Update import from `layoutNodes` to `simpleLayout` (or keep `layoutNodes` name)
   - Remove any dagre-specific logic
   - The two-pass measurement cycle, dimension fallback, and React Flow integration
     remain unchanged

3. **`package.json`**
   - Remove `@dagrejs/dagre` and `@dagrejs/graphlib` from dependencies

### Files NOT modified (unchanged):

- `src/components/nodes/EffectNode.tsx` — Handle/position logic stays the same
- `src/components/nodes/SystemPortNode.tsx` — unchanged
- `src/lib/portUtils.ts` — unchanged
- All API hooks — unchanged
- `src/components/PedalboardView.tsx` — unchanged
- `src/components/App.tsx` — unchanged

## Implementation Details

### New Layout Algorithm

```
simpleLayout(nodes, edges, { centreX, topRowY, dimensions })

1. Partition nodes into: system inputs, system outputs, effect nodes
2. Build adjacency list from edges (source → target)
3. Topological sort effect nodes using Kahn's algorithm
   - Only consider edges between effect nodes for ordering
   - System port edges just determine which row effects appear in
4. Stack effects vertically in the column at centreX
   - Y starts at topRowY + INPUT_ROW_CLEARANCE
   - Gap = EFFECT_NODE_GAP between each effect
5. Pin system inputs to topRowY at their dagre-computed X
6. Pin system outputs just below the lowest effect at their dagre-computed X
7. Non-effect, non-system input/output nodes use dagre's position as fallback
```

### Why Topological Sort Replaces Dagre

Dagre with `rankdir: 'TB'` produces a topological ranking where:
- Nodes earlier in the signal chain get lower Y values (higher rank)
- Connected nodes have consistent rank separation

A simple topological sort achieves the same ordering:
- Process nodes with no incoming edges first
- Follow edges to determine order
- Nodes at the same "level" (multiple inputs, same depth) are ordered by X position

For the pedalboard use case, this is sufficient because:
1. The signal chain is typically linear: input → effect → effect → output
2. Even with branching (parallel effects), the topological order preserves signal-flow direction
3. The single-column constraint means X doesn't matter for ordering — only Y ranking matters

### Dagre Features We Don't Use

| Dagre feature | Used in pedalboard? | Replaced by |
|---|---|---|
| `ranksep` (row spacing) | No (single column) | Fixed `EFFECT_NODE_GAP` |
| `nodesep` (node spacing) | No (single column) | Fixed gap |
| `marginx`/`marginy` | No | Hardcoded margins |
| `rankdir: 'TB'` | Yes (top-to-bottom) | Topological sort order |
| Cross-edge routing | No (single column) | N/A — edges are drawn by React Flow |
| Multi-rank layout | Partially | Topological sort handles rank ordering |

## Step-by-Step Plan

### Step 1: Write the new `simpleLayout` function

File: `src/lib/dagreLayout.ts` (keep filename to minimize import changes)

```ts
// Replace layoutNodes with simpleLayout using topological sort
// Remove dagre/graphlib imports
// Keep the same interface: (nodes, edges, options) => Node[] | null
```

Key algorithm:
1. Check all nodes have dimensions (return null if not — same as current)
2. Partition nodes: system inputs (top row), system outputs (bottom row), effects (column)
3. Build a directed graph from edges (source → target)
4. Run Kahn's algorithm for topological sort on effect nodes
5. Stack effects vertically with measured heights + gap
6. Pin system inputs to topRowY
7. Compute output row Y = max effect bottom + OUTPUT_GAP
8. Return new nodes with positions set (preserve width/height via spread)

### Step 2: Update PedalboardDAG imports

Change `layoutNodes` to `simpleLayout` (or keep the name `layoutNodes` for the new function)

### Step 3: Remove dagre dependencies

Remove from `package.json`:
```json
"@dagrejs/dagre": "^3.1.0",
"@dagrejs/graphlib": "^4.0.5",
```

### Step 4: Verify build + runtime

Same verification as before: select pedalboard #1, check that:
- 8 nodes render and are visible
- 3 edges render as SVG paths
- 12 handles have correct IDs
- Canvas height is computed correctly

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Topological sort doesn't match dagre's ordering for edge cases | Test with the 3-connection pedalboard; verify effect order matches expected signal chain |
| Node ordering within same rank is non-deterministic | Use dagre's X position (or port ID sort) as tiebreaker for deterministic ordering |
| Layout doesn't handle cycles (shouldn't happen in pedalboards) | Add a cycle-detection guard that falls back to insertion order |
| Removing dagre breaks other parts of the app | grep for dagre usage — only `dagreLayout.ts` imports it |

## Files That Already Import Dagre (impact analysis)

```bash
grep -rn "dagre\|graphlib" src/ --include="*.ts" --include="*.tsx"
# Expected: only src/lib/dagreLayout.ts
```
