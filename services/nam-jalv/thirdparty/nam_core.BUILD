load("@rules_cc//cc:defs.bzl", "cc_library")

package(default_visibility = ["//visibility:public"])

cc_library(
    name = "nam_core",
    srcs = glob(["NAM/**/*.cpp"]),
    hdrs = glob([
        "NAM/**/*.h",
    ]),
    includes = [
        ".",
        "Dependencies/nlohmann",
    ],
    deps = [
        "@eigen//:eigen",
        "@nlohmann_json//:json",
    ],
    defines = [
        "NAMCORE_EXPORTS",
    ],
)