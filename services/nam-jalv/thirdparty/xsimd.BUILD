load("@rules_cc//cc:defs.bzl", "cc_library")

package(default_visibility = ["//visibility:public"])

cc_library(
    name = "xsimd",
    hdrs = glob([
        "include/xsimd/**/*.hpp",
    ]),
    includes = ["include"],
)