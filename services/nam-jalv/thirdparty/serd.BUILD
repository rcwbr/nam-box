load("@rules_cc//cc:defs.bzl", "cc_library")

package(default_visibility = ["//visibility:public"])

# serd - RDF library for LV2
# https://github.com/drobilla/serd
# Internal headers in src/, public in include/serd/
# Source files include headers from src/ directory

filegroup(
    name = "serd_internal_hdrs",
    srcs = glob([
        "src/*.h",
    ]),
)

cc_library(
    name = "serd",
    srcs = glob([
        "src/**/*.c",
    ]),
    hdrs = glob([
        "include/serd/**/*.h",
    ]) + [":serd_internal_hdrs"],
    includes = ["include", "src"],
    defines = ["SERD_STATIC"],
)