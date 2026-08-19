import '@xyflow/react/dist/style.css'

import {
  ReactFlow,
  Background,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeTypes,
} from '@xyflow/react'

const nodeTypes: NodeTypes = {
  testNode: ({ data }: { data: { label: string } }) => (
    <div class="relative p-2 bg-black border-2 border-lcd-400 rounded-sm text-lcd-200 text-xs min-w-[120px]">
      <Handle type="target" position={Position.Top} id="input" isConnectable={false} />
      <div class="text-center">{data.label}</div>
      <Handle type="source" position={Position.Bottom} id="output" isConnectable={false} />
    </div>
  )
}

const nodes: Node[] = [
  { id: 'input-1', type: 'input', position: { x: 50, y: 50 }, data: { label: 'Input 1' } },
  { id: 'effect-1', type: 'testNode', position: { x: 100, y: 150 }, data: { label: 'Effect 1' } },
  { id: 'output-1', type: 'output', position: { x: 50, y: 300 }, data: { label: 'Output 1' } },
]

const edges: Edge[] = [
  { id: 'e1-2', source: 'input-1', target: 'effect-1', targetHandle: 'input' },
  { id: 'e2-3', source: 'effect-1', target: 'output-1', sourceHandle: 'output' },
]

export default function TestDAG() {
  return (
    <div class="border-2 border-lcd-400 rounded-sm bg-black overflow-hidden mx-auto" style={{ width: '340px', height: '400px' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2, minZoom: 0.4, maxZoom: 1.5 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        selectionOnDrag={false}
        panOnDrag={false}
        panOnScroll={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
        preventScrolling={true}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#facc15" gap={20} />
      </ReactFlow>
    </div>
  )
}
