variable "VERSION" {
  default = "local"
}

variable "REGISTRY_PUSH" {
  default = "false"
}

group "default" {
  targets = [
    "bluetooth-host",
    "mod-host",
    "mod-ui",
    "webpages"
  ]
}

group "audio" {
  targets = [
    "jack",
    "nam",
    "jalv"
  ]
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

target "certs" {
  inherits   = ["common"]
  context    = "services/certs"
  dockerfile = "Dockerfile"
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box/certs:local"
  ]
  output = concat([
    "type=oci,dest=certs.tar"
  ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,name=ghcr.io/rcwbr/nam-box/certs:${VERSION}"
  ] : [])
  cache-from = [
    "type=registry,ref=ghcr.io/rcwbr/nam-box/certs-cache:${VERSION}",
    "type=local,src=/var/buildx-cache/arm/certs"
  ]
  cache-to = concat([
    "type=local,rewrite-timestamp=true,mode=max,dest=/var/buildx-cache/arm/certs"
  ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,rewrite-timestamp=true,mode=max,ref=ghcr.io/rcwbr/nam-box/certs-cache:${VERSION}"
  ] : [])
}

target "jack" {
  inherits   = ["common"]
  context    = "services/jack"
  dockerfile = "Dockerfile"
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box/jack:local"
  ]
  output = concat([
    "type=oci,dest=jack.tar",
  ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,name=ghcr.io/rcwbr/nam-box/jack:${VERSION}"
  ] : [])
  cache-from = [
    "type=registry,ref=ghcr.io/rcwbr/nam-box/jack-cache:${VERSION}",
    "type=local,src=/var/buildx-cache/arm/jack"
  ]
  cache-to = concat([
    "type=local,rewrite-timestamp=true,mode=max,dest=/var/buildx-cache/arm/jack"
  ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,rewrite-timestamp=true,mode=max,ref=ghcr.io/rcwbr/nam-box/jack-cache:${VERSION}"
  ] : [])
}

target "mod-host" {
  inherits   = ["common"]
  context    = "services/mod-host"
  dockerfile = "Dockerfile"
  contexts = {
    github-mod-host = "https://github.com/rcwbr/mod-host.git#2025-12-10"
  }
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box/mod-host:local"
  ]
  output = concat([
    "type=oci,dest=mod-host.tar"
  ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,name=ghcr.io/rcwbr/nam-box/mod-host:${VERSION}"
  ] : [])
  cache-from = [
    "type=registry,ref=ghcr.io/rcwbr/nam-box/mod-host-cache:${VERSION}",
    "type=local,src=/var/buildx-cache/arm/mod-host"
  ]
  cache-to = concat([
    "type=local,rewrite-timestamp=true,mode=max,dest=/var/buildx-cache/arm/mod-host"
  ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,rewrite-timestamp=true,mode=max,ref=ghcr.io/rcwbr/nam-box/mod-host-cache:${VERSION}"
  ] : [])
}

target "mod-ui" {
  inherits   = ["common"]
  context    = "services/mod-ui"
  dockerfile = "Dockerfile"
  contexts = {
    github-mod-ui = "https://github.com/rcwbr/mod-ui.git#2025-12-10"
  }
  output = concat([
    "type=oci,dest=mod-ui.tar"
  ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,name=ghcr.io/rcwbr/nam-box/mod-ui:${VERSION}"
  ] : [])
  cache-from = [
    "type=registry,ref=ghcr.io/rcwbr/nam-box/mod-ui-cache:${VERSION}",
    "type=local,src=/var/buildx-cache/arm/mod-ui"
  ]
  cache-to = concat([
    "type=local,rewrite-timestamp=true,mode=max,dest=/var/buildx-cache/arm/mod-ui"
  ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,rewrite-timestamp=true,mode=max,ref=ghcr.io/rcwbr/nam-box/mod-ui-cache:${VERSION}"
  ] : [])
}

target "jalv" {
  inherits   = ["common"]
  context    = "services/jalv"
  dockerfile = "Dockerfile"
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box/jalv:local"
  ]
  output = concat([
    "type=oci,dest=jalv.tar",
  ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,name=ghcr.io/rcwbr/nam-box/jalv:${VERSION}"
  ] : [])
  cache-from = [
    "type=registry,ref=ghcr.io/rcwbr/nam-box/jalv-cache:${VERSION}",
    "type=local,src=/var/buildx-cache/arm/jalv"
  ]
  cache-to = concat([
    "type=local,rewrite-timestamp=true,mode=max,dest=/var/buildx-cache/arm/jalv"
  ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,rewrite-timestamp=true,mode=max,ref=ghcr.io/rcwbr/nam-box/jalv-cache:${VERSION}"
  ] : [])
}

target "nam" {
  inherits   = ["common"]
  context    = "services/nam"
  dockerfile = "Dockerfile"
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box/nam:local"
  ]
  output = concat([
    "type=oci,dest=nam.tar",
  ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,name=ghcr.io/rcwbr/nam-box/nam:${VERSION}"
  ] : [])
  cache-from = [
    "type=registry,ref=ghcr.io/rcwbr/nam-box/nam-cache:${VERSION}",
    "type=local,src=/var/buildx-cache/arm/nam"
  ]
  cache-to = concat([
    "type=local,rewrite-timestamp=true,mode=max,dest=/var/buildx-cache/arm/nam"
  ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,rewrite-timestamp=true,mode=max,ref=ghcr.io/rcwbr/nam-box/nam-cache:${VERSION}"
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

target "jacktrip" {
  inherits   = ["common"]
  # context    = "services/jacktrip"
  context    = "jacktrip"
  dockerfile = "Dockerfile"
  annotations = [
    "index-descriptor:io.containerd.image.name=ghcr.io/rcwbr/nam-box/jacktrip:local"
  ]
  output = concat([
    "type=oci,dest=jacktrip.tar"
  ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,name=ghcr.io/rcwbr/nam-box/jacktrip:${VERSION}"
  ] : [])
  cache-from = [
    "type=registry,ref=ghcr.io/rcwbr/nam-box/jacktrip-cache:${VERSION}",
    "type=local,src=/var/buildx-cache/arm/jacktrip"
  ]
  cache-to = concat([
    "type=local,rewrite-timestamp=true,mode=max,dest=/var/buildx-cache/arm/jacktrip"
  ], "${REGISTRY_PUSH}" == "true" ? [
    "type=registry,rewrite-timestamp=true,mode=max,ref=ghcr.io/rcwbr/nam-box/jacktrip-cache:${VERSION}"
  ] : [])
}
