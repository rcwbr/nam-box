load("@rules_cc//cc:defs.bzl", "cc_binary")

package(default_visibility = ["//visibility:public"])

#
# Jalv LV2 Host (statically linked)
# Built without SUIL to avoid dynamic module loading issues
# Uses JACK for audio backend via the system-installed libjack-dev
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
    ],
    linkstatic = True,
)

# Jalv source files for reference
filegroup(
    name = "jalv_srcs",
    srcs = glob([
        "src/**/*.c",
        "src/**/*.h",
    ]),
)
