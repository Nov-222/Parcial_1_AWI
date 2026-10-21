-- =============================================================================
-- SCRIPT DML: POBLAMIENTO MASIVO (10,000 REGISTROS POR TABLA) - LA CARTA 2.0
-- =============================================================================

begin;

-- 1. Insertar 10,000 usuarios (incluyendo clientes con sub de Auth0 y personal de cocina)
insert into content.usuario (id, nombre, apellido_paterno, apellido_materno, email, contrasena, rol, sub, numero_telefono, nit, eliminado)
select 
    uuid_generate_v4(),
    'nombre_' || g,
    'paterno_' || g,
    'materno_' || g,
    'usuario_' || g || '@lacarta.com',
    'hash_pass_' || g,
    case when g <= 8000 then 'cliente' else 'cocina' end,
    case when g <= 8000 then 'auth0|cliente_sub_' || g else null end,
    '7' || lpad(g::text, 7, '0'),
    (1000000 + g)::text,
    0
from generate_series(1, 10000) as g;

-- 2. Insertar 10,000 restaurantes (disponibles para consulta pública sin login)
insert into content.restaurante (id, nombre, descripcion, direccion, eliminado)
select 
    uuid_generate_v4(),
    'Restaurante Gourmet ' || g,
    'Descripción y especialidades del restaurante ' || g,
    'Av. Principal #' || g,
    0
from generate_series(1, 10000) as g;

-- 3. Insertar 10,000 platos (Relación 1-N distribuida equitativamente entre los restaurantes)
insert into content.plato (id, restaurante_id, nombre, descripcion, precio, disponible, eliminado)
select 
    uuid_generate_v4(),
    r.id,
    'Plato Delicioso ' || g,
    'Receta especial de la casa número ' || g,
    floor(random() * (150 - 20 + 1) + 20)::numeric(10,2), -- Precio aleatorio entre 20 y 150
    true,
    0
from generate_series(1, 10000) as g
cross join lateral (
    -- Asocia cada plato de forma cíclica a los restaurantes creados
    select id from content.restaurante offset ((g - 1) % 10000) limit 1
) r;

-- 4. Insertar 10,000 pedidos (asociados a clientes y restaurantes)
insert into content.pedido (id, usuario_id, restaurante_id, estado, fecha, total, eliminado)
select 
    uuid_generate_v4(),
    u.id,
    r.id,
    (array['pendiente', 'en_preparacion', 'listo', 'entregado', 'cancelado'])[floor(random() * 5 + 1)],
    current_timestamp - (random() * 365 || ' days')::interval, -- Distribuidos en el último año
    100.00, -- Valor base temporal, recalculado o asignado para el lote
    0
from generate_series(1, 10000) as g
cross join lateral (
    -- Selecciona un usuario con rol 'cliente'
    select id from content.usuario where rol = 'cliente' offset ((g - 1) % 8000) limit 1
) u
cross join lateral (
    select id from content.restaurante offset ((g - 1) % 10000) limit 1
) r;

-- 5. Insertar 10,000 ítems de pedido (con precio unitario congelado del plato)
insert into content.item_pedido (id, pedido_id, plato_id, cantidad, precio_unitario)
select 
    uuid_generate_v4(),
    p.id,
    pl.id,
    floor(random() * 5 + 1)::int, -- Cantidad aleatoria entre 1 y 5
    pl.precio                     -- Precio congelado obtenido directamente del plato
from generate_series(1, 10000) as g
cross join lateral (
    select id from content.pedido offset ((g - 1) % 10000) limit 1
) p
cross join lateral (
    select id, precio from content.plato offset ((g - 1) % 10000) limit 1
) pl;

commit;