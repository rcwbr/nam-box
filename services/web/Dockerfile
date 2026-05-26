FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json astro.config.mjs tailwind.config.js ./
RUN npm install

COPY src ./src

RUN --mount=type=cache,target=node_modules/.astro \
    npm run build

FROM nginx:1.30.0-alpine

RUN apk add --no-cache openssl

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html/web

EXPOSE 80 443
