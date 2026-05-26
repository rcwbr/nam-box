load("@rules_cc//cc:defs.bzl", "cc_library")

package(default_visibility = ["//visibility:public"])

cc_library(
    name = "neural_audio",
    srcs = glob([
        "NeuralAudio/*.cpp",
        "NeuralAudioCAPI/*.cpp",
    ]),
    hdrs = glob([
        "NeuralAudio/*.h",
        "NeuralAudioCAPI/*.h",
    ]),
    includes = [
        ".",
        "NeuralAudio",
        "NeuralAudioCAPI",
    ],
    deps = [
        "@neural_amp_modeler_core//:nam_core",
        "@rtneural//:rtneural",
        "@math_approx//:math_approx",
        "@nlohmann_json//:json",
        "@eigen//:eigen",
    ],
    defines = [
        "BUILD_NAMCORE",
        "NAM_SAMPLE_FLOAT",
        "DSP_SAMPLE_FLOAT",
    ],
    linkopts = [
        "-lm",
    ],
)