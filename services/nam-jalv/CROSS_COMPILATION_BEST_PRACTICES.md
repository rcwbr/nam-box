# Bazel Cross-Compilation Best Practices

## Overview
Cross-compiling C/C++ with Bazel requires proper toolchain configuration. The key is using `--crosstool_top`, `--host_crosstool_top`, and `--cpu` flags together with a registered `cc_toolchain`.

## Method 1: Platform-Based Toolchain (Recommended)

### 1. Define a Platform
Create a platform target in `BUILD.bazel`:
```python
platform(
    name = "arm64_platform",
    constraint_values = [
        "@platforms//cpu:arm64",
        "@platforms//os:linux",
    ],
)
```

### 2. Create a Toolchain Configuration
Create a `toolchain.bzl` file that defines `cc_toolchain_config`:
```python
load("@bazel_tools//tools/cpp:cc_toolchain_config_lib.bzl", "cc_toolchain_config")

def _cc_toolchain_config_impl(ctx):
    return cc_toolchain_config(
        ctx = ctx,
        cpu = "arm64",
        compiler = "gcc",
        toolchain_identifier = "aarch64-linux-gnu",
        host_system_name = "linux",
        target_system_name = "linux",
        target_libc = "glibc",
        target_cpu = "arm64",
        target_os = "linux",
        # Specify tool paths
        tool_paths = [
            tool_path(name = "gcc", path = "/usr/bin/aarch64-linux-gnu-gcc"),
            tool_path(name = "g++", path = "/usr/bin/aarch64-linux-gnu-g++"),
            tool_path(name = "ar", path = "/usr/bin/aarch64-linux-gnu-ar"),
            tool_path(name = "ld", path = "/usr/bin/aarch64-linux-gnu-ld"),
        ],
    )

cc_toolchain_config_arm64 = rule(
    implementation = _cc_toolchain_config_impl,
    provides = [cc_toolchain_config],
)
```

### 3. Register the Toolchain in BUILD.bazel
```python
load("@rules_cc//cc:defs.bzl", "cc_toolchain", "cc_toolchain_suite")
load("//:toolchain.bzl", "cc_toolchain_config_arm64")

filegroup(name = "empty", srcs = [])

cc_toolchain(
    name = "cc-compiler-arm64",
    all_files = ":empty",
    compiler_files = ":empty",
    dwp_files = ":empty",
    linker_files = ":empty",
    objcopy_files = ":empty",
    strip_files = ":empty",
    toolchain_config = ":arm64_config",
)

cc_toolchain_suite(
    name = "cc_toolchain_suite",
    toolchains = {"arm64": ":cc-compiler-arm64"},
)
```

### 4. Register Toolchain in MODULE.bazel
```python
register_toolchains("//:cc_toolchain_suite")
```

### 5. Build Command
```bash
bazel build --platforms=//:arm64_platform //:target
```

## Method 2: Environment Variable Approach (Simpler but Limited)

For basic cross-compilation in Docker, setting environment variables can work:
```bash
CC=aarch64-linux-gnu-gcc \
CXX=aarch64-linux-gnu-g++ \
AR=aarch64-linux-gnu-ar \
LD=aarch64-linux-gnu-ld \
bazel build --cpu=arm64 //:target
```

**Limitations:** This approach may not work correctly with all Bazel versions because `--cpu` alone doesn't fully configure the toolchain for cross-linking.

## Method 3: Using --compiler Flag

The `--compiler` flag can specify the compiler to use:
```bash
bazel build --compiler=aarch64-linux-gnu-gcc --cpu=arm64 //:target
```

## Key Gotchas

1. **Linker must match compiler target:** The linker must be the cross-linker (`aarch64-linux-gnu-ld`), not the native `/usr/bin/ld`. Error: "unsupported ELF machine number 183" indicates using native x86_64 linker for ARM64 objects.

2. **Toolchain registration:** In Bazel 9.x with Bzlmod (MODULE.bazel), use `register_toolchains()` at the module level, not in WORKSPACE.

3. **Platform constraint values:** Use `@platforms//cpu:arm64` and `@platforms//os:linux` for standard constraint references.

4. **Static linking:** For embedded targets, use `linkstatic = True` in `cc_binary` to produce self-contained binaries.

5. **Docker Buildx multi-platform:** When using Buildx with `platforms = ["linux/arm64/v8"]`, the TARGETPLATFORM build arg can be parsed to determine target, but for cross-compilation from amd64, the builder must explicitly use the cross-compiler toolchain.

## References

### Official Bazel Documentation
- [C++ Toolchain Configuration](https://bazel.build/versions/main/docs/cc-toolchain-configurations)
- [Platforms](https://bazel.build/versions/main/docs/platforms)
- [Cross-compilation](https://bazel.build/versions/main/docs/cross-compilation)
- [Toolchain Definition](https://bazel.build/versions/main/docs/toolchains)

### Rules CC Documentation
- [rules_cc on GitHub](https://github.com/bazelbuild/rules_cc)
- [cc_toolchain rule reference](https://github.com/bazelbuild/rules_cc/blob/master/cc/defs.bzl)

### Examples and Tutorials
- [Bazel Cross-compilation Example](https://github.com/bazelbuild/bazel/blob/master/examples/cross-compilation/cc_toolchain_config.bzl)
- [Bazel Toolchain Configurations](https://github.com/bazelbuild/examples/tree/master/cpp-cross-compilation)

### Related Tools
- [Docker Buildx Multi-platform Builds](https://docs.docker.com/build/buildkit/BuildKit/#multi-platform-images)
- [QEMU User Mode Emulation](https://wiki.qemu.org/Documentation/UserDocumentation)

### Community Resources
- [Bazel Users Google Group](https://groups.google.com/g/bazel-discuss)
- [Stack Overflow: Bazel Cross-compilation](https://stackoverflow.com/questions/tagged/bazel+cross-compilation)
