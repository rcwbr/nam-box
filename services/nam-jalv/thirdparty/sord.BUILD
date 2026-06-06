load("@rules_cc//cc:defs.bzl", "cc_library")

package(default_visibility = ["//visibility:public"])

# sord - RDF store for LV2
# https://github.com/drobilla/sord
# Internal headers in src/, public in include/sord/

cc_library(
    name = "sord",
    srcs = glob([
        "src/**/*.c",
    ]),
    hdrs = glob([
        "include/sord/**/*.h",
    ]) + [
        "src/sord_config.h",
        "src/sord_internal.h",
    ],
    includes = ["include", "src"],
    defines = ["SORD_STATIC"],
    deps = [
        "@serd//:serd",
        "@zix//:zix",
    ],
)