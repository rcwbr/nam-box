# Redefining vs. overriding targets due to override value clearing bug in buildx 0.19.1 (vs. 0.22.0)

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

target "effects" {
  inherits = ["common"]
  context  = "services/effects"
  contexts = {
    github-mod-host = "https://github.com/rcwbr/mod-host.git#2025-12-10"
    github-mod-ui   = "https://github.com/rcwbr/mod-ui.git#2025-12-10"
  }
  dockerfile = "Dockerfile"
  tags       = ["ghcr.io/rcwbr/nam-box/effects:local"]
  cache-from = [
    "type=local,src=/var/buildx-cache/effects"
  ]
  cache-to = [
    "type=local,dest=/var/buildx-cache/effects,mode=max"
  ]
}

target "files" {
  inherits   = ["common"]
  context    = "services/files"
  dockerfile = "Dockerfile"
  tags       = ["ghcr.io/rcwbr/nam-box/files:local"]
  cache-from = [
    "type=local,src=/var/buildx-cache/files"
  ]
  cache-to = [
    "type=local,dest=/var/buildx-cache/files,mode=max"
  ]
}

target "proxy" {
  inherits   = ["common"]
  context    = "services/proxy"
  dockerfile = "Dockerfile"
  tags       = ["ghcr.io/rcwbr/nam-box/proxy:local"]
  cache-from = [
    "type=local,src=/var/buildx-cache/proxy"
  ]
  cache-to = [
    "type=local,dest=/var/buildx-cache/proxy,mode=max"
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
