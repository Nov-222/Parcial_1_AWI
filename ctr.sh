#!/bin/bash

# Detener el script inmediatamente si ocurre algún error
set -e

echo "========================================================"
echo "    DESPLIEGUE FINAL CON SSL VÁLIDO (LET'S ENCRYPT)     "
echo "========================================================"

# 1. Verificar herramientas esenciales
if ! command -v docker &> /dev/null || ! command -v docker compose &> /dev/null; then
    echo "[ERROR] Docker y Docker Compose son requeridos en este servidor."
    exit 1
fi

# 2. Crear estructura de directorios base
mkdir -p nginx/certs staticfiles schema_design

# 3. Emisión de certificado SSL oficial y válido (Let's Encrypt)
DOMAIN_MAIN="djangodjangodjango.chickenkiller.com"
DOMAIN_SEC="flaskflaskflask.chickenkiller.com"
EMAIL="tu-correo-real@gmail.com"
CERT_DIR="nginx/certs"

echo "Verificando instalación de Certbot..."
if ! command -v certbot >/dev/null 2>&1; then
    echo "Certbot no está instalado. Instalando dependencias en el servidor..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -y
        sudo apt-get install -y certbot
    else
        echo "[ERROR] Sistema operativo no compatible con apt-get. Instala certbot manualmente." >&2
        exit 1
    fi
fi

echo "Solicitando certificado válido a Let's Encrypt para $DOMAIN_MAIN y $DOMAIN_SEC..."
# Nota: Asegúrate de que Nginx no esté ocupando los puertos 80/443 en el host al momento de correr esto.
sudo certbot certonly --standalone \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    -d "$DOMAIN_MAIN" \
    -d "$DOMAIN_SEC"

LE_PATH="/etc/letsencrypt/live/$DOMAIN_MAIN"

if [ -f "$LE_PATH/fullchain.pem" ] && [ -f "$LE_PATH/privkey.pem" ]; then
    echo "Certificado emitido con éxito por Let's Encrypt. Copiando a $CERT_DIR..."
    
    sudo cp -f "$LE_PATH/fullchain.pem" "$CERT_DIR/lacarta.crt"
    sudo cp -f "$LE_PATH/privkey.pem" "$CERT_DIR/lacarta.key"
    
    sudo chmod 644 "$CERT_DIR/lacarta.crt"
    sudo chmod 600 "$CERT_DIR/lacarta.key"

    echo "¡Certificados SSL VÁLIDOS configurados correctamente en la ruta de Nginx!"
else
    echo "[ERROR] Ocurrió un problema al obtener los certificados de Let's Encrypt." >&2
    exit 1
fi