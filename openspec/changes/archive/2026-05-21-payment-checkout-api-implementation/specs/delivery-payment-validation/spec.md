# Delta Spec: Delivery-Payment Method Validation

## Capability
`delivery-payment-validation`

## Requirement: Payment Method Filtering by Delivery Mode

### Scenario: Delivery order accepts TARJETA
- **Given** a client creating an order with a delivery address (`direccion_id` set)
- **When** the client selects payment method `TARJETA`
- **Then** the order is created successfully

### Scenario: Delivery order accepts TRANSFERENCIA
- **Given** a client creating an order with a delivery address
- **When** the client selects payment method `TRANSFERENCIA`
- **Then** the order is created successfully

### Scenario: Delivery order rejects EFECTIVO
- **Given** a client creating an order with a delivery address
- **When** the client selects payment method `EFECTIVO`
- **Then** the request returns `400 Bad Request`
- **And** the error message: "El pago en efectivo no está disponible para envíos. Elegí tarjeta o transferencia."

### Scenario: Pickup order accepts EFECTIVO
- **Given** a client creating an order without a delivery address (`direccion_id` is null/omitted)
- **When** the client selects payment method `EFECTIVO`
- **Then** the order is created successfully

### Scenario: Pickup order accepts TARJETA
- **Given** a client creating an order without a delivery address
- **When** the client selects payment method `TARJETA`
- **Then** the order is created successfully

### Scenario: Pickup order accepts TRANSFERENCIA
- **Given** a client creating an order without a delivery address
- **When** the client selects payment method `TRANSFERENCIA`
- **Then** the order is created successfully

### Scenario: Frontend filters payment methods for delivery mode
- **Given** the checkout page with a delivery address selected
- **When** the payment method selector is rendered
- **Then** EFECTIVO is NOT shown in the list
- **And** a message is displayed: "Para envíos, aceptamos tarjeta o transferencia bancaria"

### Scenario: Frontend shows all payment methods for pickup mode
- **Given** the checkout page with "Retiro en local" selected (no delivery address)
- **When** the payment method selector is rendered
- **Then** ALL payment methods are shown: TARJETA, EFECTIVO, TRANSFERENCIA

### Scenario: Frontend resets payment selection when switching to delivery
- **Given** the checkout page with pickup mode and EFECTIVO selected
- **When** the user selects a delivery address
- **Then** the payment selection is cleared (reset to null)
- **And** EFECTIVO is removed from the available options

## Backend Validation Rule

```python
def _validate_delivery_payment(forma_pago_codigo: str, direccion_id: int | None) -> None:
    is_delivery = direccion_id is not None
    if is_delivery and forma_pago_codigo == "EFECTIVO":
        raise ValidationError(
            "El pago en efectivo no está disponible para envíos. "
            "Elegí tarjeta o transferencia."
        )
```

## Frontend Filtering Logic

```typescript
const isDelivery = selectedAddressId !== null;
const filteredMethods = isDelivery
  ? methods.filter(m => m.codigo !== "EFECTIVO")
  : methods;

// When switching to delivery mode, reset payment if it was EFECTIVO:
if (isDelivery && selectedPaymentMethod === "EFECTIVO") {
  setSelectedPaymentMethod(null);
}
```

## Valid Combinations

| Delivery Mode | TARJETA | EFECTIVO | TRANSFERENCIA |
|---------------|---------|----------|---------------|
| Envío del local (direccion_id set) | ✅ | ❌ | ✅ |
| Retiro en local (direccion_id null) | ✅ | ✅ | ✅ |
