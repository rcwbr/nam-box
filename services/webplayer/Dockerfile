FROM nginx:alpine

# Install openssl for certificate generation
RUN apk add --no-cache openssl

COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN mkdir -p /usr/share/nginx/html/webplayer
COPY index.html /usr/share/nginx/html/webplayer/

EXPOSE 80 443
