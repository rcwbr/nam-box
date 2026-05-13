# Redefining vs. overriding targets due to override value clearing bug in buildx 0.19.1 (vs. 0.22.0)

group "default" {
  targets = [
    "bluetooth-host",
    "jack",
    "mod-host",
    "mod-ui",
    "webplayer"
  ]
}

target "common" {
  output = ["type=docker"]
}

target "bluetooth-host" {
  inherits   = ["common"]
  context    = "services/bluetooth-host"
  dockerfile = "Dockerfile"
  tags       = ["ghcr.io/rcwbr/nam-box-bluetooth-host:local"]
}

target "jack" {
  inherits = ["common"]
  context  = "services/jack"
  tags     = ["ghcr.io/rcwbr/nam-box-jack:local"]
}

target "mod-host" {
  inherits   = ["common"]
  context    = "services/mod-host"
  dockerfile = "Dockerfile"
  contexts = {
    github-mod-host = "https://github.com/rcwbr/mod-host.git#2025-12-10"
  }
  tags = ["ghcr.io/rcwbr/nam-box-mod-host:local"]
}

target "mod-ui" {
  inherits   = ["common"]
  context    = "services/mod-ui"
  dockerfile = "Dockerfile"
  contexts = {
    github-mod-ui = "https://github.com/rcwbr/mod-ui.git#2025-12-10"
  }
  tags = ["ghcr.io/rcwbr/nam-box-mod-ui:local"]
}

target "webplayer" {
  inherits   = ["common"]
  context    = "services/webplayer"
  dockerfile = "Dockerfile"
  tags       = ["ghcr.io/rcwbr/nam-box-webplayer:local"]
}
