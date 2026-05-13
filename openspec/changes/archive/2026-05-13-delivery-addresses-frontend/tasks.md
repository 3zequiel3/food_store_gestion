## 1. Tipos, servicio y schema

- [x] 1.1 Crear `features/delivery-addresses/types/deliveryAddress.types.ts` con `DireccionRead` (`id, usuario_id, calle, numero, piso_depto: string|null, ciudad, codigo_postal, referencia: string|null, es_principal: boolean`), `DireccionCreate` (`calle, numero, piso_depto?, ciudad, codigo_postal, referencia?`) y `DireccionUpdate` (todos opcionales igual que Create)
- [x] 1.2 Crear `features/delivery-addresses/services/deliveryAddresses.service.ts` con `getAddresses()`, `createAddress(data)` → 201, `updateAddress(id, data)` → 200, `deleteAddress(id)` → void (204), `setPrincipal(id)` → 200
- [x] 1.3 Crear `features/delivery-addresses/schemas/addressSchema.ts` con Zod: calle/numero/ciudad/codigo_postal requeridos (min 1, trim), piso_depto y referencia opcionales (string vacío → undefined)

## 2. Hooks TanStack Query

- [x] 2.1 Crear `features/delivery-addresses/hooks/useAddresses.ts` — `useQuery({ queryKey: ['addresses'], queryFn: getAddresses })`
- [x] 2.2 Crear `features/delivery-addresses/hooks/useCreateAddress.ts` — `useMutation` + onSuccess invalida `['addresses']`
- [x] 2.3 Crear `features/delivery-addresses/hooks/useUpdateAddress.ts` — `useMutation` con `(id, data)` + onSuccess invalida `['addresses']`
- [x] 2.4 Crear `features/delivery-addresses/hooks/useDeleteAddress.ts` — `useMutation` con id + onSuccess invalida `['addresses']`
- [x] 2.5 Crear `features/delivery-addresses/hooks/useSetPrincipal.ts` — `useMutation` con id + onSuccess invalida `['addresses']`

## 3. Componentes

- [x] 3.1 Crear `features/delivery-addresses/components/AddressCard.tsx` — muestra datos de la dirección, badge "Predeterminada" si `es_principal`, botón "Establecer como predeterminada" si `!es_principal`, botón "Editar" (llama a `onEdit`), botón "Eliminar" con confirmación inline (estado local `confirming`)
- [x] 3.2 Crear `features/delivery-addresses/components/AddressModal.tsx` — `<dialog>` nativo, modo alta (sin `address` prop) o edición (con `address` pre-cargado), TanStack Form con addressSchema onBlur, submit llama `useCreateAddress` o `useUpdateAddress` según modo, cierra el modal onSuccess, muestra errores backend inline

## 4. Página y routing

- [x] 4.1 Crear `pages/client/AddressesPage.tsx` — usa `useAddresses()`, skeleton mientras carga, estado vacío con CTA, lista de `AddressCard`, botón flotante/header "Agregar dirección" que abre `AddressModal` en modo alta; pasa `onEdit` a cada `AddressCard` para abrir el modal en modo edición
- [x] 4.2 En `router/AppRoute.tsx` reemplazar el `PlaceholderPage` de `/cliente/direcciones` por `<AddressesPage />`
