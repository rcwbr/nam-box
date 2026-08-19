# docker buildx build --build-arg USER=$USER --build-arg USER_UID=$UID -t happy -f happy.Dockerfile . --load

FROM node:24.19.0

RUN npm install -g happy @anthropic-ai/claude-code

USER node
