# FastAPI API Documentation Generation

This document describes how to generate API documentation from FastAPI endpoint docstrings and integrate them with MkDocs.

## Overview

FastAPI automatically extracts docstrings from endpoint handlers and includes them in the OpenAPI schema. This documentation can be rendered in MkDocs using the `mkdocs-swagger-ui-tag` plugin with a pre-build hook.

## How FastAPI Extracts Docstrings

FastAPI automatically extracts the **entire docstring** as the OpenAPI `description` field. Markdown formatting in docstrings is preserved and rendered correctly in Swagger UI.

### Current Docstring Format

The mod-api service uses Google-style docstrings:

```python
@router.get("/pedalboards/{pedalboard_id}")
async def get_pedalboard(pedalboard_id: int, store: PedalboardStore = Depends(get_pedalboard_store)) -> Pedalboard:
    """Get full details of a specific pedalboard.

    Args:
        pedalboard_id: The ID of the pedalboard to retrieve.

    Returns:
        Pedalboard object with all effects and connections.

    Raises:
        HTTPException: 404 if pedalboard ID doesn't exist.
    """
```

### Best Practices for FastAPI Docstrings

1. **Markdown support** - Use `**bold**` for emphasis, backticks for code, and lists for formatting
2. **Avoid f-strings** - f-string docstrings don't populate `__doc__` attribute

## Offline OpenAPI Generation via MkDocs Hook

### Directory Structure

```
docs/
├── index.md
├── api/
│   └── reference.md      # Contains swagger-ui tag
└── openapi.json          # Generated automatically by hook
scripts/
└── generate_openapi.py   # OpenAPI generation script
mkdocs.yml               # MkDocs configuration
```

### Step 1: Create OpenAPI Generation Script

Create `scripts/generate_openapi.py`:

```python
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "mod-api" / "src"))

from mod_api.main import app

def on_pre_build(config, **kwargs):
    """Generate OpenAPI spec before MkDocs build."""
    spec = app.openapi()
    output_path = Path(__file__).parent.parent / "docs" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(spec, f, indent=2)

if __name__ == "__main__":
    on_pre_build(None)
```

### Step 2: Configure mkdocs.yml with Built-in Hooks

```yaml
site_name: Pedalboard API Documentation
theme:
  name: material

plugins:
  - search
  - swagger-ui-tag

hooks:
  - scripts/generate_openapi.py:on_pre_build

nav:
  - Home: index.md
  - API Reference: api/reference.md
```

### Step 3: Create the API Reference Page

```markdown
<!-- docs/api/reference.md -->
# API Reference

<swagger-ui src="../openapi.json"/>
```
