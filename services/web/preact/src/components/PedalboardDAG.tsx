import '@xyflow/react/dist/style.css'

import {
  ReactFlow,
  Background,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
  type ReactFlowInstance,
} from '@xyflow/react'
import { useState, useCallback, useMemo, useRef, useEffect, useLayoutEffect } from 'preact/hooks'
import type { EffectInstance, Port } from '../api/types'
import { usePedalboard } from '../api/hooks/usePedalboard'
import { usePorts } from '../api/hooks/usePorts'
import { useRemoveEffect, useEffects } from '../api/hooks/useEffects'
import { useModelFiles } from '../api/hooks/useModelFiles'
import { useCreateConnection, useDeleteConnection } from '../api/hooks/useConnections'
import {
  classifyPorts,
  portId,
  nodeIdForPortId,
  type HandleType,
} from '../lib/portUtils'
import { layoutNodes, computeCanvasHeight, LAYOUT_WIDTH, TOP_ROW_Y } from '../lib/layout'
import SystemPortNode from './nodes/SystemPortNode'
import EffectNode from './nodes/EffectNode'

// Layout constants — tuned to fit within the pedalboard view space
// (parent is max-w-sm / p-8 ≈ 300px usable width).
const AMBER = '#facc15'

interface PedalboardDAGProps {
  pedalboardId: number
}

/**
 * Pedalboard DAG rendered as a React Flow canvas.
 *
 * - System input ports (capture_*) and system output ports (playback_*) are
 *   individual React Flow nodes participating in the dagre graph, so real
 *   connections from/to them drive the effect-column ordering. Their Y is pinned
 *   to the top/bottom rows by `layoutNodes`.
 * - Effect nodes are stacked in a single centred column (constraint: non-draggable,
 *   static column), ordered by dagre's topological rank from the real edges.
 * - Click-to-connect: click a source (output) handle, then a target (input) handle
 *   to create a connection via the mod-api.
 * - All nodes are non-draggable and non-connectable via native React Flow drag
 *   (connections are click-based only).
 *
 * Layout is a two-pass measure-then-position cycle:
 *  1. Raw nodes render at {0,0}; React Flow measures their real DOM dimensions and
 *     reports them via `onNodesChange` `type:'dimensions'` (merged into `nodes`
 *     state by `applyNodeChanges`).
 *  2. Once every node has measured width/height, `layoutNodes` runs dagre with the
 *     real sizes and the resulting positions are committed.
 */
export default function PedalboardDAG({ pedalboardId }: PedalboardDAGProps) {
  const { data: pedalboard } = usePedalboard(pedalboardId)
  const { data: allPorts } = usePorts(pedalboardId)
  const { data: effectCatalog } = useEffects()
  const { data: modelFiles } = useModelFiles()

  const createConnection = useCreateConnection(pedalboardId)
  const deleteConnection = useDeleteConnection(pedalboardId)
  const removeEffect = useRemoveEffect(pedalboardId)

  // --- React Flow instance ref (for programmatic fitView) ---
  const rfInstanceRef = useRef<ReactFlowInstance | null>(null)

  // --- Click-to-connect state -----------------------------------------------

  const [selectedPortId, setSelectedPortId] = useState<string | null>(null)
  // Ref so the callback closure always reads the latest selected port
  const selectedRef = useRef<string | null>(null)
  selectedRef.current = selectedPortId

  const handlePortClick = useCallback(
    (pid: string, handleType: HandleType) => {
      const current = selectedRef.current

      if (handleType === 'source') {
        // Select (or toggle off) a source port
        setSelectedPortId(pid === current ? null : pid)
      } else if (handleType === 'target' && current) {
        // User clicked a target while a source was selected → create connection
        createConnection.mutate({
          output_port_id: current,
          input_port_id: pid,
        })
        setSelectedPortId(null)
      }
    },
    [createConnection],
  )

  const handleRemoveEffect = useCallback(
    (effectId: number) => {
      removeEffect.mutate(effectId)
    },
    [removeEffect],
  )

  // --- Reactive node/edge state -------------------------------------------------
  // useNodesState / useEdgesState from @xyflow/react properly sync with React Flow's
  // internal Zustand store. This is critical in Preact/compat: the StoreUpdater's
  // useEffect-based prop→store sync (reference equality) doesn't reliably fire for
  // edges, causing edges to never appear in the store's edge array. These hooks
  // write directly to the store, bypassing the broken sync path.
  const [nodes, setNodes, onNodesChangeHandler] = useNodesState<Node>([])
  const [canvasHeight, setCanvasHeight] = useState<number>(300)
  const [rfEdges, setRfEdges, onRfEdgesChange] = useEdgesState<Edge>([])
  // Track the Y positions of the system port rows for rendering visual row blocks
  const inputRowYRef = useRef<number>(TOP_ROW_Y)
  const outputRowYRef = useRef<number | null>(null)
  // Bounding boxes for the system port rows (computed during layout)
  const inputRowBoxRef = useRef<{ x: number; y: number; width: number; height: number } | null>(null)
  const outputRowBoxRef = useRef<{ x: number; y: number; width: number; height: number } | null>(null)

  // Build raw nodes + edges from API data. Positions/dimensions are NOT estimated:
  // nodes start at {0,0} and are sized by React Flow's measurement pass.
  const { rawNodes, rawEdges, nodeIds } = useMemo(() => {
    if (!pedalboard || !allPorts) return { rawNodes: [] as Node[], rawEdges: [] as Edge[], nodeIds: [] as string[] }

    // System ports (system:capture_* = inputs, system:playback_* = outputs)
    const systemPorts = allPorts.filter((p) => p.owner_type === 'system')
    const { inputs: sysInputs, outputs: sysOutputs } = classifyPorts(systemPorts)

    const portNode = (port: Port): Node => {
      const pid = portId(port)
      return {
        id: pid,
        type: 'systemPort',
        position: { x: 0, y: 0 },
        data: {
          port,
          isSelected: selectedPortId === pid,
          onClick: handlePortClick,
        },
        draggable: false,
        connectable: false,
      }
    }

    // Effect nodes
    const effectEntries = Object.entries(pedalboard.effects) as [string, EffectInstance][]
    const effectNodes: Node[] = effectEntries.map(([id, effect]) => {
      const effectId = Number(id)
      const catalogEntry = effectCatalog?.find((e) => e.uri === effect.uri)
      // Enrich effect ports with the correct effect_instance_id from allPorts.
      // The pedalboard API returns effect.ports with effect_instance_id: null,
      // but the /ports endpoint returns them correctly. Without this, portId()
      // returns "effect_null:input" instead of "effect_1:input", causing
      // edge handle lookups to fail.
      const effectPorts = allPorts.filter(
        (p) => p.owner_type === 'effect' && p.effect_instance_id === effectId,
      )
      const enrichedEffect = { ...effect, ports: effectPorts.length > 0 ? effectPorts : effect.ports }
      return {
        id: `effect-${effectId}`,
        type: 'effectNode',
        position: { x: 0, y: 0 },
        data: {
          pedalboardId,
          effectId,
          effect: enrichedEffect,
          catalogEntry,
          modelFiles,
          selectedPortId,
          onPortClick: handlePortClick,
          onRemoveEffect: handleRemoveEffect,
        },
        draggable: false,
        connectable: false,
      }
    })

    const inputNodes = sysInputs.map(portNode)
    const outputNodes = sysOutputs.map(portNode)

    // Edges from real connections
    const edgeList: Edge[] = Object.values(pedalboard.connections).map((conn) => ({
      id: `e-${conn.id}`,
      source: nodeIdForPortId(conn.output_port_id),
      target: nodeIdForPortId(conn.input_port_id),
      sourceHandle: conn.output_port_id,
      targetHandle: conn.input_port_id,
      animated: true,
      style: { stroke: AMBER, strokeWidth: 2 },
    }))

    const allNodes = [...inputNodes, ...effectNodes, ...outputNodes]
    const ids = allNodes.map((n) => n.id)

    return { rawNodes: allNodes, rawEdges: edgeList, nodeIds: ids }
  }, [pedalboard, allPorts, effectCatalog, modelFiles, selectedPortId, pedalboardId, handlePortClick, handleRemoveEffect])

  // graphKey: forces a full node reset + re-measure whenever the pedalboard's
  // effect set or connections change (add/remove effect, new connection).
  const graphKey = useMemo(() => {
    if (!pedalboard || !allPorts) return ''
    return `${pedalboard.id}:${Object.keys(pedalboard.effects).sort().join(',')}:${Object.keys(pedalboard.connections).sort().join(',')}`
  }, [pedalboard, allPorts])

  const lastDimsKeyRef = useRef<string>('')

  // Push the freshly-built raw nodes AND edges into state when the graph identity
  // changes (add/remove effect, new connection, etc.).
  // NOTE: only graphKey in the deps — rawNodes/rawEdges are new arrays every render
  // (useMemo re-runs due to handlePortClick dep), but we only want to reset state when
  // the actual pedalboard structure changes. Resetting with rawNodes would wipe out
  // measured dimensions and trigger a layout re-cycle.
  useEffect(() => {
    if (!pedalboard || !allPorts || !graphKey) return
    setNodes(rawNodes)
    setRfEdges(rawEdges)
    lastDimsKeyRef.current = ''
  }, [graphKey])

  // Keep selection highlights in node data as selectedPortId changes.
  useEffect(() => {
    setNodes((prev) =>
      prev.map((n) => {
        if (n.type === 'systemPort') {
          const port = n.data?.port as Port | undefined
          const pid = port ? portId(port) : null
          return { ...n, data: { ...n.data, isSelected: pid === selectedPortId } }
        }
        if (n.type === 'effectNode') {
          return { ...n, data: { ...n.data, selectedPortId } }
        }
        return n
      }),
    )
  }, [selectedPortId])

  // Authoritative layout pass: once every node has measured dimensions, run dagre
  // with the real sizes. A dims checksum guards against re-entry (position-only
  // updates don't change the checksum, so the ResizeObserver won't re-emit dims).
  useLayoutEffect(() => {
    if (!pedalboard || !allPorts) return
    const current = nodes.filter((n) => nodeIds.includes(n.id))
    const ready =
      current.length === nodeIds.length &&
      current.length > 0 &&
      current.every((n) => n.width != null && n.height != null)
    if (!ready) return // React Flow is still measuring → wait

    const dimsKey = current
      .map((n) => `${n.id}:${n.width}x${n.height}`)
      .join('|')
    if (dimsKey === lastDimsKeyRef.current) return
    lastDimsKeyRef.current = dimsKey

    const dimensions = new Map(
      current.map((n) => [n.id, { width: n.width!, height: n.height! }]),
    )
    const layouted = layoutNodes(current, rfEdges, {
      centreX: LAYOUT_WIDTH / 2,
      topRowY: TOP_ROW_Y,
      dimensions,
    })
    if (!layouted) return

    setNodes(layouted)
    setCanvasHeight(computeCanvasHeight(layouted, dimensions))

    // Capture row Y positions for visual row blocks.
    // Input row is at TOP_ROW_Y (constant). Output row is wherever system
    // output nodes landed.
    inputRowYRef.current = TOP_ROW_Y
    const outputNode = layouted.find(
      (n) => n.type === 'systemPort' && n.position.y > 100,
    )
    outputRowYRef.current = outputNode ? outputNode.position.y : null

    // Compute bounding boxes for system port rows (for visual row blocks)
    const inputNodes = layouted.filter((n) => n.type === 'systemPort' && n.position.y < 100)
    const outputNodes = layouted.filter((n) => n.type === 'systemPort' && n.position.y > 100)

    if (inputNodes.length > 0 && inputNodes[0].width && inputNodes[0].height) {
      const minX = Math.min(...inputNodes.map((n) => n.position.x))
      const maxX = Math.max(...inputNodes.map((n) => n.position.x + (n.width ?? 0)))
      const minY = Math.min(...inputNodes.map((n) => n.position.y))
      const maxY = Math.max(...inputNodes.map((n) => n.position.y + (n.height ?? 0)))
      inputRowBoxRef.current = { x: minX, y: minY, width: maxX - minX, height: maxY - minY }
    }

    if (outputNodes.length > 0 && outputNodes[0].width && outputNodes[0].height) {
      const minX = Math.min(...outputNodes.map((n) => n.position.x))
      const maxX = Math.max(...outputNodes.map((n) => n.position.x + (n.width ?? 0)))
      const minY = Math.min(...outputNodes.map((n) => n.position.y))
      const maxY = Math.max(...outputNodes.map((n) => n.position.y + (n.height ?? 0)))
      outputRowBoxRef.current = { x: minX, y: minY, width: maxX - minX, height: maxY - minY }
    }
  }, [nodes, graphKey, nodeIds.length, pedalboard, allPorts])
  // Re-fit the viewport whenever the (now layouted) nodes change, so zoom tracks
  // the new bounds. Gated on a non-zero position to skip the raw {0,0} flash.
  useEffect(() => {
    if (rfInstanceRef.current && nodes.length > 0) {
      const laidOut = nodes.some((n) => n.position.x !== 0 || n.position.y !== 0)
      if (laidOut) {
        rfInstanceRef.current.fitView({ padding: 0.2, minZoom: 0.4, maxZoom: 1.5 })
      }
    }
  }, [nodes])

  // Fallback: React Flow's internal ResizeObserver measures nodes and sets
  // visibility: visible + handleBounds in the store. But in Preact/compat, the
  // dimension change events (type:'dimensions' via onNodesChange) do NOT reliably
  // reach our component's nodes state. This means n.width/n.height stay null in
  // our state, so the useLayoutEffect's readiness guard never passes.
  // Solution: poll the internal store via useReactFlow() to read measured dims
  // directly, then fall back to DOM getBoundingClientRect as a last resort.
  useEffect(() => {
    if (!pedalboard || !allPorts || !graphKey) return

    const pollDims = () => {
      // Guard: rfInstanceRef may not be set yet (onInit fires async).
      // If not, just return and let the next interval tick try again.
      if (!rfInstanceRef.current) return

      // If onNodesChange was working and all nodes have dims, stop polling
      const allHaveDims = nodes.every((n) => n.width != null && n.height != null)
      if (allHaveDims) return

      // Try reading dims from React Flow's internal node API
      let updated = false
      setNodes((prev) =>
        prev.map((n) => {
          if (n.width != null && n.height != null) return n
          const internal = rfInstanceRef.current?.getInternalNode(n.id)
          if (!internal) return n
          const width = internal.measured?.width
          const height = internal.measured?.height
          if (width && height && width > 0 && height > 0) {
            updated = true
            return { ...n, width, height }
          }
          // Also check node.width/height (setAttributes may have written them)
          if (internal.width && internal.height) {
            updated = true
            return { ...n, width: internal.width, height: internal.height }
          }
          return n
        }),
      )

      if (!updated) {
        // Ultimate fallback: read from the DOM directly
        setNodes((prev) =>
          prev.map((n) => {
            if (n.width != null && n.height != null) return n
            const el = document.querySelector<HTMLElement>('[data-id="' + n.id + '"]')
            if (!el) return n
            const rect = el.getBoundingClientRect()
            if (rect.width > 0 && rect.height > 0 && rect.width < 5000 && rect.height < 5000) {
              updated = true
              return { ...n, width: rect.width, height: rect.height }
            }
            return n
          }),
        )
      }
    }

    const interval = window.setInterval(pollDims, 50)
    pollDims()
    return () => clearInterval(interval)
  }, [graphKey, pedalboard, allPorts, nodes.length])

  // --- React Flow callbacks ---
  const onPaneClick = useCallback(() => {
    setSelectedPortId(null)
  }, [])

  // Handle edge deletion → delete the backend connection
  const onEdgeDelete = useCallback(
    (oldEdge: Edge) => {
      const connId = Number(oldEdge.id.replace('e-', ''))
      deleteConnection.mutate(connId)
    },
    [deleteConnection],
  )

  const nodeTypes: NodeTypes = useMemo(
    () => ({
      systemPort: SystemPortNode,
      effectNode: EffectNode,
    }),
    [],
  )

  // --- Loading state ---

  if (!pedalboard || !allPorts) {
    return (
      <div class="text-lcd-400 text-xs text-center py-8">
        Loading pedalboard…
      </div>
    )
  }

  // --- Debug overlay ---
  const measuredCount = nodes.filter((n) => n.width != null && n.height != null).length
  const dimsFallbackActive = rfInstanceRef.current ? 'active' : 'idle'

  // Read the current viewport transform to position the row block overlays
  // at the correct (zoomed/panned) coordinates matching the node positions.
  const viewport = rfInstanceRef.current ? rfInstanceRef.current.getViewport() : { x: 0, y: 0, zoom: 1 }

  // Compute the visual bounding box for the input row (system capture ports).
  // Falls back to a sensible default if not yet laid out.
  const inputRowX = inputRowBoxRef.current?.x ?? (LAYOUT_WIDTH - 160) / 2
  const inputRowWidth = inputRowBoxRef.current?.width ?? 160
  const inputRowHeight = inputRowBoxRef.current?.height ?? 50
  const inputRowY = TOP_ROW_Y

  // System output ports (playback) sit at the bottom row.
  const outputRowX = outputRowBoxRef.current?.x ?? (LAYOUT_WIDTH - 160) / 2
  const outputRowWidth = outputRowBoxRef.current?.width ?? 160
  const outputRowHeight = outputRowBoxRef.current?.height ?? 50
  const outputRowY = outputRowYRef.current ?? (canvasHeight - 40)

  // Apply viewport transform to flow coordinates → visual coordinates.
  // NOTE: The viewport transform is matrix(zoom, 0, 0, zoom, panX, panY),
  // which means pan is NOT scaled. The formula is:
  //   visualX = flowX * zoom + panX  (within the viewport parent element)
  // The row blocks are children of the container div (position: relative),
  // which is the viewport's parent (or an ancestor). The viewport element itself
  // has left:0/top:0 so visual position = viewport_parent_position + flow* zoom + pan.
  // Since the container is the viewport's parent at (containerX, containerY):
  //   CSS left = flowX * zoom + panX - container_offset_in_parent
  // But since container is position:relative and viewport is position:absolute with left:0,
  // the container IS the viewport's offset parent. So CSS left relative to container =
  // flowX * zoom + panX.
  const tf = (x: number, y: number) => ({
    x: x * viewport.zoom + viewport.x,
    y: y * viewport.zoom + viewport.y,
  })
  const inputPos = tf(inputRowX - 8, inputRowY - 8)
  const inputW = inputRowWidth * viewport.zoom + 16
  const inputH = inputRowHeight * viewport.zoom + 16
  const outputPos = tf(outputRowX - 8, outputRowY - 8)
  const outputW = outputRowWidth * viewport.zoom + 16
  const outputH = outputRowHeight * viewport.zoom + 16

  return (
    <div
      class="border-2 border-lcd-400 rounded-sm bg-black overflow-hidden mx-auto relative"
      style={{ width: `${LAYOUT_WIDTH}px`, height: `${canvasHeight}px` }}
    >
      {/* --- Visual row blocks around system ports --- */}
      {inputRowYRef.current !== null && (
        <div
          class="absolute border border-lcd-500/50 rounded-md bg-lcd-900/15 pointer-events-none"
          style={{
            left: `${inputPos.x}px`,
            top: `${inputPos.y}px`,
            width: `${inputW}px`,
            height: `${inputH}px`,
          }}
        />
      )}
      {outputRowYRef.current !== null && (
        <div
          class="absolute border border-lcd-500/50 rounded-md bg-lcd-900/15 pointer-events-none"
          style={{
            left: `${outputPos.x}px`,
            top: `${outputPos.y}px`,
            width: `${outputW}px`,
            height: `${outputH}px`,
          }}
        />
      )}
      <ReactFlow
        nodes={nodes}
        edges={rfEdges}
        onNodesChange={onNodesChangeHandler}
        onEdgesChange={onRfEdgesChange}
        nodeTypes={nodeTypes}
        onInit={(instance: ReactFlowInstance) => { rfInstanceRef.current = instance }}
        onPaneClick={onPaneClick}
        onEdgeDelete={onEdgeDelete}
        connectionMode="loose"
        fitView
        fitViewOptions={{ padding: 0.2, minZoom: 0.4, maxZoom: 1.5 }}
        /* --- Fully static canvas: disable all user interaction --- */
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        selectionOnDrag={false}
        selectionKeyCode={null}
        multiSelectionKeyCode={null}
        deleteKeyCode={null}
        panActivationKeyCode={null}
        zoomActivationKeyCode={null}
        disableKeyboardA11y={true}
        autoPanOnSelection={false}
        panOnDrag={false}
        panOnScroll={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
        preventScrolling={true}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          color={AMBER}
          gap={20}
          nodeBackgroundColor="#111827"
        />
      </ReactFlow>
      {/* --- Debug overlay --- */}
      <div class="fixed bottom-2 right-2 bg-black/80 text-lcd-300 text-xs font-mono p-2 rounded pointer-events-none z-50">
        <div>nodes: {nodes.length} | edges: {rfEdges.length}</div>
        <div>measured: {measuredCount}/{nodes.length} | fallback: {dimsFallbackActive ? 'active' : 'idle'}</div>
        <div>graphKey: {graphKey.substring(0, 40)}</div>
      </div>
    </div>
  )
}
