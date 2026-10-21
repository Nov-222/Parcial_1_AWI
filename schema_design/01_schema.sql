-- Habilitar extensión para UUIDs
create extension if not exists "uuid-ossp";

-- Creación del esquema dedicado
create schema if not exists content;

-- 1. Tabla usuario (integrada con tus campos originales y soporte para el sub de Auth0)
create table content.usuario (
    id uuid primary key default uuid_generate_v4(),
    nombre varchar(100) not null,
    apellido_paterno varchar(100) not null,
    apellido_materno varchar(100) not null,
    email varchar(255) not null unique,
    contrasena varchar(255) not null,
    rol varchar(50) default 'cliente' not null,
    sub varchar(255) unique, -- Mapeo directo con el identificador de Auth0 (ej: auth0|65f...)
    numero_telefono varchar(20),
    nit varchar(20) unique,
    eliminado smallint default 0 not null check (eliminado in (0, 1))
);

-- 2. Tabla restaurante (Para listar los restaurantes de forma pública sin login)
create table content.restaurante (
    id uuid primary key default uuid_generate_v4(),
    nombre varchar(150) not null,
    descripcion text,
    direccion varchar(255),
    eliminado smallint default 0 not null check (eliminado in (0, 1))
);

-- 3. Tabla plato (Relación 1-N: Un restaurante tiene muchos platos)
create table content.plato (
    id uuid primary key default uuid_generate_v4(),
    restaurante_id uuid not null,
    nombre varchar(150) not null,
    descripcion text,
    precio numeric(10, 2) not null check (precio >= 0),
    disponible boolean default true not null,
    eliminado smallint default 0 not null check (eliminado in (0, 1)),
    constraint fk_plato_restaurante foreign key (restaurante_id) 
        references content.restaurante(id) on delete cascade
);

-- 4. Tabla pedido (Asociada al usuario y al restaurante. Estados limitados por CHECK)
create table content.pedido (
    id uuid primary key default uuid_generate_v4(),
    usuario_id uuid not null,
    restaurante_id uuid not null,
    estado varchar(50) default 'pendiente' not null check (estado in ('pendiente', 'en_preparacion', 'listo', 'entregado', 'cancelado')),
    fecha timestamp with time zone default current_timestamp not null,
    total numeric(10, 2) not null check (total >= 0),
    eliminado smallint default 0 not null check (eliminado in (0, 1)),
    constraint fk_pedido_usuario foreign key (usuario_id) 
        references content.usuario(id) on delete cascade,
    constraint fk_pedido_restaurante foreign key (restaurante_id) 
        references content.restaurante(id) on delete restrict
);

-- 5. Tabla item_pedido (Precio congelado del plato y cantidad validada entre 1 y 20)
create table content.item_pedido (
    id uuid primary key default uuid_generate_v4(),
    pedido_id uuid not null,
    plato_id uuid not null,
    cantidad int not null check (cantidad between 1 and 20),
    precio_unitario numeric(10, 2) not null check (precio_unitario >= 0),
    constraint fk_item_pedido_pedido foreign key (pedido_id) 
        references content.pedido(id) on delete cascade,
    constraint fk_item_pedido_plato foreign key (plato_id) 
        references content.plato(id) on delete restrict
);

-- Índices recomendados para optimización de consultas
create index idx_usuario_email on content.usuario(email);
create index idx_usuario_sub on content.usuario(sub);
create index idx_plato_restaurante_id on content.plato(restaurante_id);
create index idx_pedido_usuario_id on content.pedido(usuario_id);
create index idx_pedido_restaurante_id on content.pedido(restaurante_id);
create index idx_pedido_estado on content.pedido(estado);
create index idx_item_pedido_pedido_id on content.item_pedido(pedido_id);
create index idx_item_pedido_plato_id on content.item_pedido(plato_id);