load("@rules_cc//cc:defs.bzl", "cc_library")

package(default_visibility = ["//visibility:public"])

# sratom - LV2 Atom serialization
# https://github.com/drobilla/sratom

cc_library(
    name = "sratom",
    srcs = glob([
        "src/**/*.c",
    ]),
    hdrs = glob([
        "include/sratom/**/*.h",
    ]),
    includes = ["include"],
    defines = ["SRATOM_STATIC"],
    deps = [
        "@sord//:sord",
        "@serd//:serd",
        "@lv2_headers//:lv2",
    ],
)