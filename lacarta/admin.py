from django.contrib import admin
from .models import Usuario, Restaurante, Plato, Pedido, ItemPedido


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido_paterno', 'email', 'rol', 'eliminado')
    list_filter = ('rol', 'eliminado')
    search_fields = ('nombre', 'apellido_paterno', 'email', 'nit')


@admin.register(Restaurante)
class RestauranteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'eliminado')
    list_filter = ('eliminado',)
    search_fields = ('nombre', 'direccion')


@admin.register(Plato)
class PlatoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'restaurante', 'precio', 'disponible', 'eliminado')
    list_filter = ('disponible', 'eliminado', 'restaurante')
    search_fields = ('nombre', 'descripcion')


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'restaurante', 'estado', 'fecha', 'total', 'eliminado')
    list_filter = ('estado', 'eliminado', 'restaurante')
    search_fields = ('id', 'estado')


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'plato', 'cantidad', 'precio_unitario')
    search_fields = ('pedido__id',)