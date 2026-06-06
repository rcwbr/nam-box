load("@rules_cc//cc:defs.bzl", "cc_library")

package(default_visibility = ["//visibility:public"])

# libsndfile - audio file I/O
cc_library(
    name = "sndfile",
    srcs = glob([
        "src/*.c",
    ]),
    hdrs = glob([
        "include/*.h",
    ]),
    includes = ["include"],
    copts = [
        "-Wno-unused-parameter",
        "-Wno-sign-compare",
    ],
    linkopts = [
        "-lm",
        "-lFLAC",
    ],
)