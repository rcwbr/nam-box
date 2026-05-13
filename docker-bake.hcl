group "default" {
  targets = [
    "bluetooth-host",
    "mod-host",
    "mod-ui",
    "webplayer"
  ]
}

target "common" {
  args = {
    BUILDKIT_MULTI_PLATFORM = 1
  }
  platforms = [
    # "linux/amd64",
    "linux/arm64/v8"
  ]
}

target "bluetooth-host" {
  inherits   = ["common"]
  context    = "services/bluetooth-host"
  dockerfile = "Dockerfile"
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box-bluetooth-host:local"
  ]
  output = [
    "type=oci,dest=nam-bluetooth.tar",
  ]
}

target "jack" {
  inherits   = ["common"]
  context    = "services/jack"
  dockerfile = "Dockerfile"
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box-jack:local"
  ]
  output = [
    "type=oci,dest=jack.tar",
  ]
}

target "mod-host" {
  inherits   = ["common"]
  context    = "services/mod-host"
  dockerfile = "Dockerfile"
  contexts = {
    github-mod-host = "https://github.com/rcwbr/mod-host.git#2025-12-10"
  }
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box-mod-host:local"
  ]
  output = [
    "type=oci,dest=mod-host.tar"
  ]
}

target "mod-ui" {
  inherits   = ["common"]
  context    = "services/mod-ui"
  dockerfile = "Dockerfile"
  contexts = {
    github-mod-ui = "https://github.com/rcwbr/mod-ui.git#2025-12-10"
  }
  output = [
    "type=oci,dest=mod-ui.tar"
  ]
}

target "webplayer" {
  inherits   = ["common"]
  context    = "services/webplayer"
  dockerfile = "Dockerfile"
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box-webplayer:local"
  ]
  output = [
    "type=oci,dest=webplayer.tar"
  ]
}
