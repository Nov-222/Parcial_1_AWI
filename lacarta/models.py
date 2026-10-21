import uuid
from django.db import models


class Usuario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=100)
    apellido_materno = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    contrasena = models.CharField(max_length=255)
    rol = models.CharField(max_length=50, default='cliente')
    sub = models.CharField(max_length=255, unique=True, null=True, blank=True)  # Auth0 ID
    numero_telefono = models.CharField(max_length=20, null=True, blank=True)
    nit = models.CharField(max_length=20, unique=True, null=True, blank=True)
    eliminado = models.SmallIntegerField(default=0)

    class Meta:
        db_table = 'content"."usuario'  # Mapeo explicito al esquema content
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.nombre} {self.apellido_paterno} ({self.email})"


class Restaurante(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(null=True, blank=True)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    eliminado = models.SmallIntegerField(default=0)

    class Meta:
        db_table = 'content"."restaurante'
        verbose_name = 'Restaurante'
        verbose_name_plural = 'Restaurantes'

    def __str__(self):
        return self.nombre


class Plato(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.CASCADE,
        related_name='platos',
        db_column='restaurante_id'
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(null=True, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    disponible = models.BooleanField(default=True)
    eliminado = models.SmallIntegerField(default=0)

    class Meta:
        db_table = 'content"."plato'
        verbose_name = 'Plato'
        verbose_name_plural = 'Platos'

    def __str__(self):
        return f"{self.nombre} - Bs. {self.precio}"


class Pedido(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('en_preparacion', 'En Preparación'),
        ('listo', 'Listo'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='pedidos',
        db_column='usuario_id'
    )
    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.RESTRICT,
        related_name='pedidos',
        db_column='restaurante_id'
    )
    estado = models.CharField(max_length=50, choices=ESTADOS, default='pendiente')
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    eliminado = models.SmallIntegerField(default=0)

    class Meta:
        db_table = 'content"."pedido'
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'

    def __str__(self):
        return f"Pedido {self.id} - {self.estado}"


class ItemPedido(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='items',
        db_column='pedido_id'
    )
    plato = models.ForeignKey(
        Plato,
        on_delete=models.RESTRICT,
        related_name='items_pedido',
        db_column='plato_id'
    )
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'content"."item_pedido'
        verbose_name = 'Ítem de Pedido'
        verbose_name_plural = 'Ítems de Pedido'

    def __str__(self):
        return f"{self.cantidad}x {self.plato.nombre} (Bs. {self.precio_unitario})"