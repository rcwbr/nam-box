FROM python:3.8.20

RUN apt-get update && apt-get install -y build-essential
# RUN apt-get install -y lv2-dev
RUN apt-get install -y libjack-jackd2-dev
RUN apt-get install -y liblilv-dev
# RUN apt-get install -y
# RUN apt-get install -y

RUN mkdir /opt/mod-ui
WORKDIR /opt/mod-ui
COPY --from=github-mod-ui . .
RUN pip install -r requirements.txt
RUN make -C utils

ENV MOD_DEV_HOST=1
ENTRYPOINT [ "/opt/mod-ui/server.py" ]
