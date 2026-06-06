load("@rules_cc//cc:defs.bzl", "cc_library")

package(default_visibility = ["//visibility:public"])

# ALSA configuration header
genrule(
    name = "config_h",
    outs = ["config.h"],
    cmd = "cat > $@ <<'HEREDOC'\n/* ALSA config header */\n#ifndef ALSA_CONFIG_H\n#define ALSA_CONFIG_H\n#define HAVE_UNISTD_H 1\n#define HAVE_STDIO_H 1\n#define HAVE_STDLIB_H 1\n#define HAVE_STRING_H 1\n#define HAVE_INTTYPES_H 1\n#define HAVE_BYTESWAP_H 1\n#define HAVE_ENDIAN_H 1\n#define HAVE_DLFCN_H 1\n#define HAVE_LIBDL 1\n#endif\nHEREDOC",
)

# ALSA asoundlib.h public header (combines head and tail)
genrule(
    name = "asoundlib_h",
    srcs = [
        "include/asoundlib-head.h",
        "include/asoundlib-tail.h",
    ],
    outs = ["asoundlib.h"],
    cmd = "cat $(SRCS) > $@",
)

# ALSA library - audio library for Linux
cc_library(
    name = "alsa",
    srcs = glob([
        "src/*.c",
        "src/control/*.c",
        "src/hwdep/*.c",
        "src/mixer/*.c",
        "src/pcm/*.c",
        "src/rawmidi/*.c",
        "src/seq/*.c",
        "src/timer/*.c",
    ]),
    hdrs = [
        ":config_h",
        ":asoundlib_h",
    ],
    includes = [
        ".",
        "include",
        "src",
    ],
    linkopts = ["-lm", "-ldl"],
)

# Create a tree of alsa/sound headers that the broken include paths expect
# This is a separate target that creates the alsa/ symlink structure
genrule(
    name = "alsa_headers",
    srcs = [
        "include/sound/type_compat.h",
        "include/sound/uapi/asound.h",
    ],
    outs = ["asound.h"],
    cmd = """
        # Create include/alsa/sound directory structure
        mkdir -p $(@D)/include/alsa/sound && \
        cp include/sound/type_compat.h $(@D)/include/alsa/sound/type_compat.h && \
        cp include/sound/uapi/asound.h $(@D)/include/alsa/sound/asound.h
    """,
)