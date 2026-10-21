from django.contrib import admin
from .models import Restaurante, Plato, Usuario, Pedido, ItemPedido

@admin.register(Restaurante)
class RestauranteAdmin(admin.ModelAdmin):
    pass

@admin.register(Plato)
class PlatoAdmin(admin.ModelAdmin):
    pass

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    pass

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    pass

@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    pass