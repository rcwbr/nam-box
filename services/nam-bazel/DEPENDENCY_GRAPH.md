# NAM LV2 Bazel Dependency Graph and Build Plan

A comprehensive analysis of package relationships and build strategy for the NAM LV2 Bazel migration.

## Package Overview Table

| Package | Type | Source | BUILD File |
|---------|------|--------|------------|
| `nam_lv2` | Main Repo | git: ce7cbeb | `thirdparty/nam_lv2.BUILD` |
| `neural_audio` | Submodule | git: 4c9d20e | `thirdparty/neural_audio.BUILD` |
| `neural_amp_modeler_core` | Submodule | git: e181f61e | `thirdparty/nam_core.BUILD` |
| `rtneural` | Submodule | git: 5909c44 | `thirdparty/rtneural.BUILD` |
| `math_approx` | Submodule | git: f6d55e7 | `thirdparty/math_approx.BUILD` |
| `xsimd` | Submodule | git: a00c81f | `thirdparty/xsimd.BUILD` |
| `eigen` | BCR | 5.0.1 | `@eigen//:eigen` |
| `nlohmann_json` | Archive | v3.12.0 | `thirdparty/nlohmann_json.BUILD` |
| `lv2_headers` | Archive | 1.18.10 | `thirdparty/lv2.BUILD` |
| `jalv` | LV2 Host | git: v1.8.0 | `thirdparty/jalv.BUILD` |
| `zix` | git | 0.5.2 | `thirdparty/zix.BUILD` |
| `serd` | git | 0.32.2 | `thirdparty/serd.BUILD` |
| `sord` | git | 0.16.14 | `thirdparty/sord.BUILD` |
| `sratom` | git | 0.6.14 | `thirdparty/sratom.BUILD` |
| `lilv` | git | 0.24.20 | `thirdparty/lilv.BUILD` |
| `suil` | git | 0.10.22 | `thirdparty/suil.BUILD` |

## Dependency Graph

```
neural_amp_modeler.lv2 (cc_binary)
├── @neural_audio//:neural_audio
│   ├── @neural_amp_modeler_core//:nam_core
│   │   ├── @eigen//:eigen
│   │   └── @nlohmann_json//:json
│   ├── @rtneural//:rtneural
│   │   ├── @xsimd//:xsimd
│   │   ├── @eigen//:eigen
│   │   └── :bundled_modules (local)
│   ├── @math_approx//:math_approx
│   ├── @nlohmann_json//:json
│   └── @eigen//:eigen
├── @lv2_headers//:lv2
└── :denormal (local)

# Jalv LV2 Host - Bazel-native build
jalv (cc_binary)
├── @lv2_headers//:lv2
├── @lilv//:lilv
│   ├── @sratom//:sratom
│   │   ├── @sord//:sord
│   │   │   └── @serd//:serd
│   │   └── @serd//:serd
│   ├── @sord//:sord
│   ├── @serd//:serd
│   ├── @zix//:zix
│   └── @lv2_headers//:lv2
├── @suil//:suil
│   ├── @lilv//:lilv
│   ├── @lv2_headers//:lv2
│   └── @zix//:zix
├── @zix//:zix
├── @sratom//:sratom
├── @serd//:serd
└── @sord//:sord
(requires system libjack at link/runtime)
```

## Detailed Package Analysis

### 1. `nam_lv2` - Main LV2 Plugin

**Purpose**: The main neural-amp-modeler-lv2 application that produces a shared library LV2 plugin.

**BUILD Target**: `@nam_lv2//:neural_amp_modeler`

**Dependencies**:
- `@neural_audio//:neural_audio` - Core neural network inference
- `@lv2_headers//:lv2` - LV2 API headers
- `:denormal` - Local denormal helper

**Build Configuration**:
```python
cc_binary(
    name = "neural_amp_modeler",
    srcs = glob(["src/*.cpp", "src/*.h"]),
    deps = [
        "@neural_audio//:neural_audio",
        "@lv2_headers//:lv2",
        ":denormal",
    ],
    linkshared = True,  # Produces .so LV2 plugin
)
```

**Key Concerns**:
- Output path: `bazel-bin/neural_amp_modeler.lv2`
- Requires denormal utilities from `deps/denormal/architecture.hpp`

---

### 2. `neural_audio` - Neural Network Audio Processing

**Purpose**: High-level audio processing library that uses NeuralAmpModelerCore and RTNeural.

**BUILD Target**: `@neural_audio//:neural_audio`

**Dependencies**:
- `@neural_amp_modeler_core//:nam_core` - Core model implementation
- `@rtneural//:rtneural` - Real-time neural network inference
- `@math_approx//:math_approx` - Math approximation functions
- `@nlohmann_json//:json` - JSON configuration parsing
- `@eigen//:eigen` - Matrix operations

**Build Configuration**:
```python
cc_library(
    name = "neural_audio",
    srcs = glob([
        "NeuralAudio/*.cpp",
        "NeuralAudioCAPI/*.cpp",
    ]),
    includes = [".", "NeuralAudio", "NeuralAudioCAPI"],
    defines = [
        "BUILD_NAMCORE",
        "NAM_SAMPLE_FLOAT",
        "DSP_SAMPLE_FLOAT",
    ],
)
```

**Key Concerns**:
- Defines control preprocessor macros that affect header behavior
- C API wrapper requires careful header exposure

---

### 3. `neural_amp_modeler_core` - Core Neural Amp Model

**Purpose**: Core shared library containing the actual neural model implementation.

**BUILD Target**: `@neural_amp_modeler_core//:nam_core`

**Dependencies**:
- `@eigen//:eigen` - Matrix math
- `@nlohmann_json//:json` - Configuration

**Build Configuration**:
```python
cc_library(
    name = "nam_core",
    srcs = glob(["NAM/**/*.cpp"]),
    includes = [".", "Dependencies/nlohmann"],
    defines = ["NAMCORE_EXPORTS"],
)
```

**Key Concerns**:
- `Dependencies/nlohmann` path expects submodule-style include structure
- Exports symbols with `NAMCORE_EXPORTS` define

---

### 4. `rtneural` - Real-Time Neural Network

**Purpose**: Lightweight neural network inference engine optimized for audio.

**BUILD Target**: `@rtneural//:rtneural`

**Dependencies**:
- `@xsimd//:xsimd` - SIMD operations
- `@eigen//:eigen` - Matrix operations
- `:bundled_modules` - Local bundled headers

**Build Configuration**:
```python
cc_library(
    name = "rtneural",
    srcs = ["RTNeural/RTNeural.cpp"],
    includes = ["."],
    defines = ["RTNEURAL_NAMESPACE=RTNeural"],
    deps = [
        "@xsimd//:xsimd",
        "@eigen//:eigen",
        ":bundled_modules",
    ],
)
```

**Key Concerns**:
- **CRITICAL**: Bundled Eigen in `modules/Eigen/` must be exposed correctly
- RTNeuralModel.h uses `#include <Eigen/Dense>` which needs to resolve
- The `modules/json` bundled json.hpp differs from nlohmann_json

---

### 5. `math_approx` - Math Approximation

**Purpose**: DSP math approximation functions (Chowdhury-DSP).

**BUILD Target**: `@math_approx//:math_approx`

**Dependencies**: None (header-only)

**Build Configuration**:
```python
cc_library(
    name = "math_approx",
    hdrs = glob(["include/**/*.hpp"]),
    includes = ["include"],  # Usage: #include <math_approx/...>
)
```

---

### 6. `xsimd` - C++ SIMD Library

**Purpose**: SIMD operations for vectorized computation.

**BUILD Target**: `@xsimd//:xsimd`

**Dependencies**: None (header-only)

**Build Configuration**:
```python
cc_library(
    name = "xsimd",
    hdrs = glob(["include/xsimd/**/*.hpp"]),
    includes = ["include"],  # Usage: #include <xsimd/... or xsimd/...
)
```

---

### 7. `eigen` - Linear Algebra

**Purpose**: Matrix and linear algebra operations.

**BUILD Target**: `@eigen//:eigen`

**Source**: Bazel Central Registry (version 5.0.1)

**Dependencies**: None (header-only)

**Build Configuration**:
```python
cc_library(
    name = "eigen",
    hdrs = glob(["Eigen/**/*.h"]),
    includes = ["."],  # Usage: #include <Eigen/Dense>
)
```

**Key Concerns**:
- Must be used over bundled Eigen from RTNeural submodule
- RTNeural's bundled_modules may conflict if not properly isolated

---

### 8. `nlohmann_json` - JSON Library

**Purpose**: Modern C++ JSON serialization.

**BUILD Target**: `@nlohmann_json//:json`

**Dependencies**: None (header-only)

**Build Configuration**:
```python
cc_library(
    name = "json",
    hdrs = ["single_include/nlohmann/json.hpp"],
    includes = ["single_include/nlohmann"],  # Usage: #include <json.hpp>
)
```

---

### 9. `lv2_headers` - LV2 API

**Purpose**: LV2 plugin API headers.

**BUILD Target**: `@lv2_headers//:lv2`

**Dependencies**: None (headers only)

**Build Configuration**:
```python
cc_library(
    name = "lv2",
    hdrs = glob(["include/lv2/**/*.h"]),
    includes = ["include"],  # Usage: #include <lv2/lv2plug.in/ns/ext/...
)
```

---

### 10. `jalv` - LV2 Host

**Purpose**: LV2 plugin host that loads and runs neural_amp_modeler.lv2. Exposes plugin ports as JACK ports.

**BUILD Target**: `@jalv//:jalv` (executable)

**Source**: git: v1.8.0 - https://github.com/drobilla/jalv

**Dependencies** (all Bazel-native):
- `@lv2_headers//:lv2` - LV2 API headers (archive)
- `@lilv//:lilv` - LV2 host library (Bazel git_repository)
- `@suil//:suil` - LV2 UI library (Bazel git_repository)
- `@zix//:zix` - Utility library (Bazel git_repository)
- `@sratom//:sratom` - LV2 Atom serialization (Bazel git_repository)
- `@serd//:serd` - RDF library (Bazel git_repository)
- `@sord//:sord` - RDF store (Bazel git_repository)
- `libjack` - System library (link against `-ljack`)

**Build Configuration**:
```python
cc_binary(
    name = "jalv",
    srcs = glob(["src/**/*.c"]),
    includes = ["src", "include"],
    deps = [
        "@lv2_headers//:lv2",
        "@lilv//:lilv",
        "@suil//:suil",
        "@zix//:zix",
        "@sratom//:sratom",
        "@serd//:serd",
        "@sord//:sord",
    ],
    linkopts = ["-lm", "-ljack"],
    defines = ["JALV_CONFIG_USE_JACK", "JALV_CONFIG_USE_SUIL"],
)
```

**Key Concerns**:
- Requires system libjack at runtime for audio
- All LV2 ecosystem dependencies are now Bazel-native (no system libs needed except jack)
- The executable produces `bazel-bin/jalv` which can run NAM LV2 plugin

---

### 11. `zix` - Utility Library

**Purpose**: C utility library used by LV2 ecosystem.

**BUILD Target**: `@zix//:zix`

**Source**: git: v0.5.2 - https://gitlab.com/drobilla/zix

**Build Configuration**:
```python
cc_library(
    name = "zix",
    srcs = glob(["src/**/*.c"]),
    hdrs = glob(["include/zix/**/*.h"]),
    includes = ["include"],
    defines = ["ZIX_STATIC"],
)
```

---

### 12. `serd` - RDF Library

**Purpose**: C library for RDF syntax serialization.

**BUILD Target**: `@serd//:serd`

**Source**: git: v0.32.2 - https://gitlab.com/drobilla/serd

**Build Configuration**:
```python
cc_library(
    name = "serd",
    srcs = glob(["src/**/*.c"]),
    hdrs = glob(["include/serd/**/*.h"]),
    includes = ["include", "src"],
    defines = ["SERD_STATIC"],
)
```

---

### 13. `sord` - RDF Store

**Purpose**: C library for RDF data storage.

**BUILD Target**: `@sord//:sord`

**Source**: git: v0.16.14 - https://gitlab.com/drobilla/sord

**Build Configuration**:
```python
cc_library(
    name = "sord",
    srcs = glob(["src/**/*.c"]),
    hdrs = glob(["include/sord/**/*.h"]),
    includes = ["include", "src"],
    defines = ["SORD_STATIC"],
    deps = ["@serd//:serd"],
)
```

---

### 14. `sratom` - Atom Serialization

**Purpose**: LV2 Atom serialization library.

**BUILD Target**: `@sratom//:sratom`

**Source**: git: v0.6.14 - https://gitlab.com/drobilla/sratom

**Build Configuration**:
```python
cc_library(
    name = "sratom",
    srcs = glob(["src/**/*.c"]),
    hdrs = glob(["include/sratom/**/*.h"]),
    includes = ["include"],
    defines = ["SRATOM_STATIC"],
    deps = [
        "@sord//:sord",
        "@serd//:serd",
        "@lv2_headers//:lv2",
    ],
)
```

---

### 15. `lilv` - LV2 Host Library

**Purpose**: LV2 plugin host library for discovery and instantiation.

**BUILD Target**: `@lilv//:lilv`

**Source**: git: v0.24.20 - https://gitlab.com/drobilla/lilv

**Build Configuration**:
```python
cc_library(
    name = "lilv",
    srcs = glob(["src/**/*.c"]),
    hdrs = glob(["include/lilv/**/*.h"]),
    includes = ["include", "src"],
    defines = ["LILV_STATIC"],
    deps = [
        "@sratom//:sratom",
        "@sord//:sord",
        "@serd//:serd",
        "@zix//:zix",
        "@lv2_headers//:lv2",
    ],
)
```

---

### 16. `suil` - LV2 UI Library

**Purpose**: LV2 UI embedding library.

**BUILD Target**: `@suil//:suil`

**Source**: git: v0.10.22 - https://gitlab.com/drobilla/suil

**Build Configuration**:
```python
cc_library(
    name = "suil",
    srcs = glob(["src/**/*.c"]),
    hdrs = glob(["include/suil/**/*.h"]),
    includes = ["include", "src"],
    defines = ["SUIL_STATIC"],
    deps = [
        "@lilv//:lilv",
        "@lv2_headers//:lv2",
        "@zix//:zix",
    ],
)
```

---

## Build Order and Parallelization

The optimal build order respects dependency ordering. Packages at the same indentation level can build in parallel.

```
Level 0 (no deps):
  - lv2_headers
  - math_approx
  - xsimd
  - eigen (Bazel Central Registry)
  - nlohmann_json
  - zix (no deps)
  - serd (no deps)

Level 1 (depends on Level 0):
  - neural_amp_modeler_core ──► eigen, nlohmann_json
  - rtneural ──► xsimd, eigen (+ bundled_modules)
  - sord ──► serd
  - sratom ──► sord, serd, lv2_headers

Level 2 (depends on Level 1):
  - neural_audio ──► neural_amp_modeler_core, rtneural, math_approx, nlohmann_json, eigen
  - lilv ──► sratom, sord, serd, zix, lv2_headers
  - suil ──► lilv, lv2_headers, zix

Level 3 (final):
  - nam_lv2 ──► neural_audio, lv2_headers, denormal
  - jalv ──► lv2_headers, lilv, suil, zix, sratom, serd, sord

Runtime:
  - Requires system libjack for jalv executable
  - jalv loads neural_amp_modeler.lv2 at runtime
```

---

## Include Path Resolution Map

| Package | Include Path | Resolved To |
|---------|-------------|-------------|
| `neural_amp_modeler_core` | `Eigen/Dense` | `@eigen//:eigen` -> `./Eigen/Dense` |
| `neural_amp_modeler_core` | `nlohmann/json.hpp` | `@nlohmann_json//:json` -> `single_include/nlohmann/json.hpp` |
| `rtneural` | `Eigen/Dense` | `@eigen//:eigen` (BCR version takes precedence) |
| `rtneural` | `RTNeural/...` | Local headers via `includes = ["."]` |
| `rtneural :bundled_modules` | `modules/Eigen/...` | Bundled Eigen from RTNeural commit |
| `rtneural :bundled_modules` | `modules/json/json.hpp` | Bundled single-header json |
| `neural_audio` | `NeuralAudio/...` | Local headers |
| `neural_audio` | `json.hpp` | `@nlohmann_json//:json` |

---

## Known Issues and Solutions

### Issue 1: RTNeural Bundled Eigen vs BCR Eigen

**Problem**: RTNeural bundles Eigen in `modules/Eigen/` but the build should use the Bazel Central Registry version.

**Solution**: 
1. The `:bundled_modules` library exposes the bundled headers for compilation
2. Include path order ensures BCR Eigen takes precedence
3. RTNeural should find `#include <Eigen/Dense>` via `@eigen//:eigen`

**Status**: FIXED - The `rtneural.BUILD` file has been updated to define `:bundled_modules` as a separate cc_library containing the bundled Eigen and json headers. RTNeural now depends on `:bundled_modules` alongside `@eigen//:eigen`.

### Issue 2: Include Path Conflicts

**Problem**: RTNeural's `modules/json/json.hpp` differs from nlohmann_json.

**Solution**: Use nlohmann_json v3.12.0 consistently across all packages. The bundled version in RTNeural should not be used.

### Issue 3: neural_amp_modeler_core Submodule Dependencies

**Problem**: The original repo has `Dependencies/nlohmann` as a submodule path.

**Solution**: The BUILD file's `includes = ["Dependencies/nlohmann"]` is currently set but should use `@nlohmann_json//:json` instead. Consider updating the include paths or the source to use the external dependency.

---

## Migration Checklist

- [ ] Verify Eigen includes resolve to BCR version, not bundled
- [ ] Test RTNeural builds with bundled_modules but links against @eigen
- [ ] Validate neural_amp_modeler_core uses @nlohmann_json correctly
- [ ] Confirm lv2_headers path resolution for LV2_URI_MAP, LV2_SYMBOL_MAP, etc.
- [ ] Run full build: `docker buildx bake -f local.docker-bake.hcl nam-bazel`
- [ ] Validate jalv can discover and load neural_amp_modeler.lv2 at runtime

---

## Jalv LV2 Host

**Purpose**: LV2 plugin host that loads and runs the neural_amp_modeler.lv2 plugin. Jalv exposes plugin ports as JACK ports for audio I/O.

**BUILD Target**: `@jalv//:jalv` (executable)

**Source**: git: v1.8.0 - https://github.com/drobilla/jalv

**Dependencies** (all Bazel-native except jack):
- `@lv2_headers//:lv2` - LV2 API headers
- `@lilv//:lilv` - LV2 host library (Bazel)
- `@suil//:suil` - LV2 UI library (Bazel)
- `@zix//:zix` - Utility library (Bazel)
- `@sratom//:sratom` - Atom serialization (Bazel)
- `@serd//:serd` - RDF library (Bazel)
- `@sord//:sord` - RDF store (Bazel)
- `libjack` - System library (link with `-ljack`)

**Build Configuration**:
```python
cc_binary(
    name = "jalv",
    srcs = glob(["src/**/*.c"]),
    includes = ["src", "include"],
    deps = [
        "@lv2_headers//:lv2",
        "@lilv//:lilv",
        "@suil//:suil",
        "@zix//:zix",
        "@sratom//:sratom",
        "@serd//:serd",
        "@sord//:sord",
    ],
    linkopts = ["-lm", "-ljack"],
    defines = ["JALV_CONFIG_USE_JACK", "JALV_CONFIG_USE_SUIL"],
)
```

**Runtime Configuration**:
```dockerfile
# Jalv runtime - only JACK is required as system package
RUN apt-get update && apt-get install -y \
    jackd2 \
    libjack-jackd2-0

ENV LV2_PATH=/usr/local/lib/lv2
```

**Usage**:
```bash
# Run NAM LV2 plugin via Jalv
./bazel-bin/jalv --plugin "http://github.com/mikeoliphant/neural-amp-modeler-lv2" --sample-rate 48000
```

**Key Concerns**:
- Requires JACK server running with matching sample rate (48kHz recommended for NAM models)
- `LV2_PATH` must include the directory containing `neural_amp_modeler.lv2` bundle
- IPC namespace sharing required when running in separate container from JACK

---

## Alternative: CMake Approach

If Bazel build complexity exceeds project needs:

```dockerfile
# From services/nam-bazel/Dockerfile alternative
RUN git clone -j$(nproc) --recurse-submodules --branch v0.1.9 \
    https://github.com/mikeoliphant/neural-amp-modeler-lv2

RUN cd neural-amp-modeler-lv2 && \
    cmake -B build -S . -DCMAKE_BUILD_TYPE=Release && \
    cmake --build build --parallel
```

The CMake approach handles submodules automatically with `--recurse-submodules` flag.