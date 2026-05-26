load("@rules_cc//cc:defs.bzl", "cc_binary")

package(default_visibility = ["//visibility:public"])

#
# Jalv LV2 Host with JACK backend
# Uses JACK audio backend for audio I/O
#

cc_binary(
    name = "jalv",
    srcs = glob(
        ["src/**/*.c", "src/**/*.cpp", "src/**/*.h"],
        exclude = [
            "src/gtk/**/*.c",
            "src/gtk/**/*.h",
            "src/qt/**/*.cpp",
            "src/qt/**/*.hpp",
            "src/portaudio.c",
        ],
    ),
    deps = [
        "@lv2_headers//:lv2",
        "@lilv//:lilv",
        "@suil//:suil",
        "@zix//:zix",
        "@sratom//:sratom",
        "@serd//:serd",
        "@sord//:sord",
        "@jack//:jack",
    ],
    linkopts = [
        "-lm",
        "-lpthread",
        "-lrt",
        "-ldl",
        "-ljack",
    ],
    defines = [
        "JALV_CONFIG_USE_SUIL",
    ],
)

# Jalv source files for reference
filegroup(
    name = "jalv_srcs",
    srcs = glob([
        "src/**/*.c",
        "src/**/*.h",
    ]),
)