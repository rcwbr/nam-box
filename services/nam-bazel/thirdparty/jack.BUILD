load("@rules_cc//cc:defs.bzl", "cc_library")

package(default_visibility = ["//visibility:public"])

# JACK configuration header - mimics waf-generated config.h
genrule(
    name = "config_h",
    outs = ["config.h"],
    cmd = "cat > $@ <<'HEREDOC'\n// Configuration header created by Bazel\n#ifndef _CONFIG_H_WAF\n#define _CONFIG_H_WAF\n\n#define JACK_MAJOR 1\n#define JACK_MINOR 9\n#define JACK_MICRO 23\n#define JACK_VERSION \"1.9.23\"\n\n#define HAVE_STDIO_H 1\n#define HAVE_STDLIB_H 1\n#define HAVE_STRING_H 1\n#define HAVE_SYS_TYPES_H 1\n#define HAVE_UNISTD_H 1\n#define HAVE_PTHREAD_H 1\n#define HAVE_SIGNAL_H 1\n#define HAVE_CLOCK_GETTIME 1\n#define HAVE_TIMER_CREATE 1\n\n#define HAVE_SYS_SOCKET_H 1\n#define HAVE_SYS_UN_H 1\n#define HAVE_ARPA_INET_H 1\n#define HAVE_NETINET_IN_H 1\n\n#define CLIENT_NUM 32\n#define PORT_NUM_FOR_CLIENT 24\n#define PORT_NUM 256\n#define PORT_NUM_MAX 512\n\n#undef HAVE_DB\n#undef HAVE_CELT\n#undef HAVE_OPUS\n#undef HAVE_SAMPLERATE\n#undef HAVE_SNDFILE\n\n#define JACK_ON_LINUX 1\n\n#endif\nHEREDOC",
)

# JACK public API headers
filegroup(
    name = "jack_headers",
    srcs = glob([
        "common/jack/*.h",
    ]),
)

# Internal headers that are part of the public API but not in jack/
filegroup(
    name = "jack_internal_headers",
    srcs = [
        "common/JackAtomic.h",
        "common/JackTypes.h",
        "common/JackPlatformPlug.h",
    ],
)

filegroup(
    name = "config_h_file",
    srcs = [":config_h"],
)

# JACK client library - minimal set of sources for JACK client compilation
cc_library(
    name = "jack",
    srcs = [
        # Core client sources from wscript common_libsources
        "common/JackActivationCount.cpp",
        "common/JackAPI.cpp",
        "common/JackArgParser.cpp",
        "common/JackAudioPort.cpp",
        "common/JackClient.cpp",
        "common/JackConnectionManager.cpp",
        "common/JackError.cpp",
        "common/JackException.cpp",
        "common/JackFrameTimer.cpp",
        "common/JackGraphManager.cpp",
        "common/JackPort.cpp",
        "common/JackPortType.cpp",
        "common/JackAudioPort.cpp",
        "common/JackMidiPort.cpp",
        "common/JackMidiAPI.cpp",
        "common/JackEngineControl.cpp",
        "common/JackShmMem.cpp",
        "common/JackGenericClientChannel.cpp",
        "common/JackGlobals.cpp",
        "common/JackTransportEngine.cpp",
        "common/JackTools.cpp",
        "common/JackMessageBuffer.cpp",
        "common/JackEngineProfiling.cpp",
        "common/ringbuffer.c",
        # Additional client sources
        "common/JackLibClient.cpp",
        "common/JackLibAPI.cpp",
        "common/JackMetadata.cpp",
        # POSIX/Linux platform sources (needed for client)
        "posix/JackFifo.cpp",
        "posix/JackPosixMutex.cpp",
        "posix/JackPosixProcessSync.cpp",
        "posix/JackPosixThread.cpp",
        "posix/JackSocket.cpp",
        "posix/JackPosixTime.c",
        "linux/JackLinuxFutex.cpp",
        "linux/JackLinuxTime.c",
        "posix/JackSocketClientChannel.cpp",
        "posix/JackPosixServerLaunch.cpp",
    ],
    hdrs = [
        ":jack_headers",
        ":jack_internal_headers",
        ":config_h_file",
    ],
    includes = [
        "common",
        "common/jack",
        "posix",
        "linux",
    ],
    defines = [
        "HAVE_CONFIG_H",
        "JACK_API_VERSION=0",
        "JACK_VERSION=\"1.9.23\"",
    ],
    linkopts = [
        "-lpthread",
        "-lrt",
        "-ldl",
        "-lm",
    ],
    linkstatic = True,
)