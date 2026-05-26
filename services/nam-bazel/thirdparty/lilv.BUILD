load("@rules_cc//cc:defs.bzl", "cc_library")

package(default_visibility = ["//visibility:public"])

# lilv - LV2 host library
# https://github.com/drobilla/lilv
# Internal headers in src/, public in include/lilv/

cc_library(
    name = "lilv",
    srcs = glob([
        "src/**/*.c",
    ]),
    hdrs = glob([
        "include/lilv/**/*.h",
        "src/*.h",
    ]),
    includes = [".", "include", "src"],
    defines = ["LILV_STATIC"],
    deps = [
        "@sratom//:sratom",
        "@sord//:sord",
        "@serd//:serd",
        "@zix//:zix",
        "@lv2_headers//:lv2",
    ],
)