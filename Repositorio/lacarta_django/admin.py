from django.contrib import admin

from .models import ItemPedido, Pedido, Plato, Restaurante, Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido_paterno', 'email', 'rol', 'sub', 'eliminado')
    list_filter = ('rol', 'eliminado')
    search_fields = ('nombre', 'apellido_paterno', 'email', 'nit', 'sub')


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


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    fields = ('plato', 'cantidad', 'precio_unitario')
    # R3: nobody edits prices by hand.
    readonly_fields = ('precio_unitario',)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'usuario', 'restaurante', 'estado', 'fecha', 'total', 'eliminado',
    )
    list_filter = ('estado', 'restaurante', 'eliminado')
    # R3: search by client (name, email or Auth0 sub), not only by id.
    search_fields = (
        'id',
        'usuario__nombre',
        'usuario__apellido_paterno',
        'usuario__email',
        'usuario__sub',
    )
    # R3: total is computed by the server / Flask, never typed in the admin.
    readonly_fields = ('total', 'fecha')
    date_hierarchy = 'fecha'
    inlines = (ItemPedidoInline,)


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'plato', 'cantidad', 'precio_unitario')
    search_fields = ('pedido__id', 'plato__nombre')
    readonly_fields = ('precio_unitario',)
