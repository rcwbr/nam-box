/**
 * Mock mod-api server for testing the PedalboardDAG component.
 *
 * Simulates the FastAPI backend endpoints used by the frontend:
 *   GET  /api/effects/pedalboards            → list all pedalboards
 *   GET  /api/effects/pedalboards/current    → current pedalboard
 *   GET  /api/effects/pedalboards/{id}      → specific pedalboard (with effects + connections)
 *   GET  /api/effects/pedalboards/{id}/ports → all ports (system + effect)
 *   GET  /api/effects/effects                → effect catalog
 *   POST /api/effects/pedalboards/{id}/connections → create a connection
 *   DELETE /api/effects/pedalboards/{id}/connections/{cid} → delete a connection
 *   GET  /api/model/all                      → NAM model files
 */

const http = require('http')

// ── Mock data ──────────────────────────────────────────────────────────────

// A NAM neural amp modeler effect (from the NAM LV2 plugin)
const NAM_EFFECT_URI = 'http://github.com/sdatkinson/neural-amp-modeler-lv2'

const pedalboards = {
  1: {
    id: 1,
    name: 'Test Pedalboard',
    file: 'test-pedalboard.json',
    effects: {
      1: {
        id: 1,
        uri: NAM_EFFECT_URI,
        name: 'NAM Model',
        ports: [
          { name: 'in', type: 'input', owner_type: 'effect', effect_instance_id: 1 },
          { name: 'out', type: 'output', owner_type: 'effect', effect_instance_id: 1 },
        ],
        parameters: {
          input_level: { name: 'input_level', type: 'number', min: 0.0, max: 2.0, default: 1.0, value: 1.0 },
          output_level: { name: 'output_level', type: 'number', min: 0.0, max: 2.0, default: 1.0, value: 1.0 },
          model: { name: 'model', type: 'filename', default: '', value: '' },
        },
      },
      2: {
        id: 2,
        uri: 'http://drobilla.net/plugins/lv2/gc5.calf.so',
        name: 'Tube Screamer',
        ports: [
          { name: 'in', type: 'input', owner_type: 'effect', effect_instance_id: 2 },
          { name: 'out', type: 'output', owner_type: 'effect', effect_instance_id: 2 },
        ],
        parameters: {
          drive: { name: 'drive', type: 'number', min: 0.0, max: 1.0, default: 0.5, value: 0.5 },
          level: { name: 'level', type: 'number', min: 0.0, max: 1.0, default: 0.5, value: 0.5 },
        },
      },
    },
    connections: {
      1: { id: 1, input_port_id: 'effect_1:in', output_port_id: 'system:capture_1' },
      2: { id: 2, input_port_id: 'effect_2:in', output_port_id: 'effect_1:out' },
      3: { id: 3, input_port_id: 'system:playback_1', output_port_id: 'effect_2:out' },
    },
  },
}

const effectCatalog = [
  {
    uri: NAM_EFFECT_URI,
    name: 'NAM Neural Amp Modeler',
    ports: [
      { name: 'in', type: 'input' },
      { name: 'out', type: 'output' },
    ],
    parameters: { model: { name: 'model', type: 'filename', default: '' } },
  },
  {
    uri: 'http://drobilla.net/plugins/lv2/gc5.calf.so',
    name: 'Tube Screamer',
    ports: [
      { name: 'in', type: 'input' },
      { name: 'out', type: 'output' },
    ],
    parameters: {
      drive: { name: 'drive', type: 'number', min: 0.0, max: 1.0, default: 0.5 },
      level: { name: 'level', type: 'number', min: 0.0, max: 1.0, default: 0.5 },
    },
  },
]

const modelFiles = [
  { name: 'model1.nam', size: 1024000, path: '/opt/nam/models/model1.nam' },
  { name: 'model2.nam', size: 2048000, path: '/opt/nam/models/model2.nam' },
]

const systemPorts = [
  { name: 'capture_1', type: 'input', owner_type: 'system', effect_instance_id: null },
  { name: 'capture_2', type: 'input', owner_type: 'system', effect_instance_id: null },
  { name: 'playback_1', type: 'output', owner_type: 'system', effect_instance_id: null },
  { name: 'playback_2', type: 'output', owner_type: 'system', effect_instance_id: null },
]

// ── Request handler ────────────────────────────────────────────────────────

const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost')
  const path = url.pathname
  const method = req.method

  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type')

  if (method === 'OPTIONS') {
    res.writeHead(200)
    res.end()
    return
  }

  // GET /api/effects/pedalboards
  if (method === 'GET' && path === '/api/effects/pedalboards') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(pedalboards))
    return
  }

  // GET /api/effects/pedalboards/current
  if (method === 'GET' && path === '/api/effects/pedalboards/current') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(pedalboards[1]))
    return
  }

  // GET /api/effects/pedalboards/{id}
  const pbMatch = path.match(/^\/api\/effects\/pedalboards\/(\d+)$/)
  if (method === 'GET' && pbMatch) {
    const id = parseInt(pbMatch[1])
    if (pedalboards[id]) {
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify(pedalboards[id]))
    } else {
      res.writeHead(404, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ detail: 'Not found' }))
    }
    return
  }

  // GET /api/effects/pedalboards/{id}/ports
  const portsMatch = path.match(/^\/api\/effects\/pedalboards\/(\d+)\/ports$/)
  if (method === 'GET' && portsMatch) {
    const id = parseInt(portsMatch[1])
    if (pedalboards[id]) {
      const pb = pedalboards[id]
      const allPorts = [...systemPorts]
      for (const [eid, effect] of Object.entries(pb.effects)) {
        for (const port of effect.ports) {
          allPorts.push({ ...port, owner_type: 'effect', effect_instance_id: parseInt(eid) })
        }
      }
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify(allPorts))
    } else {
      res.writeHead(404, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ detail: 'Not found' }))
    }
    return
  }

  // GET /api/effects/effects
  if (method === 'GET' && path === '/api/effects/effects') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(effectCatalog))
    return
  }

  // POST /api/effects/pedalboards/{id}/connections
  const connPostMatch = path.match(/^\/api\/effects\/pedalboards\/(\d+)\/connections$/)
  if (method === 'POST' && connPostMatch) {
    let body = ''
    req.on('data', chunk => body += chunk)
    req.on('end', () => {
      const request = JSON.parse(body)
      const id = parseInt(connPostMatch[1])
      const pb = pedalboards[id]
      if (!pb) {
        res.writeHead(404, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ detail: 'Not found' }))
        return
      }
      const newId = Math.max(0, ...Object.keys(pb.connections).map(k => parseInt(k))) + 1
      const conn = {
        id: newId,
        input_port_id: request.input_port_id,
        output_port_id: request.output_port_id,
      }
      pb.connections[newId] = conn
      res.writeHead(201, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify(conn))
    })
    return
  }

  // DELETE /api/effects/pedalboards/{id}/connections/{cid}
  const connDelMatch = path.match(/^\/api\/effects\/pedalboards\/(\d+)\/connections\/(\d+)$/)
  if (method === 'DELETE' && connDelMatch) {
    const pid = parseInt(connDelMatch[1])
    const cid = parseInt(connDelMatch[2])
    const pb = pedalboards[pid]
    if (pb && pb.connections[cid]) {
      delete pb.connections[cid]
      res.writeHead(204)
      res.end()
    } else {
      res.writeHead(404, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ detail: 'Not found' }))
    }
    return
  }

  // GET /api/model/all
  if (method === 'GET' && path === '/api/model/all') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(modelFiles))
    return
  }

  // Fallback
  res.writeHead(404, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify({ detail: `No route for ${method} ${path}` }))
})

const PORT = 8001
server.listen(PORT, () => {
  console.log(`Mock API server running on port ${PORT}`)
})
