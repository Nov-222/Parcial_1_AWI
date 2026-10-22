#!/bin/sh
# Genera un certificado autofirmado SOLO para desarrollo local.
# En EC2 usa Let's Encrypt y reemplaza nginx/certs/lacarta.crt y .key.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
CERT_DIR="${1:-$REPO_ROOT/nginx/certs}"

if ! command -v openssl >/dev/null 2>&1; then
    echo "Error: openssl no está instalado." >&2
    exit 1
fi

mkdir -p "$CERT_DIR"

openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout "$CERT_DIR/lacarta.key" \
    -out "$CERT_DIR/lacarta.crt" \
    -subj "/CN=carta.serverd.com" \
    -addext "subjectAltName=DNS:carta.serverd.com,DNS:carta.serverf.com,DNS:admin.serverd.com,DNS:localhost,IP:127.0.0.1"

chmod 600 "$CERT_DIR/lacarta.key" 2>/dev/null || true

echo "Certificado local generado en:"
echo "  $CERT_DIR/lacarta.crt"
echo "  $CERT_DIR/lacarta.key"
echo "Recuerda: el navegador mostrará una advertencia porque es autofirmado."
