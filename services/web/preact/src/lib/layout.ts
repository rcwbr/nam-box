/**
 * Simple layout engine for the pedalboard DAG.
 *
 * Replaces `@dagrejs/dagre` with a straightforward topological sort +
 * column stacking approach. Dagre is a full graph layout algorithm that
 * is overkill for pedalboards — the signal chain is essentially a linear
 * path (input → effect → effect → output) with occasional branches.
 *
 * React Flow measures each node's DOM size and surfaces it through the
 * `dimensions` map. This layout uses those **real** measured dimensions to
 * compute Y positions, so edge routing and stacking reflect the actual
 * rendered sizes instead of guesses.
 *
 * Layout model:
 * - **System input ports** (capture_*)  → pinned to a top row, distributed horizontally.
 * - **System output ports** (playback_*) → pinned to a bottom row, distributed horizontally.
 * - **Effect nodes** → stacked in a single centred column. The order follows
 *   the topological sort of the connection graph, so the signal path — not
 *   insertion order — determines layout.
 *
 * @see https://reactflow.dev/examples/layout/dagre  (the original dagre example)
 */

import { type Node } from '@xyflow/react'
import { portHandleType } from './portUtils'
import type { Port } from '../api/types'

// Canvas / column geometry (parent is max-w-sm with p-8 ≈ 300px usable width).
export const LAYOUT_WIDTH = 300
export const EFFECT_NODE_WIDTH = 220
export const TOP_ROW_Y = 30

// Vertical spacing constants
const EFFECT_NODE_GAP = 32   // gap between stacked effect cards in the column
const OUTPUT_GAP = 40        // gap between the last effect and the output-port row
const INPUT_ROW_CLEARANCE = 16 // gap between input row and first effect
const MAX_CANVAS_HEIGHT = 720

export interface LayoutDimensions {
  width: number
  height: number
}

export interface LayoutOptions {
  /** Horizontal centre of the effect column. */
  centreX?: number
  /** Y-position for the system input port row (top of canvas). */
  topRowY?: number
  /** Real measured sizes keyed by node id. Missing/unmeasured entries cause
   * `layoutNodes` to return `null` so the caller can wait for measurement. */
  dimensions?: Map<string, LayoutDimensions>
}

/** True when the node is a system input port (signal origin / top row). */
function isSystemInput(node: Node): boolean {
  return node.type === 'systemPort' && portHandleType(node.data?.port as Port) === 'source'
}

/** True when the node is a system output port (signal sink / bottom row). */
function isSystemOutput(node: Node): boolean {
  return node.type === 'systemPort' && portHandleType(node.data?.port as Port) === 'target'
}

/**
 * Topological sort using Kahn's algorithm.
 *
 * Only considers edges between effect nodes (not system ports) to determine
 * the vertical order within the effect column. System port edges only
 * determine which effect is "first" or "last" via their rank in the
 * overall graph.
 *
 * @returns Effect node IDs in topological order.
 */
function topologicalSort(
  effectNodeIds: string[],
  edges: Array<{ source: string; target: string }>,
): string[] {
  const idSet = new Set(effectNodeIds)
  const adj = new Map<string, string[]>()       // source -> [targets]
  const inDegree = new Map<string, number>()    // node -> incoming count

  for (const id of effectNodeIds) {
    adj.set(id, [])
    inDegree.set(id, 0)
  }

  // Build adjacency only for effect-to-effect edges
  for (const edge of edges) {
    if (idSet.has(edge.source) && idSet.has(edge.target)) {
      adj.get(edge.source)!.push(edge.target)
      inDegree.set(edge.target, (inDegree.get(edge.target) ?? 0) + 1)
    }
  }

  // Kahn's algorithm — process nodes with in-degree 0 first.
  // Use the original effect node order as tie-breaker for deterministic results.
  const order: string[] = []
  const queue: string[] = []

  for (const id of effectNodeIds) {
    if ((inDegree.get(id) ?? 0) === 0) queue.push(id)
  }

  while (queue.length > 0) {
    // Pop from front for FIFO (stable ordering)
    const current = queue.shift()!
    order.push(current)
    for (const next of adj.get(current)!) {
      inDegree.set(next, (inDegree.get(next) ?? 0) - 1)
      if (inDegree.get(next) === 0) queue.push(next)
    }
  }

  // If there's a cycle (shouldn't happen in pedalboards), fall back
  // to the remaining nodes in insertion order.
  if (order.length < effectNodeIds.length) {
    for (const id of effectNodeIds) {
      if (!order.includes(id)) order.push(id)
    }
  }

  return order
}

/**
 * Compute a horizontal distribution for a set of nodes across a given width.
 *
 * Centers the group within the available space, with equal gaps between nodes
 * and padding on both sides.
 *
 * @param count      Number of nodes to distribute.
 * @param totalWidth Available horizontal space.
 * @param nodeWidth  Width of each node (assumed equal).
 * @returns Array of X positions (left edge for each node).
 */
function distributeHorizontally(
  count: number,
  totalWidth: number,
  nodeWidth: number,
): number[] {
  if (count === 0) return []
  if (count === 1) {
    return [(totalWidth - nodeWidth) / 2]
  }
  // Equal spacing: node_width + gap fills the available width
  const totalContentWidth = count * nodeWidth
  const availableGap = totalWidth - totalContentWidth
  const gap = availableGap / (count + 1) // gap on both sides + between each
  return Array.from({ length: count }, (_, i) => gap + i * (nodeWidth + gap))
}

/**
 * Run a simple layout on the given nodes and edges, returning the nodes with
 * updated `position` values.
 *
 * - Every node must have measured dimensions in the `dimensions` map.
 * - Effect nodes are stacked vertically in a centred column, ordered by
 *   topological sort of the connection graph.
 * - System output nodes are stacked vertically at the bottom, ordered by
 *   their X position from the top-row distribution (for visual alignment).
 * - System input nodes are distributed horizontally across the top row.
 *
 * @returns Layouted nodes, or `null` if any node still lacks measured dimensions.
 */
export function layoutNodes(
  nodes: Node[],
  edges: Array<{ source: string; target: string }>,
  options: LayoutOptions = {},
): Node[] | null {
  const {
    centreX = LAYOUT_WIDTH / 2,
    topRowY = TOP_ROW_Y,
    dimensions = new Map(),
  } = options

  if (nodes.length === 0) return null

  // Wait until every node has been measured.
  for (const node of nodes) {
    const dims = dimensions.get(node.id)
    if (!dims || dims.width <= 0 || dims.height <= 0) return null
  }

  // ---- Partition nodes ----
  const inputs = nodes.filter(isSystemInput)
  const outputs = nodes.filter(isSystemOutput)
  const effects = nodes.filter((n) => n.type === 'effectNode')

  // ---- Effect column: topological sort, then stack vertically ----
  const effectOrder = topologicalSort(effects.map((n) => n.id), edges)

  const effectY = new Map<string, number>()
  let cursorY = topRowY + INPUT_ROW_CLEARANCE
  let maxEffectBottom = 0

  for (const id of effectOrder) {
    const dims = dimensions.get(id)!
    effectY.set(id, cursorY)
    cursorY += dims.height + EFFECT_NODE_GAP
    maxEffectBottom = Math.max(maxEffectBottom, cursorY)
  }

  // ---- System output row: just below the lowest effect ----
  const outputRowY = maxEffectBottom + OUTPUT_GAP

  // ---- System input positions: distribute horizontally ----
  // Each system port is typically ~100px wide. If there's only one, center it.
  const inputPositions = distributeHorizontally(inputs.length, LAYOUT_WIDTH, 100)

  // ---- System output positions: distribute horizontally (same pattern) ----
  const outputPositions = distributeHorizontally(outputs.length, LAYOUT_WIDTH, 100)

  // ---- Assemble layouted nodes (immutably) ----
  return nodes.map((node) => {
    const dims = dimensions.get(node.id)!

    if (node.type === 'effectNode') {
      return {
        ...node,
        position: { x: centreX - dims.width / 2, y: effectY.get(node.id) ?? 0 },
      }
    }

    if (isSystemInput(node) || isSystemOutput(node)) {
      const inputIdx = inputs.findIndex((n) => n.id === node.id)
      const outputIdx = outputs.findIndex((n) => n.id === node.id)

      if (inputIdx >= 0) {
        const x = inputPositions[inputIdx]
        return { ...node, position: { x, y: topRowY } }
      }
      if (outputIdx >= 0) {
        const x = outputPositions[outputIdx]
        return { ...node, position: { x, y: outputRowY } }
      }
    }

    // Fallback for any other node type
    return { ...node, position: { x: centreX - dims.width / 2, y: topRowY + INPUT_ROW_CLEARANCE } }
  })
}

/**
 * Compute the total canvas height required to display the layouted nodes.
 *
 * @param nodes  The layouted nodes (positions already set).
 * @param dimensions  Measured sizes keyed by node id.
 * @param maxHeight  Viewport-safe cap.
 * @returns The canvas height in pixels, capped at `maxHeight`.
 */
export function computeCanvasHeight(
  nodes: Node[],
  dimensions: Map<string, LayoutDimensions> = new Map(),
  maxHeight = MAX_CANVAS_HEIGHT,
): number {
  let maxY = 0
  for (const node of nodes) {
    const dims = dimensions.get(node.id)
    const h = dims?.height ?? 0
    maxY = Math.max(maxY, node.position.y + h)
  }
  // Minimum: input row + clearance to the first effect.
  const minHeight = TOP_ROW_Y + 80
  return Math.min(Math.max(maxY + 60, minHeight), maxHeight)
}
