variable "VERSION" {
  default = "local"
}

variable "REGISTRY_PUSH" {
  default = "false"
}

target "common" {
  args = {
    BUILDKIT_MULTI_PLATFORM = 1
  }
  platforms = [
    "linux/arm64/v8"
  ]
}

target "bluetooth-host" {
  inherits   = ["common"]
  context    = "services/bluetooth-host"
  dockerfile = "Dockerfile"
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box/bluetooth-host:local"
  ]
  output = concat([
    "type=oci,dest=bluetooth-host.tar",
    ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,name=ghcr.io/rcwbr/nam-box/bluetooth-host:${VERSION}"
  ] : [])
  cache-from = [
    "type=registry,ref=ghcr.io/rcwbr/nam-box/bluetooth-host-cache:${VERSION}",
    "type=local,src=/var/buildx-cache/arm/bluetooth-host"
  ]
  cache-to = concat([
    "type=local,rewrite-timestamp=true,mode=max,dest=/var/buildx-cache/arm/bluetooth-host"
    ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,rewrite-timestamp=true,mode=max,ref=ghcr.io/rcwbr/nam-box/bluetooth-host-cache:${VERSION}"
  ] : [])
}

target "bluetooth-manager" {
  inherits   = ["common"]
  context    = "services/bluetooth-manager"
  dockerfile = "Dockerfile"
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box/bluetooth-manager:local"
  ]
  output = concat([
    "type=oci,dest=bluetooth-manager.tar",
    ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,name=ghcr.io/rcwbr/nam-box/bluetooth-manager:${VERSION}"
  ] : [])
  cache-from = [
    "type=registry,ref=ghcr.io/rcwbr/nam-box/bluetooth-manager-cache:${VERSION}",
    "type=local,src=/var/buildx-cache/arm/bluetooth-manager"
  ]
  cache-to = concat([
    "type=local,rewrite-timestamp=true,mode=max,dest=/var/buildx-cache/arm/bluetooth-manager"
    ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,rewrite-timestamp=true,mode=max,ref=ghcr.io/rcwbr/nam-box/bluetooth-manager-cache:${VERSION}"
  ] : [])
}

target "effects" {
  inherits = ["common"]
  context  = "services/effects"
  contexts = {
    github-mod-host = "https://github.com/rcwbr/mod-host.git#2025-12-10"
    github-mod-ui   = "https://github.com/rcwbr/mod-ui.git#2025-12-10"
  }
  dockerfile = "Dockerfile"
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box/effects:local"
  ]
  output = concat([
    "type=oci,dest=effects.tar",
    ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,name=ghcr.io/rcwbr/nam-box/effects:${VERSION}"
  ] : [])
  cache-from = [
    "type=registry,ref=ghcr.io/rcwbr/nam-box/effects-cache:${VERSION}",
    "type=local,src=/var/buildx-cache/arm/effects"
  ]
  cache-to = concat([
    "type=local,rewrite-timestamp=true,mode=max,dest=/var/buildx-cache/arm/effects"
    ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,rewrite-timestamp=true,mode=max,ref=ghcr.io/rcwbr/nam-box/effects-cache:${VERSION}"
  ] : [])
}

target "files" {
  inherits   = ["common"]
  context    = "services/files"
  dockerfile = "Dockerfile"
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box/files:local"
  ]
  output = concat([
    "type=oci,dest=files.tar"
    ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,name=ghcr.io/rcwbr/nam-box/files:${VERSION}"
  ] : [])
  cache-from = [
    "type=registry,ref=ghcr.io/rcwbr/nam-box/files-cache:${VERSION}",
    "type=local,src=/var/buildx-cache/arm/files"
  ]
  cache-to = concat([
    "type=local,rewrite-timestamp=true,mode=max,dest=/var/buildx-cache/arm/files"
    ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,rewrite-timestamp=true,mode=max,ref=ghcr.io/rcwbr/nam-box/files-cache:${VERSION}"
  ] : [])
}

target "proxy" {
  inherits   = ["common"]
  context    = "services/proxy"
  dockerfile = "Dockerfile"
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box/proxy:local"
  ]
  output = concat([
    "type=oci,dest=proxy.tar"
    ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,name=ghcr.io/rcwbr/nam-box/proxy:${VERSION}"
  ] : [])
  cache-from = [
    "type=registry,ref=ghcr.io/rcwbr/nam-box/proxy-cache:${VERSION}",
    "type=local,src=/var/buildx-cache/arm/proxy"
  ]
  cache-to = concat([
    "type=local,rewrite-timestamp=true,mode=max,dest=/var/buildx-cache/arm/proxy"
    ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,rewrite-timestamp=true,mode=max,ref=ghcr.io/rcwbr/nam-box/proxy-cache:${VERSION}"
  ] : [])
}

target "web" {
  inherits   = ["common"]
  context    = "services/web"
  dockerfile = "Dockerfile"
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box/web:local"
  ]
  output = concat([
    "type=oci,dest=web.tar"
    ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,name=ghcr.io/rcwbr/nam-box/web:${VERSION}"
  ] : [])
  cache-from = [
    "type=registry,ref=ghcr.io/rcwbr/nam-box/web-cache:${VERSION}",
    "type=local,src=/var/buildx-cache/arm/web"
  ]
  cache-to = concat([
    "type=local,rewrite-timestamp=true,mode=max,dest=/var/buildx-cache/arm/web"
    ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,rewrite-timestamp=true,mode=max,ref=ghcr.io/rcwbr/nam-box/web-cache:${VERSION}"
  ] : [])
}
