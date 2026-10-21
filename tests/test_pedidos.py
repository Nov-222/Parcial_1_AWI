"""The six mandatory tests from practico.pdf (R6).

Auth0 is not called: the `login` fixture writes a real signed JWT with the
permissions of the simulated user into the Flask session.
"""

import uuid
from decimal import Decimal

from api_flask.extensions import db
from api_flask.models import ItemPedido, Pedido, Usuario
from api_flask.permissions import (
    CREATE_PEDIDOS,
    READ_MIS_PEDIDOS,
    READ_PEDIDOS,
    UPDATE_PEDIDOS,
)

CLIENTE_PERMISSIONS = [CREATE_PEDIDOS, READ_MIS_PEDIDOS]
COCINA_PERMISSIONS = [READ_PEDIDOS, UPDATE_PEDIDOS]


# 1. Sin sesión, crear un pedido no crea nada y redirige al login (o 401).
def test_crear_pedido_sin_sesion_no_crea_nada(client, app, seed):
    response = client.post(
        "/pedidos",
        data={
            "restaurante_id": seed.restaurante_1,
            f"cantidad_{seed.plato_ok}": "1",
        },
    )

    assert response.status_code == 302
    assert "/auth/ingresar" in response.headers["Location"]
    with app.app_context():
        assert Pedido.query.count() == 0
        assert ItemPedido.query.count() == 0


# 2. Un cliente que intenta avanzar el estado recibe 403 y el estado no cambia.
def test_cliente_no_puede_avanzar_el_estado(client, app, seed, pedido_factory, login):
    pedido_id = pedido_factory(seed.cliente_2, estado="pendiente")
    login(seed.cliente_1, CLIENTE_PERMISSIONS, role="cliente")

    response = client.post(f"/cocina/{pedido_id}/avanzar")

    assert response.status_code == 403
    with app.app_context():
        pedido = db.session.get(Pedido, uuid.UUID(pedido_id))
        assert pedido.estado == "pendiente"


# 3. El total se calcula en el servidor: un precio inventado se ignora.
def test_total_lo_calcula_el_servidor_ignorando_precios_del_formulario(
    client, app, seed, login
):
    login(seed.cliente_1, CLIENTE_PERMISSIONS, role="cliente")

    response = client.post(
        "/pedidos",
        data={
            "restaurante_id": seed.restaurante_1,
            f"cantidad_{seed.plato_ok}": "2",
            # Forged fields: the route must never read them.
            "precio": "0.01",
            "precio_unitario": "0.01",
            "total": "0.01",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        profile = Usuario.query.filter_by(sub=seed.cliente_1).one()
        pedido = Pedido.query.filter_by(usuario_id=profile.id).one()
        item = ItemPedido.query.filter_by(pedido_id=pedido.id).one()
        assert pedido.total == Decimal("20.00")
        assert item.precio_unitario == Decimal("10.00")


# 4. Un plato no disponible rechaza el pedido completo (sin filas nuevas).
def test_plato_no_disponible_no_deja_pedido_ni_items(client, app, seed, login):
    login(seed.cliente_1, CLIENTE_PERMISSIONS, role="cliente")

    response = client.post(
        "/pedidos",
        data={
            "restaurante_id": seed.restaurante_1,
            f"cantidad_{seed.plato_agotado}": "1",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        assert Pedido.query.count() == 0
        assert ItemPedido.query.count() == 0


# 5. Un cliente que abre el pedido de otro cliente recibe 404, no 403.
def test_pedido_ajeno_responde_404(client, app, seed, pedido_factory, login):
    pedido_id = pedido_factory(seed.cliente_2, estado="pendiente")
    login(seed.cliente_1, CLIENTE_PERMISSIONS, role="cliente")

    response = client.get(f"/pedidos/{pedido_id}")

    assert response.status_code == 404
    with app.app_context():
        assert db.session.get(Pedido, uuid.UUID(pedido_id)) is not None


# 6. La cocina no puede devolver un pedido de listo a pendiente.
def test_cocina_no_puede_devolver_un_pedido_a_pendiente(
    client, app, seed, pedido_factory, login
):
    pedido_id = pedido_factory(seed.cliente_1, estado="listo")
    login(seed.cocina, COCINA_PERMISSIONS, role="cocina")

    # The form tries to force "pendiente"; the route only allows the next state.
    response = client.post(
        f"/cocina/{pedido_id}/avanzar", data={"estado": "pendiente"}
    )

    assert response.status_code == 302
    with app.app_context():
        pedido = db.session.get(Pedido, uuid.UUID(pedido_id))
        assert pedido.estado != "pendiente"
        assert pedido.estado == "entregado"
