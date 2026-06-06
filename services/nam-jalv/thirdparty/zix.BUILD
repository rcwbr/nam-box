load("@rules_cc//cc:defs.bzl", "cc_library")

package(default_visibility = ["//visibility:public"])

# zix - Utility library from Drobilla
# https://github.com/drobilla/zix
# Sources are in src/, public headers in include/zix/
# Internal headers are included with relative paths
# Platform-specific files in src/win32/, src/darwin/ are excluded

cc_library(
    name = "zix",
    srcs = glob(
        ["src/**/*.c"],
        exclude = [
            "src/win32/**/*.c",
            "src/darwin/**/*.c",
        ],
    ),
    hdrs = glob([
        "include/zix/**/*.h",
        "src/**/*.h",
    ]),
    includes = ["include", "src"],
    defines = [
        "ZIX_STATIC",
        "_GNU_SOURCE",
    ],
)