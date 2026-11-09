"""Roles and permissions.

In the exam these claims come from Auth0 (RBAC). While the app runs without an
Auth0 tenant, the same six permission names are derived from the local role so
the decorator and the templates do not change when Auth0 is connected.
"""

CREATE_PEDIDOS = "create:pedidos"
READ_MIS_PEDIDOS = "read:mis-pedidos"
READ_PEDIDOS = "read:pedidos"
UPDATE_PEDIDOS = "update:pedidos"
WRITE_CARTA = "write:carta"
DELETE_CARTA = "delete:carta"

ALL_PERMISSIONS = (
    CREATE_PEDIDOS,
    READ_MIS_PEDIDOS,
    READ_PEDIDOS,
    UPDATE_PEDIDOS,
    WRITE_CARTA,
    DELETE_CARTA,
)

ROLE_PERMISSIONS = {
    # cliente: hace pedidos y ve/cancela solo los suyos
    "cliente": (CREATE_PEDIDOS, READ_MIS_PEDIDOS),
    # cocina: ve la cola y avanza estados
    "cocina": (READ_PEDIDOS, UPDATE_PEDIDOS),
    # admin: carta + lectura de pedidos en Flask; corrige estados en Django
    "admin": (READ_PEDIDOS, WRITE_CARTA, DELETE_CARTA),
}

ROLES = tuple(ROLE_PERMISSIONS)


def permissions_for_role(role):
    """Return the permission list for a role (empty for unknown roles)."""
    return list(ROLE_PERMISSIONS.get((role or "").strip().lower(), ()))
