"""Server-rendered pages (Jinja2) for the La Carta flow.

The JSON API in routes.py stays untouched for deployment; these routes are the
browser UI. Every business rule is enforced here on the server, never in the
template.
"""

import uuid
from decimal import Decimal

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from api_flask.auth import requires_auth
from api_flask.auth.service import usuario_from_payload
from api_flask.extensions import db
from api_flask.models import ItemPedido, Pedido, Plato, Restaurante, Usuario

bp = Blueprint("views", __name__)

ESTADOS_ACTIVOS = ("pendiente", "en_preparacion", "listo")
SIGUIENTE_ESTADO = {
    "pendiente": "en_preparacion",
    "en_preparacion": "listo",
    "listo": "entregado",
}


def _get_or_404(model, object_id):
    obj = db.session.get(model, object_id)
    if obj is None or getattr(obj, "eliminado", 0):
        abort(404)
    return obj


def _items_de(pedido):
    return (
        db.session.query(ItemPedido, Plato)
        .join(Plato, ItemPedido.plato_id == Plato.id)
        .filter(ItemPedido.pedido_id == pedido.id)
        .all()
    )


# ------------------------------------------------------------------- público


@bp.get("/")
def index():
    """The menu is public: listado y detalle no piden login."""
    q = request.args.get("q", "").strip()
    query = Restaurante.query.filter_by(eliminado=0)
    if q:
        query = query.filter(Restaurante.nombre.ilike(f"%{q}%"))
    total = query.count()
    restaurantes = query.order_by(Restaurante.nombre.asc()).limit(60).all()
    return render_template(
        "index.html",
        restaurantes=restaurantes,
        q=q,
        mostrar_mas=total > len(restaurantes),
    )


@bp.get("/restaurantes/<uuid:restaurante_id>")
def restaurante_detalle(restaurante_id):
    restaurante = _get_or_404(Restaurante, restaurante_id)
    platos = (
        Plato.query.filter_by(restaurante_id=restaurante.id, eliminado=0)
        .order_by(Plato.nombre.asc())
        .all()
    )
    return render_template(
        "restaurante.html", restaurante=restaurante, platos=platos
    )


# -------------------------------------------------------------------- pedidos


@bp.post("/pedidos")
@requires_auth("create:pedidos")
def crear_pedido(payload):
    """One atomic transaction: total on the server, frozen unit prices."""
    usuario = usuario_from_payload(payload)
    if usuario is None:
        abort(403)

    restaurante = _get_or_404(
        Restaurante, _uuid_or_400(request.form.get("restaurante_id"))
    )
    destino = url_for("views.restaurante_detalle", restaurante_id=restaurante.id)

    items = []  # (Plato, cantidad)
    for field, raw in request.form.items():
        if not field.startswith("cantidad_"):
            continue
        if str(raw).strip() in ("", "0"):
            continue

        plato = db.session.get(Plato, _uuid_or_400(field.removeprefix("cantidad_")))
        if plato is None or plato.eliminado:
            flash("El plato no existe.", "error")
            return redirect(destino)
        if not plato.disponible:
            flash(f"El plato «{plato.nombre}» no está disponible.", "error")
            return redirect(destino)
        if plato.restaurante_id != restaurante.id:
            flash("Todos los platos deben ser del mismo restaurante.", "error")
            return redirect(destino)
        try:
            cantidad = int(str(raw).strip())
        except ValueError:
            flash("La cantidad debe ser un entero entre 1 y 20.", "error")
            return redirect(destino)
        if not 1 <= cantidad <= 20:
            flash("La cantidad debe ser un entero entre 1 y 20.", "error")
            return redirect(destino)
        items.append((plato, cantidad))

    if not items:
        flash("Selecciona al menos un plato.", "error")
        return redirect(destino)

    total = sum(
        (plato.precio * cantidad for plato, cantidad in items), Decimal("0.00")
    )

    try:
        pedido = Pedido(
            usuario_id=usuario.id,
            restaurante_id=restaurante.id,
            estado="pendiente",
            total=total,
        )
        db.session.add(pedido)
        db.session.flush()

        for plato, cantidad in items:
            db.session.add(
                ItemPedido(
                    pedido_id=pedido.id,
                    plato_id=plato.id,
                    cantidad=cantidad,
                    precio_unitario=plato.precio,  # frozen price
                )
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("No se pudo crear el pedido")
        flash("No se pudo registrar el pedido. Intenta de nuevo.", "error")
        return redirect(destino)

    flash("Pedido registrado.", "success")
    return redirect(url_for("views.pedido_detalle", pedido_id=pedido.id))


@bp.get("/pedidos")
@requires_auth("read:mis-pedidos")
def mis_pedidos(payload):
    usuario = usuario_from_payload(payload)
    if usuario is None:
        abort(403)
    pedidos = (
        Pedido.query.filter_by(usuario_id=usuario.id, eliminado=0)
        .order_by(Pedido.fecha.desc())
        .all()
    )
    return render_template("pedidos.html", pedidos=pedidos, usuario=usuario)


@bp.get("/pedidos/<uuid:pedido_id>")
@requires_auth
def pedido_detalle(payload, pedido_id):
    pedido = db.session.get(Pedido, pedido_id)
    if pedido is None or pedido.eliminado:
        abort(404)

    usuario = usuario_from_payload(payload)
    can_read_all = "read:pedidos" in payload.get("permissions", [])
    if not can_read_all and (usuario is None or pedido.usuario_id != usuario.id):
        # 404, not 403: do not confirm that someone else's order exists.
        abort(404)

    return render_template(
        "pedido.html",
        pedido=pedido,
        restaurante=db.session.get(Restaurante, pedido.restaurante_id),
        items=_items_de(pedido),
        dueno=db.session.get(Usuario, pedido.usuario_id),
        usuario=usuario,
    )


@bp.post("/pedidos/<uuid:pedido_id>/cancelar")
@requires_auth("read:mis-pedidos")
def cancelar_pedido(payload, pedido_id):
    pedido = db.session.get(Pedido, pedido_id)
    if pedido is None or pedido.eliminado:
        abort(404)

    usuario = usuario_from_payload(payload)
    if usuario is None or pedido.usuario_id != usuario.id:
        abort(404)

    updated = Pedido.query.filter_by(id=pedido.id, estado="pendiente").update(
        {"estado": "cancelado"}, synchronize_session=False
    )
    db.session.commit()
    if updated:
        flash("Pedido cancelado.", "success")
    else:
        flash("Solo se puede cancelar un pedido pendiente.", "error")

    return redirect(url_for("views.pedido_detalle", pedido_id=pedido.id))


# -------------------------------------------------------------------- cocina


@bp.get("/cocina")
@requires_auth("read:pedidos")
def cocina(payload):
    pedidos = (
        Pedido.query.filter(
            Pedido.eliminado == 0, Pedido.estado.in_(ESTADOS_ACTIVOS)
        )
        .order_by(Pedido.fecha.asc())
        .all()
    )
    usuarios = {
        usuario.id: usuario
        for usuario in Usuario.query.filter(
            Usuario.id.in_([pedido.usuario_id for pedido in pedidos])
        ).all()
    }
    return render_template("cocina.html", pedidos=pedidos, usuarios=usuarios)


@bp.post("/cocina/<uuid:pedido_id>/avanzar")
@requires_auth("update:pedidos")
def avanzar_pedido(payload, pedido_id):
    pedido = db.session.get(Pedido, pedido_id)
    if pedido is None or pedido.eliminado:
        abort(404)

    siguiente = SIGUIENTE_ESTADO.get(pedido.estado)
    if siguiente is None:
        flash(f"El pedido ya está {pedido.estado}.", "error")
        return redirect(url_for("views.pedido_detalle", pedido_id=pedido.id))

    # Conditional UPDATE: two cocineros clicking at once advance it only once.
    updated = Pedido.query.filter_by(id=pedido.id, estado=pedido.estado).update(
        {"estado": siguiente}, synchronize_session=False
    )
    db.session.commit()
    if updated:
        flash(f"Pedido → {siguiente}.", "success")
    else:
        flash("Otro usuario cambió el estado antes. Recarga la cola.", "error")

    return redirect(url_for("views.cocina"))


def _uuid_or_400(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        abort(400)
