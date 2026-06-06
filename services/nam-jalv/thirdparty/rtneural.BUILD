load("@rules_cc//cc:defs.bzl", "cc_library")

package(default_visibility = ["//visibility:public"])

# Bundled modules from RTNeural submodule (Eigen, json)
cc_library(
    name = "bundled_modules",
    hdrs = glob([
        "modules/Eigen/Eigen/**/*.h",
        "modules/Eigen/unsupported/**/*.h",
        "modules/json/json.hpp",
    ], allow_empty = True),
    includes = [
        "modules/Eigen",
        "modules/json",
    ],
)

cc_library(
    name = "rtneural",
    srcs = [
        "RTNeural/RTNeural.cpp",
    ],
    hdrs = glob([
        "RTNeural/**/*.h",
        "RTNeural/**/*.hpp",
        "RTNeural/**/*.tpp",
    ]),
    includes = [
        ".",
    ],
    deps = [
        "@xsimd//:xsimd",
        "@eigen//:eigen",
        ":bundled_modules",
    ],
    defines = [
        "RTNEURAL_NAMESPACE=RTNeural",
        "RTNEURAL_USE_EIGEN",
    ],
)