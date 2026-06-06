# Bazel Build Setup Progress - DRAFT

## Summary
Attempts to build NAM LV2 with Bazel 9.x have encountered fundamental blockers around git submodule handling. Progress has been made on explicit submodule declaration, but complex nested dependency chains remain challenging.

## Current Files Created
- `MODULE.bazel` - Repository rules for all dependencies
- `thirdparty/nam_lv2.BUILD` - BUILD file for NAM LV2
- `thirdparty/neural_audio.BUILD` - BUILD file for NeuralAudio
- `thirdparty/nam_core.BUILD` - BUILD file for NeuralAmpModelerCore
- `thirdparty/rtneural.BUILD` - BUILD file for RTNeural
- `thirdparty/nlohmann_json.BUILD` - BUILD file for nlohmann/json
- `thirdparty/lv2.BUILD` - BUILD file for LV2 headers
- `thirdparty/math_approx.BUILD` - BUILD file for math_approx
- `thirdparty/xsimd.BUILD` - BUILD file for xsimd
- `thirdparty/jack.BUILD` - BUILD file for JACK headers (stub headers)
- `thirdparty/BUILD.bazel` - Package marker

## Current State
- MODULE.bazel has all required dependencies declared (lv2_headers, nam_lv2, neural_audio, neural_amp_modeler_core, rtneural, math_approx, nlohmann_json, xsimd, eigen)
- All top-level submodules declared as separate git_repository rules
- xsimd.BUILD created for xsimd SIMD library
- math_approx.BUILD created for math_approx library

## Build Progress
Build attempts show compilation is progressing but encountering include path issues:
1. ✅ Fixed `architecture.hpp` not found (denormal folder in NAM LV2 repo)
2. ✅ Fixed `json.hpp` not found (updated nlohmann_json.BUILD include paths)
3. ⚠️ Current error: `'Eigen' has not been declared` in RTNeuralModel.h

## Dependency Resolution Status
```
neural-amp-modeler-lv2 (main repo)  → @nam_lv2
  - deps/denormal/architecture.hpp  → included via nam_lv2.BUILD
  - deps/NeuralAudio (submodule)  → @neural_audio
    - deps/NeuralAmpModelerCore (submodule)  → @neural_amp_modeler_core
      - Dependencies/eigen (submodule)  → @eigen from BCR
      - Dependencies/nlohmann (submodule)  → @nlohmann_json
    - deps/RTNeural (submodule)  → @rtneural
      - modules/Eigen (BUNDLED in RTNeural commit)  → needs include path
      - modules/json (BUNDLED in RTNeural commit)  → included via nlohmann_json
      - modules/xsimd (EMPTY without --recurse-submodules)  → @xsimd separate
    - deps/math_approx (submodule)  → @math_approx
  - deps/lv2 (submodule)  → @lv2_headers
```

## Issues Fixed So Far
- MODULE.bazel Syntax (Bazel 9+ compatibility)
- BUILD File Compatibility (cc_binary/cc_library rules)
- LV2 Archive Format (.tar.xz)
- Package Markers

## Current Blocker
**RTNeural bundled Eigen not exposed to NeuralAudio**

RTNeural at commit 5909c44909cd6100367f62cd04b348de85d57dbf includes bundled Eigen in `modules/Eigen/` but:
1. The include path `modules/Eigen` expects headers at `modules/Eigen/Eigen/`
2. NeuralAudio's RTNeuralModel.h needs `#include <Eigen/Dense>` for `Eigen::MatrixXf`
3. The RTNeural BUILD file has `includes = [".", "modules/Eigen", "modules/json"]` but the files aren't being found

## Next Steps

1. Verify RTNeural BUILD file correctly exposes bundled Eigen headers
2. Ensure NeuralAudio include paths can reach RTNeural's bundled modules/Eigen
3. Continue debugging: `docker buildx bake --allow=fs=/var/buildx-cache/nam-bazel -f local.docker-bake.hcl nam-bazel`

### Alternative: Switch to CMake
Given the complexity of nested submodules and include paths, consider switching to the proven CMake approach used in `services/nam/Dockerfile`:
```dockerfile
git clone -j$(nproc) --recurse-submodules --branch v0.1.9 https://github.com/mikeoliphant/neural-amp-modeler-lv2
```
## JACK Audio Connection Kit Target

Added `jack.BUILD` to provide JACK headers for client compilation as a native Bazel target.

### Status: Header-only Target with Stub Headers (Complete)
Building JACK from source in Bazel is resolved via header-only target:
1. ✅ Stub `varargs.h` → redirects to `stdarg.h` for legacy compatibility
2. ✅ Stub `shm.h` → provides minimal shared memory interface
3. ⚠️ Optional features (libdb, libffado, aften) disabled via `HAVE_*` macros
4. ✅ `config.h` generated via genrule with platform feature detection

### Implementation Details
- `jack` library provides headers from `common/jack/*.h`
- Stub headers (`varargs.h`, `shm.h`) generated via genrules
- `config.h` genrule defines platform features and disables optional dependencies
- Uses system `libjack` for linking (`-ljack` via system libraries)

### Usage
```python
# In dependent BUILD files:
deps = [
    "@jack//:jack",
]
```

### Build Notes
- System JACK library (`libjack-jackd2-dev`) still required for final linking
- Header-only target allows NAM LV2 to compile against JACK API without Bazel-building JACK itself
- Optional features (DB, CELT, OPUS, SAMPLERATE, SNDFILE) disabled in config.h
