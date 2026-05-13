"""
Pydantic schema tests for order-state-machine-fsm #16.

Tests: AvanzarEstadoRequest validation.
Runner: cd backend && uv run pytest tests/integration/test_schemas.py -v
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestAvanzarEstadoRequest:

    def test_avanzar_estado_request_acepta_estados_validos(self):
        """Schema accepts all valid manual transition targets."""
        from backend.features.orders.schemas import AvanzarEstadoRequest

        for estado in {"CANCELADO", "EN_PREPARACION", "EN_CAMINO", "ENTREGADO"}:
            req = AvanzarEstadoRequest(nuevo_estado=estado)
            assert req.nuevo_estado == estado

    def test_avanzar_estado_request_rechaza_confirmado(self):
        """Schema rejects CONFIRMADO — manual confirmation is forbidden (D5)."""
        from backend.features.orders.schemas import AvanzarEstadoRequest

        with pytest.raises(ValidationError):
            AvanzarEstadoRequest(nuevo_estado="CONFIRMADO")

    def test_avanzar_estado_request_rechaza_estado_inexistente(self):
        """Schema rejects unknown state codes."""
        from backend.features.orders.schemas import AvanzarEstadoRequest

        with pytest.raises(ValidationError):
            AvanzarEstadoRequest(nuevo_estado="FOO")

    def test_avanzar_estado_request_rechaza_motivo_demasiado_largo(self):
        """Schema rejects motivo longer than 500 characters."""
        from backend.features.orders.schemas import AvanzarEstadoRequest

        with pytest.raises(ValidationError):
            AvanzarEstadoRequest(nuevo_estado="CANCELADO", motivo="x" * 501)

    def test_avanzar_estado_request_acepta_motivo_valido(self):
        """Schema accepts motivo within 500 chars."""
        from backend.features.orders.schemas import AvanzarEstadoRequest

        req = AvanzarEstadoRequest(nuevo_estado="CANCELADO", motivo="x" * 500)
        assert len(req.motivo) == 500

    def test_avanzar_estado_request_motivo_opcional(self):
        """motivo defaults to None when not provided."""
        from backend.features.orders.schemas import AvanzarEstadoRequest

        req = AvanzarEstadoRequest(nuevo_estado="CANCELADO")
        assert req.motivo is None
