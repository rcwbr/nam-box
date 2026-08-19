# Step-by-Step Guide: Provision rcwbr/mod-api Standalone Repository

This guide provisions a new repository at `rcwbr/mod-api` with development environment patterns from `mender-docker-lifecycle-helper`.

**Important**: Some steps require creating GitHub Apps and secrets BEFORE Codespaces will work. Follow the order carefully.

---

## Phase 1: Authentication Setup (Required Before Codespaces)

### Step 1: Create GitHub Apps

Create two GitHub Apps in your organization (rcwbr) before Codespaces can function:

| App | Permissions | Purpose |
|-----|-------------|---------|
| `mod-api-devcontainer` | Actions: Read | Cache devcontainer builds [Guide](https://github.com/rcwbr/devcontainer-cache-build) |
| `mod-api-release-it` | Contents: Read/Write | Automated releases [Guide](https://github.com/rcwbr/release-it-gh-workflow) |

**Steps for each App:**
1. Go to Organization Settings → Applications → GitHub Apps
2. Create new app
3. Generate private key
4. Note the App ID (needed for settings.yml)

### Step 2: Configure Repository Secrets

Add these secrets BEFORE pushing workflow code:

| Secret | Source | Used by |
|--------|--------|---------|
| `CODECOV_TOKEN` | [codecov.io](https://codecov.io) | pytest workflow |
| `RELEASE_IT_GITHUB_APP_KEY` | GitHub App private key (Step 1) | release-it workflow |
| `DOCS_GITHUB_APP_KEY` | GitHub App private key (create if using Pages) | pages workflow |

---

## Phase 2: Minimal Files for Working Codespace

### Step 3: Create Core Configuration Files

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mod-api"
version = "0.1.0"
description = "PLACEHOLDER: API service for mod-host control"
authors = [{ name = "rcwbr" }]
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "PLACEHOLDER-YOUR-DEPS-HERE"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=7.0.0",
    "httpx>=0.24.0",
]

[tool.setuptools.packages.find]
where = ["src"]
```

Create `.devcontainer/devcontainer.json` (full framework from start):

```json
{
  "containerEnv": {
    "DEVCONTAINER_HOST_WORKSPACE_MOUNT": "/var/lib/docker/codespacemount/workspace/mod-api",
    "DEVCONTAINER_WORKSPACE_PATH": "${containerWorkspaceFolder}",
    "PYTEST_DEBUG_TEMPROOT": "/var/pytest-tmp"
  },
  "customizations": {
    "vscode": {
      "extensions": [
        "hashicorp.hcl",
        "ms-azuretools.vscode-docker",
        "bierner.markdown-mermaid",
        "joshbolduc.commitlint",
        "ms-python.python",
        "ryanluker.vscode-coverage-gutters"
      ]
    }
  },
  "hostRequirements": {
    "cpus": 2,
    "memory": "8gb",
    "storage": "32gb"
  },
  "image": "mod-api-devcontainer",
  "initializeCommand": ".devcontainer/initialize",
  "mounts": [
    {
      "source": "/var/run/docker.sock",
      "target": "/var/run/docker.sock",
      "type": "bind"
    },
    {
      "source": "pytest-tmp",
      "target": "/var/pytest-tmp",
      "type": "volume"
    }
  ],
  "name": "mod-api",
  "onCreateCommand": "/opt/devcontainers/on_create_command"
}
```

Create `.devcontainer/devcontainer-bake.hcl`:

```hcl
variable "devcontainer_layers" {
  default = [
    "docker-client",
    "zsh-base",
    "zsh-thefuck-pyenv",
    "zsh",
    "tmux",
    "uv-project",
    "mod-api",
    "useradd",
    "pre-commit-base",
    "pre-commit-tool-image",
    "pre-commit",
  ]
}

target "docker-client" {
  contexts = {
    base_context = "docker-image://python:3.12.4"
  }
}

target "uv-project" {
  args = {
    UV_PACKAGE_NAME = "mod-api"
  }
}

target "mod-api" {
  dockerfile = "cwd://Dockerfile"
}
```

Create `.devcontainer/initialize`:

```bash
#!/bin/bash
set -ex

export DEVCONTAINER_IMAGE=mod-api-devcontainer
export DEVCONTAINER_REGISTRY=ghcr.io/rcwbr
export DEVCONTAINER_DEFINITION_TYPE=bake
export DEVCONTAINER_INITIALIZE_PID=$PPID
devcontainer_definition_files_arr=(
  devcontainer-bake.hcl
  docker-client/devcontainer-bake.hcl
  zsh/devcontainer-bake.hcl
  tmux/devcontainer-bake.hcl
  uv-project/devcontainer-bake.hcl
  useradd/devcontainer-bake.hcl
  pre-commit/devcontainer-bake.hcl
  cwd://.devcontainer/devcontainer-bake.hcl
)
DEVCONTAINER_DEFINITION_FILES="${devcontainer_definition_files_arr[*]}"
export DEVCONTAINER_DEFINITION_FILES
export DEVCONTAINER_CACHE_BUILD_IMAGE=ghcr.io/rcwbr/devcontainer-cache-build:41-merge-143d5ba93b595d7fe8fd0d23f42e3e4fd7d4cbd5
export DEVCONTAINER_BUILD_ADDITIONAL_ARGS="remote_definition=https://github.com/rcwbr/dockerfile-partials.git#0.12.1"
if [[ -z $# ]]; then
  export DEVCONTAINER_BUILD_ADDITIONAL_ARGS="$DEVCONTAINER_BUILD_ADDITIONAL_ARGS $*"
fi
curl https://raw.githubusercontent.com/rcwbr/devcontainer-cache-build/0.9.2/devcontainer-cache-build-initialize | bash
```

**Note**: The devcontainer uses the `devcontainer-cache-build-initialize` script which pulls layers from `rcwbr/dockerfile-partials`. After the first workflow run populates the cache, Codespaces will work with full functionality.

---

## Phase 3: Docker Configuration

### Step 4: Create Dockerfile and docker-bake.hcl

Create `Dockerfile` (uses bake multi-stage context):

```dockerfile
# hadolint ignore=DL3006
FROM base_context

COPY <<EOF /opt/mod-api/entrypoint
#!/bin/bash
set -e

cd /workspace
exec uv run mod-api "\$@"
EOF

RUN chmod +x /opt/mod-api/entrypoint

ENTRYPOINT ["/opt/mod-api/entrypoint"]
```

Create `docker-bake.hcl` (multi-stage build matching mender-helper pattern):

```hcl
group "default" {
  targets = ["uv-project"]
}

target "docker-client" {
  dockerfile = "docker-client/Dockerfile"
  contexts = {
    base_context = "docker-image://python:3.12.4"
    docker_image = "docker-image://docker:27.3.1-cli"
  }
  cache-from = [
    "type=registry,ref=\${IMAGE_REF}-cache-docker-client:main",
    "type=registry,ref=\${IMAGE_REF}-cache-docker-client:\${VERSION}"
  ]
  cache-to = [
    "type=registry,rewrite-timestamp=true,mode=max,ref=\${IMAGE_REF}-cache-docker-client:\${VERSION}"
  ]
  output = []
}

target "deps" {
  dockerfile = "cwd://Dockerfile"
  contexts = {
    base_context = "target:docker-client"
  }
  cache-from = [
    "type=registry,ref=\${IMAGE_REF}-cache-deps:main",
    "type=registry,ref=\${IMAGE_REF}-cache-deps:\${VERSION}"
  ]
  cache-to = [
    "type=registry,rewrite-timestamp=true,mode=max,ref=\${IMAGE_REF}-cache-deps:\${VERSION}"
  ]
  output = []
}

target "uv-project" {
  inherits = ["default"]
  contexts = {
    base_context = "target:deps"
    dep_docker_client = "target:docker-client"
  }
  args = {
    UV_PACKAGE_NAME = "mod-api"
  }
}
```

---

## Phase 4: DevContainer Cache Workflow (REQUIRED BEFORE DOCS)

### Step 6: Create CI Workflow for DevContainer

Create `.github/workflows/push-workflow.yaml` with only the devcontainer cache job:

```yaml
name: Push workflow
on:
  push:
    branches: [main]
    tags: ['*']
jobs:
  devcontainer-cache-build:
    uses: rcwbr/devcontainer-cache-build/.github/workflows/devcontainer-cache-build.yaml@0.9.2
    permissions:
      packages: write
```

### Step 7: Pre-commit Configuration

Create `.pre-commit-config.yaml`:

```yaml
default_install_hook_types:
  - pre-commit
  - commit-msg

repos:
- repo: https://github.com/psf/black-pre-commit-mirror
  rev: 24.8.0
  hooks: [{ id: black, language_version: python3.12.4 }]
- repo: https://github.com/alessandrojcm/commitlint-pre-commit-hook
  rev: v9.20.0
  hooks: [{ id: commitlint, stages: [commit-msg], additional_dependencies: ["@commitlint/config-conventional"] }]
- repo: https://github.com/executablebooks/mdformat
  rev: 0.7.17
  hooks:
  - id: mdformat
    exclude: '.github/ISSUE_TEMPLATE/.*\.md$'
    additional_dependencies:
    - mdformat-black
    - mdformat-config
    - mdformat-gfm-alerts
    - mdformat-shfmt
    - mdformat-tables
    - mdformat-toc
- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v5.0.0
  hooks:
  - id: check-added-large-files
  - id: check-case-conflict
  - id: check-json
  - id: check-merge-conflict
  - id: check-toml
  - id: check-vcs-permalinks
  - id: check-yaml
  - id: end-of-file-fixer
    exclude: '.github/ISSUE_TEMPLATE/.*\.md$'
  - id: forbid-submodules
  - id: mixed-line-ending
  - id: trailing-whitespace
    exclude: 'README.md'
- repo: local
  hooks:
  - id: hclfmt
    name: hclfmt
    language: docker_image
    entry: alpine/terragrunt:1.10.3 terragrunt hclfmt
    types: ["hcl"]
  - id: hadolint-docker
    name: Lint Dockerfiles
    language: docker_image
    types: ["dockerfile"]
    entry: ghcr.io/hadolint/hadolint:2.12.0 hadolint
  - id: commitlint-ci
    name: commitlint-ci
    stages: [manual]
    always_run: true
    language: node
    additional_dependencies: ["@commitlint/config-conventional"]
    entry: bash
    args: ["-c", "npx commitlint --from $PRE_COMMIT_FROM_COMMIT --to $PRE_COMMIT_TO_COMMIT"]
    pass_filenames: false
```

---

## Phase 5: Enhanced CI/CD Workflows

### Step 8: Full CI Workflow (DevContainer image must be cached first)

Update `.github/workflows/push-workflow.yaml` to add all jobs including release-it:

```yaml
name: Push workflow
on:
  push:
    branches: [main]
    tags: ['*']
  pull_request:
jobs:
  devcontainer-cache-build:
    uses: rcwbr/devcontainer-cache-build/.github/workflows/devcontainer-cache-build.yaml@0.9.2
    permissions:
      packages: write

  release-it-workflow:
    needs: devcontainer-cache-build
    uses: rcwbr/release-it-gh-workflow/.github/workflows/release-it-workflow.yaml@0.5.2
    with:
      app-id: YOUR_APP_ID # mod-api release-it app
      app-environment: Repo release
      release-it-config: .release-it.json
      release-it-image: ghcr.io/rcwbr/release-it-docker-file-bumper:0.8.1
    secrets:
      app-secret: ${{ secrets.RELEASE_IT_GITHUB_APP_KEY }}

  pre-commit:
    if: github.event_name == 'pull_request'
    uses: rcwbr/dockerfile-partials/.github/workflows/pre-commit.yaml@0.4.0
    needs: devcontainer-cache-build
    with:
      pre-commit-image: ${{ fromJSON(needs.devcontainer-cache-build.outputs.devcontainer-cache-image-all_configs).target.pre-commit.args.DEVCONTAINER_PRE_COMMIT_IMAGE }}

  pytest:
    runs-on: ubuntu-24.04
    if: github.event_name == 'pull_request'
    needs: devcontainer-cache-build
    container:
      image: ${{ needs.devcontainer-cache-build.outputs.devcontainer-cache-image-ref }}
      options: --user root
    steps:
      - uses: actions/checkout@v4.1.7
      - name: Run tests and coverage
        env:
          DEVCONTAINER_HOST_WORKSPACE_MOUNT: ${{ github.workspace }}
          DEVCONTAINER_WORKSPACE_PATH: ${{ github.workspace }}
          PYTEST_DEBUG_TEMPROOT: ${{ runner.temp }}
        run: |
          pip install -e ".[dev]"
          pytest --cov=src --cov-branch --cov-report=xml --junitxml=junit.xml -vv --tb=long -o log_cli=true -o log_cli_level=DEBUG tests/unit
      - uses: codecov/codecov-action@v5.5.1
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
      - uses: codecov/codecov-action@v5.5.1
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          report_type: test_results
          files: junit.xml

  pages:
    if: github.event_name != 'pull_request'
    runs-on: ubuntu-24.04
    needs: devcontainer-cache-build
    container:
      image: ${{ needs.devcontainer-cache-build.outputs.devcontainer-cache-image-ref }}
      options: --user root
    permissions:
      pages: write
      id-token: write
    steps:
      - uses: actions/create-github-app-token@v2.2.1
        with:
          app-id: YOUR_DOCS_APP_ID # mod-api CI docs app
          private-key: ${{ secrets.DOCS_GITHUB_APP_KEY }}
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
      - uses: actions/configure-pages@v5
      - name: Deploy docs
        run: |
          pip install -e ".[dev]"
          mike deploy --branch mkdocs --update-aliases --push $(echo ${{ github.ref_name }} | sed 's|/|-|g')
      - uses: actions/checkout@v6
        with:
          ref: mkdocs
      - uses: actions/upload-pages-artifact@v3
        with:
          path: '.'
      - uses: actions/deploy-pages@v5
        with:
          token: ${{ github.token }}

  pypi-publish:
    if: ${{ github.ref_type == 'tag' }}
    runs-on: ubuntu-24.04
    environment:
      name: pypi
    needs: devcontainer-cache-build
    container:
      image: ${{ needs.devcontainer-cache-build.outputs.devcontainer-cache-image-ref }}
      options: --user root
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v6
      - run: $UV_PROJECT_ENVIRONMENT/bin/uv build
      - run: $UV_PROJECT_ENVIRONMENT/bin/uv publish
```

---

## Phase 6: Documentation and Templates

### Step 9: Documentation Configuration

Create `mkdocs.yml`:

```yaml
site_name: mod-api
repo_url: https://github.com/rcwbr/mod-api
theme:
  name: material
plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          options:
            show_source: true
nav:
  - Home: index.md
  - API Reference: api.md
```

Create `docs/index.md`:
```markdown
# mod-api
PLACEHOLDER: Brief project description.
```

Create `docs/api.md`:
```markdown
# API Reference

::: mod_api
    handler: python
    selection:
      members: true
```

### Step 10: Issue and PR Templates

Create `.github/ISSUE_TEMPLATE/config.yml`:
```yaml
blank_issues_enabled: false
```

Create `.github/ISSUE_TEMPLATE/bug.md`:
```markdown
---
name: Bug report
about: Report a bug
title: '[Bug]: '
labels: bug
---

**Describe the bug**

**To Reproduce**
1. ...
2. ...
```

Create `.github/ISSUE_TEMPLATE/feature.md`:
```markdown
---
name: Feature request
about: Suggest a feature
title: '[Feature]: '
labels: enhancement
---

**Is your feature related to a problem?**
```

Create `.github/pull_request_template.md`:
```markdown
## Description

## Related Issue

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
```

### Step 11: Repository Settings

Create `.github/settings.yml` for branch protection rules:

```yaml
repository:
  name: mod-api
  description: API service for mod-host control
  default_branch: main
  allow_squash_merge: false
  allow_rebase_merge: false
  allow_merge_commit: true
  delete_branch_on_merge: true

rulesets:
  - name: Default branch rules
    target: branch
    enforcement: active
    conditions:
      ref_name:
        include: ["~DEFAULT_BRANCH"]
    bypass_actors:
      - actor_id: 5
        actor_type: RepositoryRole
        bypass_mode: pull_request
    rules:
      - type: creation
      - type: deletion
      - type: non_fast_forward
      - type: required_status_checks
        parameters:
          required_status_checks:
            - context: Build Docker images
            - context: devcontainer-cache-build
            - context: pre-commit
            - context: pytest
      - type: pull_request
        parameters:
          required_review_thread_resolution: true

environments:
  - name: github-pages
  - name: pypi
```

---

## Phase 7: Release Automation and Final Steps

### Step 12: Release Configuration

Create `.release-it.json`:

```json
{
  "extends": ["github:rcwbr/release-it-docker/file-bumper#0.8.0"],
  "github": { "release": true },
  "hooks": {
    "after:bump": [
      "docker run --rm -v $(pwd):$(pwd) -w $(pwd) ghcr.io/astral-sh/uv:0.9.11-python3.12-trixie-slim uv version ${version}"
    ]
  },
  "plugins": {
    "@release-it/bumper": {
      "out": [
        {"file": "pyproject.toml", "type": "text/plain"}
      ]
    }
  }
}
```

Create `.codecov.yml` for coverage requirements:

```yaml
coverage:
  status:
    project:
      default:
        target: auto
    patch:
      default:
        target: auto
```

---

### Step 13: Initial Commit and Push

### Step 12: Initial Commit and Push

```bash
git add .devcontainer/ .github/ .vscode/ .pre-commit-config.yaml \
       pyproject.toml docker-bake.hcl Dockerfile mkdocs.yml VERSION .codecov.yml

git commit -m "feat: initial project setup"

gh repo create rcwbr/mod-api --public --source=. --remote=origin
git push -u origin main
```

### Step 13: Trigger First Build

After push, manually run the `devcontainer-cache-build` workflow to populate the image cache. This enables Codespaces.
Visit Actions tab → Select `devcontainer-cache-build` → Run workflow manually.

---

## Authentication Reference

| Component | Docs Link | Secret Required |
|-----------|-----------|---------------|
| DevContainer Cache | https://github.com/rcwbr/devcontainer-cache-build | None (uses defaults) |
| Release-it | https://github.com/rcwbr/release-it-gh-workflow | `RELEASE_IT_GITHUB_APP_KEY` |
| Codecov | https://docs.codecov.com | `CODECOV_TOKEN` |
| GitHub Pages | https://github.com/rcwbr/release-it-gh-workflow | `DOCS_GITHUB_APP_KEY` |

---

## Working Sequence Summary

1. **Create GitHub Apps** (Step 1) - Required for release-it workflow
2. **Configure Secrets** (Step 2) - Required for later workflows
3. **Push core config** (Steps 3-5) - pyproject.toml, devcontainer, Dockerfile
4. **Push CI workflow** (Step 6) - Triggers first `devcontainer-cache-build`
5. **Trigger first workflow manually** - Populates GHCR cache
6. **Codespaces enabled** - Full dev environment works