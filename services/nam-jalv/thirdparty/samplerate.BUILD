load("@rules_cc//cc:defs.bzl", "cc_library")

package(default_visibility = ["//visibility:private"])

filegroup(
    name = "libsamplerate_headers",
    srcs = glob(
        [
            "include/**/*.h",
        ],
    ),
)

filegroup(
    name = "libsamplerate_srcs",
    srcs = glob(
        [
            "src/**/*.c",
            "src/**/*.h",
        ],
    ),
)

cc_library(
    name = "samplerate",
    hdrs = [
        ":libsamplerate_headers",
    ],
    srcs = [
        ":libsamplerate_srcs",
    ],
    includes = [
        "include",
    ],
    copts = [
        "-std=c99",
        "-Wno-unused-parameter",
        "-Wno-sign-compare",
    ],
    local_defines = [
        "PACKAGE=\\\"libsamplerate\\\"",
        "VERSION=\\\"0.2.2\\\"",
        "HAVE_STDBOOL_H=1",
    ],
    visibility = ["//visibility:public"],
)

