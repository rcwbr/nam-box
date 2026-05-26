FROM nginx:1.30.0-alpine

# Install openssl for certificate generation
RUN apk add --no-cache openssl

COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN mkdir -p /usr/share/nginx/html/webpages
COPY pages /usr/share/nginx/html/webpages

EXPOSE 80 443
