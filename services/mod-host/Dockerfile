FROM python:3.12.4

RUN apt-get update && apt-get install -y build-essential pkg-config
RUN apt-get install -y lv2-dev
RUN apt-get install -y libjack-jackd2-dev
RUN apt-get install -y liblilv-dev
# RUN apt-get install -y
# RUN apt-get install -y

WORKDIR /tmp/mod-host
RUN --mount=type=bind,from=github-mod-host,target=.,rw \
  make \
  && make install

ENTRYPOINT [ "mod-host" ]
CMD [ "" ]
LABEL io.containerd.image.name=ghcr.io/rcwbr/nam-box-mod-host:local
