load("@rules_cc//cc:defs.bzl", "cc_binary", "cc_library")

package(default_visibility = ["//visibility:public"])

cc_library(
    name = "denormal",
    hdrs = ["deps/denormal/architecture.hpp"],
    includes = ["deps/denormal"],
)

cc_binary(
    name = "neural_amp_modeler",
    srcs = glob([
        "src/*.cpp",
        "src/*.h",
    ]),
    deps = [
        "@neural_audio//:neural_audio",
        "@lv2_headers//:lv2",
        ":denormal",
    ],
    includes = [
        "src",
    ],
    linkshared = True,
    visibility = ["//visibility:public"],
)