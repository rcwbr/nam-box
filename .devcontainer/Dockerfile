# hadolint ignore=DL3006
FROM base_context

# hadolint ignore=SC2034
RUN DEBIAN_FRONTEND=noninteractive \
  && apt-get update \
  && apt-get install --allow-unauthenticated --no-install-recommends -y \
    mender-artifact=3.9.0* \
  && apt-get clean \
  && apt-get autoclean \
  && apt-get autoremove \
  && rm -rf /var/cache/debconf \
  && rm -rf /var/lib/apt/lists/*
