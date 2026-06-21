# FROM node:20-alpine AS builder

# WORKDIR /app

# COPY package.json astro.config.mjs tailwind.config.js ./
# RUN npm install

# COPY src ./src

# RUN --mount=type=cache,target=node_modules/.astro \
#     npm run build

# FROM nginx:1.30.0-alpine AS final

# RUN apk add --no-cache openssl

# COPY nginx.conf /etc/nginx/conf.d/default.conf
# COPY --from=builder /app/dist /usr/share/nginx/html/web

# EXPOSE 80 443


FROM node:24-alpine AS builder-preact

WORKDIR /app

COPY preact/package.json ./
COPY preact/package-lock.json ./
RUN npm ci

COPY preact/astro.config.mjs preact/tsconfig.json ./

COPY preact/src ./src

RUN --mount=type=cache,target=node_modules/.astro \
    npm run build


FROM nginx:1.30.0-alpine

RUN apk add --no-cache openssl~=3.5.7

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder-preact /app/dist /usr/share/nginx/html/web

EXPOSE 80 443
