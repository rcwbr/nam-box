FROM nginx:1.30.0-alpine

RUN apk add --no-cache openssl

COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY <<'EOF' /usr/local/bin/entrypoint
#!/bin/sh
set -e

SSL_DIR="/etc/nam-box/ssl"
CA_KEY="${SSL_DIR}/ca.key"
CA_CRT="${SSL_DIR}/ca.crt"
SRV_KEY="${SSL_DIR}/server.key"
SRV_CRT="${SSL_DIR}/server.crt"

mkdir -p "$SSL_DIR"

# Generate CA if it doesn't exist
if [ ! -f "$CA_KEY" ] || [ ! -f "$CA_CRT" ]; then
  cat > "${SSL_DIR}/ca.cnf" << 'CACONF'
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_ca
prompt = no

[req_distinguished_name]
CN = nam-box-local-ca

[v3_ca]
basicConstraints = critical,CA:TRUE
keyUsage = critical, digitalSignature, keyEncipherment, keyCertSign
CACONF
  openssl genrsa -out "$CA_KEY" 2048
  openssl req -x509 -new -nodes -key "$CA_KEY" \
    -config "${SSL_DIR}/ca.cnf" \
    -out "$CA_CRT"
  rm -f "${SSL_DIR}/ca.cnf"
  chmod 644 "$CA_CRT"
  echo "CA certificate generated"
fi

# Generate server cert if needed
if [ ! -f "$SRV_KEY" ] || [ ! -f "$SRV_CRT" ]; then
  cat > "${SSL_DIR}/server.cnf" << SERVERCONF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = ${CN}

[v3_req]
basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = DNS:${CN},DNS:localhost,IP:127.0.0.1
SERVERCONF
  openssl genrsa -out "$SRV_KEY" 2048
  openssl req -new -key "$SRV_KEY" \
    -config "${SSL_DIR}/server.cnf" \
    -out "${SSL_DIR}/server.csr"
  openssl x509 -req -in "${SSL_DIR}/server.csr" -CA "$CA_CRT" -CAkey "$CA_KEY" \
    -CAcreateserial -out "$SRV_CRT" -days 365 -sha256 \
    -extfile "${SSL_DIR}/server.cnf" -extensions v3_req
  rm -f "${SSL_DIR}/server.csr" "${SSL_DIR}/ca.srl" "${SSL_DIR}/server.cnf"
  # Append CA certificate to server.crt for QUIC WebTransport certificate chain
  # msquic requires the full certificate chain in the file for proper TLS handshake
  cat "$CA_CRT" >> "$SRV_CRT"
  chmod 644 "$SRV_KEY" "$SRV_CRT"
  echo "Server certificate generated"
fi

# Start nginx after certs are ready
exec nginx -g 'daemon off;'
EOF

RUN chmod +x /usr/local/bin/entrypoint

EXPOSE 80 443

ENTRYPOINT ["entrypoint"]