from flask import Blueprint, abort, jsonify
from sqlalchemy.exc import SQLAlchemyError

from api_flask.auth import requires_auth
from api_flask.auth.service import usuario_from_payload
from api_flask.extensions import db
from api_flask.models import Pedido, Plato, Restaurante
from api_flask.views import _items_de

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/restaurantes")
def listar_restaurantes():
    restaurantes = Restaurante.query.filter_by(eliminado=0).all()
    return jsonify({
        'success': True,
        'total': len(restaurantes),
        'restaurantes': [r.format() for r in restaurantes]
    })


@bp.get("/platos")
def listar_platos():
    platos = Plato.query.filter_by(eliminado=0, disponible=True).all()
    return jsonify({
        'success': True,
        'total': len(platos),
        'platos': [p.format() for p in platos]
    })


@bp.get("/pedidos")
@requires_auth("read:pedidos")
def listar_pedidos(payload):
    """Kitchen queue: requires the same permission as the Jinja page."""
    pedidos = Pedido.query.filter_by(eliminado=0).all()
    return jsonify({
        'success': True,
        'total': len(pedidos),
        'pedidos': [p.format() for p in pedidos]
    })


@bp.get("/mis-pedidos")
@requires_auth("read:mis-pedidos")
def listar_mis_pedidos(payload):
    usuario = usuario_from_payload(payload)
    if usuario is None:
        abort(403)
    pedidos = (
        Pedido.query.filter_by(usuario_id=usuario.id, eliminado=0)
        .order_by(Pedido.fecha.desc())
        .all()
    )
    return jsonify({
        'success': True,
        'total': len(pedidos),
        'pedidos': [p.format() for p in pedidos]
    })


@bp.get("/pedidos/<uuid:pedido_id>")
@requires_auth
def detalle_pedido(payload, pedido_id):
    pedido = db.session.get(Pedido, pedido_id)
    if pedido is None or pedido.eliminado:
        abort(404)

    usuario = usuario_from_payload(payload)
    can_read_all = "read:pedidos" in payload.get("permissions", [])
    if not can_read_all and (usuario is None or pedido.usuario_id != usuario.id):
        # 404, not 403: do not confirm that someone else's order exists.
        abort(404)

    return jsonify({
        'success': True,
        'pedido': pedido.format(),
        'items': [
            {
                'id': str(item.id),
                'plato_id': str(item.plato_id),
                'plato': plato.nombre,
                'cantidad': item.cantidad,
                'precio_unitario': float(item.precio_unitario),
            }
            for item, plato in _items_de(pedido)
        ],
    })


@bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 404,
        'code': 'not_found',
        'message': 'Resource not found.'
    }), 404


@bp.errorhandler(SQLAlchemyError)
def database_error(error):
    db.session.rollback()
    return jsonify({
        'success': False,
        'error': 503,
        'code': 'database_unavailable',
        'message': 'Database unavailable.'
    }), 503
