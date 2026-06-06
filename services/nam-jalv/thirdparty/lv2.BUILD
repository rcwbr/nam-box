load("@rules_cc//cc:defs.bzl", "cc_library")

package(default_visibility = ["//visibility:public"])

cc_library(
    name = "lv2",
    hdrs = glob([
        "include/lv2/**/*.h",
    ]),
    includes = ["include"],
    linkopts = ["-lm"],
)