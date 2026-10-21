import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
from api_flask.extensions import db

class Usuario(db.Model):
    __tablename__ = 'usuario'
    __table_args__ = {'schema': 'content'}

    id = db.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = db.Column('nombre', db.String(100), nullable=False)
    apellido_paterno = db.Column('apellido_paterno', db.String(100), nullable=False)
    apellido_materno = db.Column('apellido_materno', db.String(100), nullable=False)
    email = db.Column('email', db.String(255), nullable=False, unique=True)
    contrasena = db.Column('contrasena', db.String(255), nullable=False)
    rol = db.Column('rol', db.String(50), nullable=False, default='cliente')
    sub = db.Column('sub', db.String(255), unique=True)
    numero_telefono = db.Column('numero_telefono', db.String(20))
    nit = db.Column('nit', db.String(20), unique=True)
    eliminado = db.Column('eliminado', db.SmallInteger, nullable=False, default=0)

    def format(self):
        return {
            'id': str(self.id),
            'nombre': self.nombre,
            'apellido_paterno': self.apellido_paterno,
            'apellido_materno': self.apellido_materno,
            'email': self.email,
            'rol': self.rol,
            'sub': self.sub,
            'numero_telefono': self.numero_telefono,
            'nit': self.nit,
            'eliminado': self.eliminado
        }


class Restaurante(db.Model):
    __tablename__ = 'restaurante'
    __table_args__ = {'schema': 'content'}

    id = db.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = db.Column('nombre', db.String(150), nullable=False)
    descripcion = db.Column('descripcion', db.Text)
    direccion = db.Column('direccion', db.String(255))
    eliminado = db.Column('eliminado', db.SmallInteger, nullable=False, default=0)

    def format(self):
        return {
            'id': str(self.id),
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'direccion': self.direccion,
            'eliminado': self.eliminado
        }


class Plato(db.Model):
    __tablename__ = 'plato'
    __table_args__ = {'schema': 'content'}

    id = db.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurante_id = db.Column('restaurante_id', UUID(as_uuid=True), db.ForeignKey('content.restaurante.id'), nullable=False)
    nombre = db.Column('nombre', db.String(150), nullable=False)
    descripcion = db.Column('descripcion', db.Text)
    precio = db.Column('precio', db.Numeric(10, 2), nullable=False)
    disponible = db.Column('disponible', db.Boolean, nullable=False, default=True)
    eliminado = db.Column('eliminado', db.SmallInteger, nullable=False, default=0)

    def format(self):
        return {
            'id': str(self.id),
            'restaurante_id': str(self.restaurante_id),
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'precio': float(self.precio) if self.precio is not None else 0.0,
            'disponible': self.disponible,
            'eliminado': self.eliminado
        }


class Pedido(db.Model):
    __tablename__ = 'pedido'
    __table_args__ = {'schema': 'content'}

    id = db.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = db.Column('usuario_id', UUID(as_uuid=True), db.ForeignKey('content.usuario.id'), nullable=False)
    restaurante_id = db.Column('restaurante_id', UUID(as_uuid=True), db.ForeignKey('content.restaurante.id'), nullable=False)
    estado = db.Column('estado', db.String(50), nullable=False, default='pendiente')
    fecha = db.Column('fecha', db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    total = db.Column('total', db.Numeric(10, 2), nullable=False)
    eliminado = db.Column('eliminado', db.SmallInteger, nullable=False, default=0)

    def format(self):
        return {
            'id': str(self.id),
            'usuario_id': str(self.usuario_id),
            'restaurante_id': str(self.restaurante_id),
            'estado': self.estado,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'total': float(self.total) if self.total is not None else 0.0,
            'eliminado': self.eliminado
        }


class ItemPedido(db.Model):
    __tablename__ = 'item_pedido'
    __table_args__ = {'schema': 'content'}

    id = db.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pedido_id = db.Column('pedido_id', UUID(as_uuid=True), db.ForeignKey('content.pedido.id'), nullable=False)
    plato_id = db.Column('plato_id', UUID(as_uuid=True), db.ForeignKey('content.plato.id'), nullable=False)
    cantidad = db.Column('cantidad', db.Integer, nullable=False)
    precio_unitario = db.Column('precio_unitario', db.Numeric(10, 2), nullable=False)

    def format(self):
        return {
            'id': str(self.id),
            'pedido_id': str(self.pedido_id),
            'plato_id': str(self.plato_id),
            'cantidad': self.cantidad,
            'precio_unitario': float(self.precio_unitario) if self.precio_unitario is not None else 0.0
        }