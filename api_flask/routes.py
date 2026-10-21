from flask import Blueprint, jsonify, request, abort
from api_flask.models import Restaurante, Plato, Pedido

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
def listar_pedidos():
    pedidos = Pedido.query.filter_by(eliminado=0).all()
    return jsonify({
        'success': True,
        'total': len(pedidos),
        'pedidos': [p.format() for p in pedidos]
    })