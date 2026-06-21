# API Endpoints Behavior Documentation

This document describes the actual tested behavior of each API endpoint used by `services/web/src/pages/effects.astro`.

## Overview

The application uses two backend services accessible through Traefik routing:

- **effects service** (mod-ui): Pedalboard and Effect management at `/api/effects/*`
- **model service** (file_api): NAM model file management at `/api/model/*`

______________________________________________________________________

## Pedalboard Endpoints (via mod-ui)

### GET /api/effects/pedalboard/list

**Purpose:** Load all pedalboards (user + factory) into the selector dropdown.

**Used in:** `loadPedalboards()` function

**Actual Response Tested:**

```json
[
  { "bundle": "/root/.pedalboards/default.pedalboard", "title": "Default", "broken": false, "factory": false, ... },
  { "bundle": "/root/.pedalboards/my.pedalboard", "title": "my", "broken": true, ... }
]
```

**Response Structure:**

- Returns a JSON array of pedalboard objects
- Each pedalboard has `bundle` (path) and `title` (display name)
- Optional fields: `broken`, `factory`, `hasTrialPlugins`, `uri`, `version`

______________________________________________________________________

### GET /api/effects/pedalboard/info/?bundlepath={path}

**Purpose:** Load the current pedalboard's effects/plugins to display in the UI.

**Used in:** `loadCurrentPedalboard()` function

**Actual Response Tested:**

```json
{
  "title": "Default",
  "plugins": [
    {
      "instance": "nam1",  // Note: NOT prefixed with /graph/
      "uri": "http://github.com/mikeoliphant/neural-amp-modeler-lv2",
      "x": 0, "y": 0,
      "ports": [  // Note: current values are in ports, not parameters
        { "symbol": "input_level", "value": 0.0 },
        { "symbol": "output_level", "value": 0.0 },
        { "symbol": "quality_scale", "value": 1.0 }
      ]
    }
  ],
  "connections": [],
  "hardware": {...}
}
```

**Key Observations:**

- ⚠️ Instance format may be `/nam1` (with leading slash) or `nam1` depending on the saved state
- ⚠️ For parameter set API, we need to convert to `/graph/nam1` format
- ✅ Current parameter values are in `ports[].value`

______________________________________________________________________

### POST /api/effects/pedalboard/load_bundle/?bundlepath={path}

**Purpose:** Load a selected pedalboard from the dropdown.

**Used in:** `loadPedalboardBtn` click handler

**Actual Response Tested:**

```json
{
  "ok": true,
  "name": "Default"
}
```

**Response Structure:**

- Method: POST
- Takes `bundlepath` query parameter
- Returns `{ ok: true, name: "..." }` on success

______________________________________________________________________

### POST /api/effects/pedalboard/save?title={title}&asNew={0|1}

**Purpose:** Save current pedalboard or create a new one.

**Used in:**

- `savePedalboardBtn` click handler - saves current state
- `confirmCreatePedalboard` click handler - creates new with `asNew=1`

**Actual Response Tested:**

```json
{
  "ok": true,
  "bundlepath": "/root/.pedalboards/TestPedalboard.pedalboard",
  "title": "TestPedalboard"
}
```

**Response Structure:**

- Method: POST
- `title` query parameter: pedalboard name
- `asNew` query parameter: `1` to create new, `0` or omitted to save in-place
- Returns `{ ok: true, bundlepath, title }` on success

______________________________________________________________________

## Effect Endpoints (via mod-ui)

### GET /api/effects/effect/list

**Purpose:** Load available effects/plugins to select from and add to pedalboard.

**Used in:** `loadEffects()` function

**Actual Response Tested:**

```json
[
  {
    "uri": "http://github.com/mikeoliphant/neural-amp-modeler-lv2",
    "name": "Neural Amp Modeler",
    "brand": "Mike Oliphant",
    "category": ["Simulator"],
    "ports": {...},
    "parameters": [{ "uri": "...#model", "label": "Neural Model", ... }]
  }
]
```

**Response Fields Used:**

- `uri` - used for click handler data attribute
- `name` - display name
- `brand` - manufacturer (fallback to "Unknown" if missing)

______________________________________________________________________

### GET /api/effects/effect/get?uri={uri}

**Purpose:** Load effect parameters for configuration UI.

**Used in:** `loadEffectParameters()` function

**Actual Response Structure:**

```json
{
  "uri": "http://github.com/mikeoliphant/neural-amp-modeler-lv2",
  "parameters": [
    {
      "uri": "http://github.com/mikeoliphant/neural-amp-modeler-lv2#model",
      "label": "Neural Model",
      "ranges": {
        "minimum": "",
        "maximum": "",
        "default": ""
      }
    }
  ],
  "ports": {
    "control": {
      "input": [
        {
          "symbol": "input_level",
          "name": "Input Lvl",
          "ranges": {
            "minimum": -20.0,
            "maximum": 20.0,
            "default": 0.0
          },
          "value": 0.0
        },
        {
          "symbol": "output_level",
          "name": "Output Lvl",
          "ranges": {
            "minimum": -20.0,
            "maximum": 20.0,
            "default": 0.0
          },
          "value": 0.0
        },
        {
          "symbol": "quality_scale",
          "name": "Quality",
          "ranges": {
            "minimum": 0.0,
            "maximum": 1.0,
            "default": 1.0
          },
          "value": 1.0
        }
      ]
    }
  }
}
```

**Key Observations for Code:**

- `parameters` array may contain model file parameter (empty min/max/default)
- `ports.control.input` contains actual control parameters with `symbol`, `name`, `ranges`, and `value`
- Code must map `label` → `name`, `ranges.minimum` → `min`, etc.

______________________________________________________________________

### GET /api/effects/effect/add/{instance}?uri={uri}

**Purpose:** Add an effect to the current pedalboard.

**Used in:** `addEffectBtn` click handler

**Actual Response:**

- Returns full plugin info object on success
- Method: GET

**URL Format Notes:**

- Instance format is just the unique name (e.g., `nam1`), NOT `/graph/nam1`
- Correct URL: `/api/effects/effect/add/nam1?uri=http://...`
- Traefik strips `/api/effects/` prefix

______________________________________________________________________

### POST /api/effects/effect/parameter/set/

**Purpose:** Set a parameter value on an effect plugin.

**Used in:**

- `setEffectParameter()` function - for effect parameters
- Model selection handler - for NAM model selection
- Model upload handler - for auto-selecting uploaded models

**Actual Request Format Tested:**

```
Body: <plugin_uri>/<instance>/<param_symbol_or_property_uri>/<value>
```

**Examples that work:**

```
# For control parameters:
http://github.com/mikeoliphant/neural-amp-modeler-lv2/graph/nam1/input_level/10.0
http://github.com/mikeoliphant/neural-amp-modeler-lv2/graph/nam1/output_level/-6.0
http://github.com/mikeoliphant/neural-amp-modeler-lv2/graph/nam1/quality_scale/0.8

# For NAM model:
http://github.com/mikeoliphant/neural-amp-modeler-lv2/graph/nam1/http://github.com/mikeoliphant/neural-amp-modeler-lv2#model//opt/nam/models/model.nam
```

**Response:** `true` or `false` (plain text)

______________________________________________________________________

## Model Endpoints (via file_api)

### GET /api/model/all

**Purpose:** List available NAM model files for the model selector dropdown.

**Used in:** `loadModels()` function

**Actual Response Tested:**

```json
[
  {
    "name": "BossWN-feather.nam",
    "size": 65266,
    "path": "/opt/nam/models/BossWN-feather.nam"
  },
  {
    "name": "Recti Core Lead \u2013 Diode.nam",
    "size": 282651,
    "path": "/opt/nam/models/Recti Core Lead \u2013 Diode.nam"
  }
]
```

**Response Structure:**

- Returns JSON array of FileInfo objects
- Each file has `name`, `size`, and `path` properties
- Only `.nam` files are listed (configured via `FILE_EXTENSIONS`)

______________________________________________________________________

### POST /api/model/upload

**Purpose:** Upload a .nam model file to the models directory.

**Used in:** `modelUpload` change handler

**Actual Request:**

- Method: POST
- Content-Type: `multipart/form-data`
- Form field: `file` containing the .nam file

**Actual Response:**

```json
{
  "status": "uploaded",
  "uploaded": "test-model.nam",
  "path": "/opt/nam/models/test-model.nam",
  "action_result": null
}
```

**Response Structure:**

- `status`: "uploaded"
- `uploaded`: filename
- `path`: full path
- `action_result`: null (or result of post-upload hook)

______________________________________________________________________

## Code Updates Made

### 1. `loadEffectParameters()` function

Updated to handle `ports.control.input` for control parameters:

```typescript
// Collect parameters from both parameters array and ports.control.input
let parameters: any[] = [];

// For NAM models, parameters array contains model path parameter
if (effectData.parameters && effectData.parameters.length > 0) {
  parameters = effectData.parameters.map((p: any) => ({
    key: p.uri?.split('#').pop() || p.label?.toLowerCase().replace(/\s+/g, '_'),
    name: p.label || p.name || p.uri?.split('#').pop(),
    min: p.ranges?.minimum ?? 0,
    max: p.ranges?.maximum ?? 1,
    step: 0.01,
    value: 0,
    default: 0
  }));
}

// For control parameters, use ports.control.input (has actual min/max/step values)
const controlParams = effectData.ports?.control?.input || [];
if (controlParams.length > 0) {
  controlParams.forEach((p: any) => {
    parameters.push({
      key: p.symbol,
      name: p.name,
      min: p.ranges?.minimum ?? 0,
      max: p.ranges?.maximum ?? 1,
      step: 0.01,
      value: p.value ?? p.ranges?.default ?? 0.5,
      default: p.ranges?.default ?? 0.5
    });
  });
}
```

### 2. `setEffectParameter()` function

Fixed to handle various instance formats and convert to `/graph/` format:

```typescript
let instancePath: string;
if (instance.startsWith('/graph/')) {
  instancePath = instance;
} else if (instance.startsWith('/')) {
  // instance is already /nam1 format, convert to /graph/nam1
  instancePath = `/graph${instance}`;
} else {
  // instance is just nam1, convert to /graph/nam1
  instancePath = `/graph/${instance}`;
}
body: `${uri}${instancePath}/${key}/${value}`
```

### 3. `loadCurrentModel()` function

Updated to show "Configure via selector" when NAM plugin exists (since pedalboard.info doesn't return current model value).

### 4. Model selection and upload handlers

Fixed body format (removed extra slash):

```typescript
// Before (incorrect):
body: `${PLUGIN_URI}//graph/nam1/${MODEL_PROPERTY}/${encodeURIComponent(modelPath)}`

// After (correct):
body: `${PLUGIN_URI}/graph/nam1/${MODEL_PROPERTY}/${encodeURIComponent(modelPath)}`
```

### 5. Effect add URL

Fixed to use `nam1` instead of `//graph/nam1`:

```typescript
// Before (incorrect):
`/api/effects/effect/add//graph/nam1?uri=${encodeURIComponent(selectedEffectUri)}`

// After (correct):
`/api/effects/effect/add/nam1?uri=${encodeURIComponent(selectedEffectUri)}`
```

### 6. Broken pedalboard filtering

Added filter to exclude broken pedalboards from the selector to prevent errors:

```typescript
pedalboards = (data || []).filter((pb: Pedalboard) => !pb.broken);
```

### 7. Effect info 404 handling

Added graceful handling for plugins that return 404 (effect no longer available):

```typescript
if (!response.ok) {
  controls.innerHTML = '<p class="text-lcd-500 text-xs">Effect not available</p>';
  return;
}
```

### 8. Pedalboard creation UI refresh

Fixed to properly set current pedalboard and refresh the UI after creation:

```typescript
const data = await response.json();
currentPedalboardPath = data.bundlepath;  // Set the new pedalboard as current
loadPedalboards();  // Refresh the dropdown
loadCurrentPedalboard();  // Show the new pedalboard's effects (will be empty)
```

### 9. Pedalboard save fix

Fixed to use the selected pedalboard's title and `asNew=0` for in-place save:

```typescript
const selectedOption = pedalboardSelector.options[pedalboardSelector.selectedIndex];
const title = selectedOption ? selectedOption.textContent : 'My Pedalboard';
const response = await fetch(`/api/effects/pedalboard/save?title=${encodeURIComponent(title)}&asNew=0`, { method: 'POST' });
```

Note: The mod-ui API requires `title` parameter and `asNew=0` for in-place saves.
