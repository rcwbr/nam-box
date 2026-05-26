load("@rules_cc//cc:defs.bzl", "cc_library")

package(default_visibility = ["//visibility:public"])

# suil - LV2 UI library
# https://github.com/drobilla/suil
# Internal headers in src/, public in include/suil/
# Note: suil depends on lilv for UI type discovery

cc_library(
    name = "suil",
    srcs = glob(
        ["src/**/*.c"],
        exclude = [
            "src/*_in_gtk*.c",
            "src/*_in_qt*.cpp",
            "src/cocoa*.mm",
            "src/win*.cpp",
        ],
    ),
    hdrs = glob([
        "include/suil/**/*.h",
        "src/*.h",
    ]),
    includes = [".", "include", "src"],
    defines = ["SUIL_STATIC"],
    deps = [
        "@lilv//:lilv",
        "@lv2_headers//:lv2",
        "@zix//:zix",
    ],
)