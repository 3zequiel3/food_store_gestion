"""
Enumeration definitions for domain entities.
"""

from enum import Enum


class EstadoPedido(str, Enum):
    """Order states/statuses."""

    PENDIENTE = "PENDIENTE"
    CONFIRMADO = "CONFIRMADO"
    EN_PREPARACIÓN = "EN_PREPARACIÓN"
    EN_CAMINO = "EN_CAMINO"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"


class FormaPago(str, Enum):
    """Payment methods."""

    EFECTIVO = "EFECTIVO"
    TARJETA_CREDITO = "TARJETA_CREDITO"
    MERCADOPAGO = "MERCADOPAGO"


class Role(str, Enum):
    """User roles."""

    ADMIN = "ADMIN"
    USER = "USER"
    DELIVERY = "DELIVERY"
