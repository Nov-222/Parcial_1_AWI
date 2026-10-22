# Parcial 1 AWI — La Carta 2.0

Aplicación de pedidos de restaurantes construida con **Flask + Jinja2**, **Django Admin** y **PostgreSQL**, ejecutada detrás de **Nginx** y autenticada con **JWT local**.

> **Aclaración importante:** el proyecto **no utiliza Auth0 real** ni la librería Authlib. No hay tenant, no se llama a `/oauth/token` y no se valida un token firmado por Auth0. Se implementó un **JWT HS256 local** que imita el contrato de Auth0 (`sub`, `permissions`, `iss`, `exp`) para que la aplicación funcione sin depender de un servicio externo. La migración a Auth0 real queda documentada como trabajo pendiente.

---

## 1. Decisión de arquitectura

### ADR-001: monolito modular híbrido con una sola base de datos

**Estado:** aceptada.

**Contexto**

El enunciado exige dos responsabilidades que no encajan naturalmente en un solo framework:

- Flask debe exponer la API JSON y las páginas Jinja2 del flujo de pedidos.
- Django debe administrar el esquema, el `auth_user` y el panel de administración.
- Ambos deben trabajar sobre la misma base PostgreSQL y el despliegue existente debe seguir funcionando.

**Decisión**

Se adopta un **monolito modular híbrido**:

- **Django** es dueño del esquema y de las credenciales (`public.auth_user`).
- **Flask** implementa la API y la interfaz Jinja2, leyendo y escribiendo el mismo esquema mediante SQLAlchemy.
- **PostgreSQL** es la única fuente de verdad.
- **Nginx** es el único punto de entrada HTTP y enruta cada prefijo al servicio correspondiente.
- La autenticación se resuelve con un **JWT local HS256**, no con Auth0 real.

**Consecuencias**

- Una sola base de datos evita duplicar usuarios y mantiene consistentes los pedidos entre Flask y Django.
- Django puede autenticar a los mismos usuarios que crea Flask porque ambos usan el formato PBKDF2 de Django.
- El frontend y la API comparten el mismo origen, lo que simplifica cookies, CORS y despliegue.
- La arquitectura conserva la API y el despliegue anteriores, agregando las páginas Jinja y la autenticación.
- El costo es una mayor complejidad operativa: dos frameworks, dos procesos y un proxy inverso.

### Diagrama de componentes

```text
                         ┌──────────────────────────────┐
                         │          Navegador           │
                         │  HTML Jinja / fetch / admin  │
                         └──────────────┬───────────────┘
                                        │ HTTP :80
                         ┌──────────────▼───────────────┐
                         │            Nginx             │
                         │  único punto de entrada      │
                         └───┬───────┬───────┬───────┬──┘
                             │       │       │       │
             /, /auth,       │       │       │       │  /static/
             /pedidos,       │       │       │       │  (collectstatic)
             /cocina,        │       │       │       │
             /restaurantes,  │       │       │       │
             /assets, /api   │       │       │       │
                             ▼       │       ▼       ▼
                    ┌────────────────┐│┌──────────────┐
                    │ Flask/Gunicorn │││   Django     │
                    │ API + Jinja    │││ Admin + auth │
                    └───────┬────────┘│└──────┬───────┘
                            │         │       │
                            └─────────┴───────┘
                                      │
                         ┌────────────▼─────────────┐
                         │       PostgreSQL         │
                         │ public.auth_user         │
                         │ content.usuario          │
                         │ content.restaurante      │
                         │ content.plato            │
                         │ content.pedido           │
                         │ content.item_pedido      │
                         └──────────────────────────┘
```

---

## 2. Componentes y responsabilidades

| Componente | Responsabilidad | Justificación |
|---|---|---|
| **Nginx** | Único punto de entrada. Enruta `/api/`, `/auth`, `/pedidos`, `/cocina`, `/restaurantes` y `/assets` a Flask; `/admin/` a Django; `/static/` a los estáticos de Django. | Evita exponer dos orígenes distintos, simplifica cookies y mantiene una URL única. |
| **Flask + Gunicorn** | API JSON, páginas Jinja2, login/registro, reglas de negocio de pedidos y cola de cocina. | Es el framework exigido para la API y Jinja2. |
| **Django** | Esquema, migraciones, `auth_user`, superusuario y panel de administración. | Aprovecha el admin ya existente y mantiene credenciales compatibles con Django. |
| **PostgreSQL** | Única fuente de verdad para usuarios, perfiles, restaurantes, platos y pedidos. | Evita sincronización entre bases y permite transacciones atómicas. |
| **SQLAlchemy** | Acceso de Flask al esquema propiedad de Django. | Permite consultar y escribir sin duplicar modelos de Django. |
| **JWT local** | Identidad y permisos para API y páginas HTML. | Permite autenticar sin un proveedor externo y conserva un contrato compatible con Auth0. |

---

## 3. Autenticación: JWT local, no Auth0

### Qué se implementó

- Contraseñas en `public.auth_user.password` con formato **PBKDF2-SHA256** de Django, 600 000 iteraciones.
- Perfil de aplicación en `content.usuario`, con `rol` y `sub`.
- El `sub` se genera como `auth0|<id>` a partir de `auth_user.id`.
- El login emite un **JWT HS256** con:

```json
{
  "sub": "auth0|3",
  "username": "demo_cliente",
  "role": "cliente",
  "permissions": ["create:pedidos", "read:mis-pedidos"],
  "iat": 1792615480,
  "exp": 1792619080,
  "iss": "lacarta"
}
```

- El token se firma con `JWT_SECRET_KEY`, una clave distinta de `SECRET_KEY` y de al menos 32 bytes.
- La validación exige `exp`, `iat` y `sub`, usa una lista explícita de algoritmos (`HS256`) y verifica el emisor.

### Cómo viaja el token

| Canal | Uso | Justificación |
|---|---|---|
| `Authorization: Bearer <token>` | API JSON (`/api/...`) y pruebas con curl. | Es el contrato de la guía JWT y no depende de cookies. |
| Cookie de sesión firmada de Flask | Páginas Jinja2 (`/pedidos`, `/cocina`, etc.). | Un formulario HTML no puede agregar el header `Authorization`; la cookie guarda el mismo JWT, que igual se verifica criptográficamente en cada petición. |

La cookie se configura `HttpOnly` y `SameSite=Lax`. No se guarda la contraseña ni el rol como fuente de verdad: el rol y los permisos se leen del token, y el `sub` se contrasta con `content.usuario`.

### Permisos por rol

| Rol | Permisos |
|---|---|
| `cliente` | `create:pedidos`, `read:mis-pedidos` |
| `cocina` | `read:pedidos`, `update:pedidos` |
| `admin` | `read:pedidos`, `write:carta`, `delete:carta` |

Estos permisos coinciden con los seis permisos del enunciado. El decorador `requires_auth` acepta tanto `@requires_auth` como `@requires_auth("create:pedidos")` y devuelve `401` si falta el token o `403` si falta el permiso.

### Por qué no se usa Auth0 real

- No se dispone de un tenant ni de credenciales de Auth0 para el examen.
- El flujo debe funcionar sin conexión a un proveedor externo.
- El contrato se mantiene compatible: `sub` con formato `auth0|...`, permisos en el claim `permissions` y validación por firma.
- Para migrar a Auth0 real bastaría con sustituir la emisión/verificación local por el flujo de Auth0 y validar el token con JWKS/RS256; las rutas y las reglas de negocio no tendrían que cambiar.

**Limitaciones frente a Auth0 real:** no hay Universal Login, no hay refresh tokens, no hay revocación centralizada y no se valida un token RS256 con JWKS.

---

## 4. Decisiones justificadas

1. **Django es dueño del esquema y de `auth_user`.**
   Django crea las tablas de autenticación con `migrate auth`, conserva el panel de administración y aplica sus validadores. Flask nunca llama a `create_all()` en producción; solo lee y escribe el esquema existente. Esto evita dos fuentes de verdad para usuarios y contraseñas.

2. **Flask se encarga de la API y de Jinja2.**
   El enunciado pide la API y las páginas del flujo de pedidos en Flask. Mantenerlas en un solo servicio simplifica el renderizado, las sesiones y el despliegue con Gunicorn.

3. **Una sola base PostgreSQL.**
   Los pedidos creados desde Flask deben verse en el admin de Django y los usuarios creados en Flask deben poder autenticarse en Django. Compartir la base elimina sincronizaciones y permite transacciones atómicas para el pedido y sus ítems.

4. **JWT local en lugar de Auth0 real.**
   Permite cumplir el flujo de login sin tenant externo, manteniendo el mismo contrato de claims. Es una decisión explícita de alcance, no una implementación incompleta de Auth0.

5. **Mismo JWT para API y HTML.**
   La API lo recibe por header y las páginas lo guardan en la cookie de sesión. Así no existen dos sistemas de autenticación distintos: en ambos casos se valida la misma firma y los mismos permisos.

6. **Hash PBKDF2 compatible con Django.**
   `public.auth_user.password` tiene un límite de 128 caracteres. El hash PBKDF2 de Django cabe y permite que Django Admin autentique usuarios creados por Flask. Werkzeug/Flask usa por defecto scrypt, cuyo formato no encaja en ese esquema.

7. **El total y los precios se calculan en el servidor.**
   La ruta de creación ignora cualquier `precio`, `precio_unitario` o `total` enviado por el formulario. Toma el precio actual del plato, lo congela en `item_pedido.precio_unitario` y calcula el total con `Decimal`. Esto evita manipulación de precios desde el navegador.

8. **Reglas de pedido en el servidor, no en la plantilla.**
   Se valida que la cantidad sea un entero entre 1 y 20, que el plato exista, esté disponible y pertenezca al mismo restaurante. El pedido y sus ítems se guardan en una sola transacción: si algo falla, se hace `rollback` y no quedan filas parciales.

9. **Cambios de estado con actualización condicional.**
   La cocina solo puede avanzar `pendiente → en_preparacion → listo → entregado`. La actualización usa `UPDATE ... WHERE estado = estado_actual` para que dos personas haciendo clic a la vez no avancen el pedido dos veces. Un pedido `listo` no puede volver a `pendiente`.

10. **Pedido ajeno responde 404, no 403.**
    Si un cliente intenta abrir el pedido de otro, la respuesta es `404`. Así no se confirma la existencia de un recurso que no le pertenece. La cocina y el admin sí pueden leer todos los pedidos porque tienen `read:pedidos`.

11. **Nginx como único origen.**
    El navegador siempre habla con `http://localhost`; Nginx decide si la petición va a Flask, Django o a los estáticos. Esto evita CORS, permite compartir cookies y imita un despliegue real con un solo dominio.

12. **Separación de estáticos: `/static/` y `/assets/`.**
    `/static/` lo sirve Nginx desde `./staticfiles`, generado por `collectstatic` de Django (CSS del admin). `/assets/` lo sirve Flask para el CSS de las páginas Jinja. La separación evita que ambas aplicaciones compitan por el mismo prefijo.

13. **`collectstatic` en el arranque de Django.**
    El `entrypoint.sh` ejecuta `python manage.py collectstatic --noinput` y comparte `./staticfiles` con Nginx en modo lectura. Sin esto, el admin se ve sin estilos porque Django no sirve estáticos con `DEBUG=False`.

14. **Pruebas contra PostgreSQL real, no SQLite.**
    El esquema usa UUID, el schema `content` y tipos propios de PostgreSQL. Los tests crean una base separada `lacarta_test`, ejecutan `db.create_all()` solo ahí y la limpian al final. Así no se toca la base de desarrollo y no se falsean comportamientos por usar SQLite.

15. **Usuarios demo idempotentes.**
    El comando `seed-demo` crea o repara `demo_cliente`, `demo_cocina` y `demo_admin` al arrancar Django. La contraseña se lee de `DEMO_PASSWORD` en `.env`, nunca está escrita en el código. Esto hace que las credenciales sigan funcionando aunque se recree la base.

16. **Admin de Django con totales y precios de solo lectura.**
    `PedidoAdmin` muestra los ítems con `TabularInline`, permite buscar por cliente y filtra por estado/restaurante, pero no permite editar `total`, `fecha` ni `precio_unitario`. Los precios y totales son responsabilidad del servidor.

17. **Secretos fuera del repositorio.**
    `.env` contiene `SECRET_KEY`, `JWT_SECRET_KEY`, credenciales de PostgreSQL y `DEMO_PASSWORD`; está ignorado por Git. `.env.example` solo tiene placeholders. `.dockerignore` excluye secretos, cachés y estáticos generados.

18. **Finales de línea LF con `.gitattributes`.**
    El `entrypoint.sh` se ejecuta dentro de un contenedor Linux. Forzar LF evita errores como `$'\r': command not found` cuando Git hace checkout en Windows.

19. **Dependencias de prueba separadas.**
    `requirements.txt` contiene solo lo necesario para ejecutar la aplicación; `requirements-dev.txt` agrega pytest. La imagen Docker no instala herramientas de prueba innecesarias.

---

## 5. Flujo principal

### Login JSON

```text
POST /auth/login
{ "username": "...", "password": "..." }
        │
        ▼
authenticate() consulta public.auth_user
        │
        ▼
verifica PBKDF2 y busca content.usuario por sub
        │
        ▼
emite JWT HS256 con sub, rol y permisos
```

### Login HTML

```text
POST /auth/ingresar
        │
        ▼
mismo authenticate()
        │
        ▼
guarda el JWT en la cookie de sesión firmada
        │
        ▼
redirige a /pedidos, /cocina o / según el rol
```

### Crear un pedido

```text
POST /pedidos  (requiere create:pedidos)
        │
        ├─ valida restaurante, platos, cantidades y disponibilidad
        ├─ calcula el total en el servidor
        ├─ congela precio_unitario
        └─ guarda Pedido + ItemPedido en una transacción
```

### Avanzar un pedido en cocina

```text
POST /cocina/<id>/avanzar  (requiere update:pedidos)
        │
        ├─ calcula el siguiente estado permitido
        └─ UPDATE condicional por estado actual
```

---

## 6. Modelo de datos

| Tabla | Dueño | Uso |
|---|---|---|
| `public.auth_user` | Django | Credenciales, `username`, hash PBKDF2, flags de Django. |
| `content.usuario` | Django/Flask | Perfil, rol, `sub`, datos de contacto, borrado lógico. |
| `content.restaurante` | Django/Flask | Restaurantes y su información pública. |
| `content.plato` | Django/Flask | Platos, precio y disponibilidad. |
| `content.pedido` | Django/Flask | Cabecera del pedido, estado y total. |
| `content.item_pedido` | Django/Flask | Líneas del pedido con cantidad y precio congelado. |

Relaciones principales:

- `content.usuario.sub = 'auth0|' || public.auth_user.id`
- `content.pedido.usuario_id → content.usuario.id`
- `content.pedido.restaurante_id → content.restaurante.id`
- `content.item_pedido.pedido_id → content.pedido.id`
- `content.item_pedido.plato_id → content.plato.id`

Estados del pedido: `pendiente`, `en_preparacion`, `listo`, `entregado`, `cancelado`.

---

## 7. Estructura del proyecto

```text
api_flask/
  __init__.py          fábrica de Flask, CLI create-user / seed-demo
  config.py            configuración y JWT
  models.py            modelos SQLAlchemy del esquema existente
  routes.py            API JSON
  views.py             páginas Jinja y reglas de pedidos
  permissions.py       roles y permisos
  auth/
    service.py         registro, login, seed de usuarios demo
    passwords.py       PBKDF2 compatible con Django
    tokens.py          emisión y verificación del JWT
    decorators.py      requires_auth
    routes.py          /auth/login, /auth/ingresar, /auth/registro
    handlers.py        respuestas 401/403
  templates/           HTML Jinja
  static/              CSS de Flask (se sirve en /assets)

config/                configuración de Django
lacarta/               modelos y admin de Django
nginx/nginx.conf       enrutamiento del proxy inverso
schema_design/         esquema y datos iniciales de PostgreSQL
tests/                 pruebas pytest
entrypoint.sh          migraciones, seed, collectstatic y arranque Django
docker-compose.yml     db, django, flask y nginx
```

---

## 8. Cómo ejecutar

```
# 1. Instalar Docker
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker ubuntu
# cerrar sesión SSH y volver a entrar para que tome el grupo

# 2. Traer el proyecto
git clone "https://github.com/Nov-222/Parcial_1_AWI"
cd Parcial_1_AWI

# 3. Crear el archivo .env en el servidor (no viene del repositorio)
nano .env

# 4. Generar un certificado local autofirmado (solo desarrollo)
sh scripts/generate-local-cert.sh

# 5. Levantar
docker compose up -d --build
docker compose ps
```

En EC2, reemplaza `nginx/certs/lacarta.crt` y `nginx/certs/lacarta.key` por el
certificado de Let's Encrypt antes de levantar Nginx. Los certificados locales
no se suben al repositorio. El certificado local es autofirmado, así que el
navegador mostrará una advertencia hasta que uses uno de confianza.

Servicios:

| URL | Servicio |
|---|---|
| `https://localhost/` | Menú público (Flask/Jinja) |
| `https://localhost/auth/ingresar` | Login HTML |
| `https://localhost/auth/registro` | Registro HTML |
| `https://localhost/pedidos` | Pedidos del cliente |
| `https://localhost/cocina` | Cola de cocina |
| `https://localhost/api/...` | API JSON |
| `https://localhost/admin/` | Django Admin |
| `https://localhost/static/...` | Estáticos de Django |
| `https://localhost/assets/...` | Estáticos de Flask |

Los usuarios demo se crean al arrancar Django:

- `demo_cliente` → rol `cliente`
- `demo_cocina` → rol `cocina`
- `demo_admin` → rol `admin`

La contraseña es la definida en `DEMO_PASSWORD` dentro de `.env`. No se documenta en el repositorio.

### Pruebas

```powershell
.\venv\Scripts\pip install -r requirements-dev.txt
docker compose up -d db
.\venv\Scripts\python.exe -m pytest -q
```

Las pruebas usan la base `lacarta_test` en el mismo PostgreSQL. No tocan `lacarta`.

> No uses `docker compose down -v` si quieres conservar los datos: elimina el volumen de PostgreSQL. Usa `docker compose down` o `docker compose restart`.

---

## 9. Pruebas incluidas

Las seis pruebas obligatorias están en `tests/test_pedidos.py`:

1. Sin sesión, crear un pedido no crea nada y redirige al login.
2. Un cliente no puede avanzar el estado de un pedido (`403`).
3. El total y el precio unitario se calculan en el servidor, ignorando precios falsos del formulario.
4. Un plato no disponible rechaza el pedido completo, sin filas nuevas.
5. Un cliente que abre el pedido de otro recibe `404`, no `403`.
6. La cocina no puede devolver un pedido de `listo` a `pendiente`.

Resultado esperado:

```text
6 passed
```

---

## 10. Límites y trabajo pendiente

- **Auth0 real no está implementado.** Se usa un JWT local HS256 que imita el contrato; no hay tenant, JWKS, RS256, refresh tokens ni Universal Login.
- **R4 (Docker/Compose):** Django todavía arranca con `runserver`; PostgreSQL publica `5432` para que las pruebas locales puedan conectarse y no existe un servicio de migraciones separado.
- **R5 (HTTPS/subdominios):** Nginx escucha en 443 con un certificado local autofirmado y redirige HTTP a HTTPS. En EC2 falta reemplazarlo por un certificado de Let's Encrypt y abrir el puerto 443 en el Security Group.
- **Credenciales del superusuario:** `entrypoint.sh` crea `admin` con una contraseña por defecto. Antes de un despliegue real debería leerlas de variables de entorno.
- **Tests:** dependen de que PostgreSQL esté levantado y no se ejecutan todavía en un pipeline CI.
- **Cookies:** la cookie de sesión usa `HttpOnly` y `SameSite=Lax`; para producción con HTTPS debería añadirse `Secure`.
