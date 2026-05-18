"""Custom exceptions for checkout module."""

from shared.exceptions import BusinessRuleError


class PaymentRejectedError(BusinessRuleError):
    """Raised when MercadoPago rejects the payment."""
    
    def __init__(self, mp_status: str, status_detail: str):
        super().__init__(
            f"Pago rechazado: {mp_status} - {status_detail}",
            code="payment_rejected"
        )
        self.mp_status = mp_status
        self.status_detail = status_detail


class PaymentPendingNotAcceptedError(BusinessRuleError):
    """Raised when MP returns pending/in_process (strict mode D3)."""
    
    def __init__(self, mp_status: str, status_detail: str):
        super().__init__(
            "Tu pago quedó en revisión y no podemos confirmar el pedido. "
            "Probá con otra tarjeta o elegí pago en efectivo al retirar.",
            code="payment_pending_not_accepted"
        )
        self.mp_status = mp_status
        self.status_detail = status_detail


class PaymentCancelledError(BusinessRuleError):
    """Raised when MP returns cancelled status."""
    
    def __init__(self, mp_status: str, status_detail: str):
        super().__init__(
            "El pago fue cancelado. Probá con otro método.",
            code="payment_cancelled"
        )
        self.mp_status = mp_status
        self.status_detail = status_detail


class PaymentUnexpectedStatusError(BusinessRuleError):
    """Raised when MP returns an unknown status."""
    
    def __init__(self, mp_status: str, status_detail: str):
        super().__init__(
            f"Estado de pago inesperado: {mp_status}",
            code="payment_unexpected_status"
        )
        self.mp_status = mp_status
        self.status_detail = status_detail


class UpstreamError(BusinessRuleError):
    """Raised when upstream service (MP) is unreachable."""
    
    def __init__(self, code: str, detail: str):
        super().__init__(detail, code=code)
