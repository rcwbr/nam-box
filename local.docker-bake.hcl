# Redefining vs. overriding targets due to override value clearing bug in buildx 0.19.1 (vs. 0.22.0)

group "default" {
  targets = [
    "bluetooth-mock",
    "bluetooth-manager",
    "certs",
    # "jack",
    # "mod-host",
    # "mod-ui",
    "webpages"
  ]
}

target "common" {
  output = ["type=docker"]
}

target "bluetooth-mock" {
  inherits   = ["common"]
  context    = "services/bluetooth-mock"
  dockerfile = "Dockerfile"
  tags       = ["ghcr.io/rcwbr/nam-box/bluetooth-mock:local"]
  cache-from = [
    "type=local,src=/var/buildx-cache/bluetooth-mock"
  ]
  cache-to = [
    "type=local,dest=/var/buildx-cache/bluetooth-mock,mode=max"
  ]
}

target "bluetooth-manager" {
  inherits   = ["common"]
  context    = "services/bluetooth-manager"
  dockerfile = "Dockerfile"
  tags       = ["ghcr.io/rcwbr/nam-box/bluetooth-manager:local"]
  cache-from = [
    "type=local,src=/var/buildx-cache/bluetooth-manager"
  ]
  cache-to = [
    "type=local,dest=/var/buildx-cache/bluetooth-manager,mode=max"
  ]
}

target "certs" {
  inherits   = ["common"]
  context    = "services/certs"
  dockerfile = "Dockerfile"
  tags       = ["ghcr.io/rcwbr/nam-box/certs:local"]
  cache-from = [
    "type=local,src=/var/buildx-cache/certs"
  ]
  cache-to = [
    "type=local,dest=/var/buildx-cache/certs,mode=max"
  ]
}

target "jack" {
  inherits = ["common"]
  context  = "services/jack"
  tags     = ["ghcr.io/rcwbr/nam-box/jack:local"]
  cache-from = [
    "type=local,src=/var/buildx-cache/jack"
  ]
  cache-to = [
    "type=local,dest=/var/buildx-cache/jack,mode=max"
  ]
}

target "jacktrip" {
  inherits = ["common"]
  context  = "jacktrip"
  tags     = ["ghcr.io/rcwbr/nam-box/jacktrip:local"]
  cache-from = [
    "type=local,src=/var/buildx-cache/jacktrip"
  ]
  cache-to = [
    "type=local,dest=/var/buildx-cache/jacktrip,mode=max"
  ]
}

target "jalv" {
  inherits = ["common"]
  context  = "services/jalv"
  tags     = ["ghcr.io/rcwbr/nam-box/jalv:local"]
  cache-from = [
    "type=local,src=/var/buildx-cache/jalv"
  ]
  cache-to = [
    "type=local,dest=/var/buildx-cache/jalv,mode=max"
  ]
}

target "mod-host" {
  inherits   = ["common"]
  context    = "services/mod-host"
  dockerfile = "Dockerfile"
  contexts = {
    github-mod-host = "https://github.com/rcwbr/mod-host.git#2025-12-10"
  }
  tags = ["ghcr.io/rcwbr/nam-box/mod-host:local"]
  cache-from = [
    "type=local,src=/var/buildx-cache/mod-host"
  ]
  cache-to = [
    "type=local,dest=/var/buildx-cache/mod-host,mode=max"
  ]
}

target "mod-ui" {
  inherits   = ["common"]
  context    = "services/mod-ui"
  dockerfile = "Dockerfile"
  contexts = {
    github-mod-ui = "https://github.com/rcwbr/mod-ui.git#2025-12-10"
  }
  tags = ["ghcr.io/rcwbr/nam-box/mod-ui:local"]
  cache-from = [
    "type=local,src=/var/buildx-cache/mod-ui"
  ]
  cache-to = [
    "type=local,dest=/var/buildx-cache/mod-ui,mode=max"
  ]
}

target "nam" {
  inherits   = ["common"]
  context    = "services/nam"
  dockerfile = "Dockerfile"
  tags       = ["ghcr.io/rcwbr/nam-box/nam:local"]
  cache-from = [
    "type=local,src=/var/buildx-cache/nam"
  ]
  cache-to = [
    "type=local,dest=/var/buildx-cache/nam,mode=max"
  ]
}

target "nam-bazel" {
  inherits   = ["common"]
  context    = "services/nam-bazel"
  dockerfile = "Dockerfile"
  tags       = ["ghcr.io/rcwbr/nam-box/nam-bazel:local"]
  cache-from = [
    "type=local,src=/var/buildx-cache/nam-bazel"
  ]
  cache-to = [
    "type=local,dest=/var/buildx-cache/nam-bazel,mode=max"
  ]
}


target "webpages" {
  inherits   = ["common"]
  context    = "services/webpages"
  dockerfile = "Dockerfile"
  tags       = ["ghcr.io/rcwbr/nam-box/webpages:local"]
  cache-from = [
    "type=local,src=/var/buildx-cache/webpages"
  ]
  cache-to = [
    "type=local,dest=/var/buildx-cache/webpages,mode=max"
  ]
}

target "web" {
  inherits   = ["common"]
  context    = "services/web"
  dockerfile = "Dockerfile"
  tags       = ["ghcr.io/rcwbr/nam-box/web:local"]
  cache-from = [
    "type=local,src=/var/buildx-cache/web"
  ]
  cache-to = [
    "type=local,dest=/var/buildx-cache/web,mode=max"
  ]
}
