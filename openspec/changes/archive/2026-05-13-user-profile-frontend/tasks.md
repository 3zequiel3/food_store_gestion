## 1. Tipos y servicio

- [x] 1.1 Crear `features/user-profile/types/userProfile.types.ts` con `ProfileRead` (`id, email, nombre, apellido, telefono: string | null, roles: string[], creado_en: string, actualizado_en: string`) y `UpdateProfilePayload` (`nombre?: string, apellido?: string, telefono?: string | null`) y `ChangePasswordPayload` (`password_actual: string, password_nuevo: string`)
- [x] 1.2 Crear `features/user-profile/services/userProfile.service.ts` con `getProfile()` → GET ENDPOINTS.usuarios.me, `updateProfile(data: UpdateProfilePayload)` → PATCH ENDPOINTS.usuarios.me, `changePassword(payload: ChangePasswordPayload)` → POST ENDPOINTS.usuarios.password

## 2. Schemas Zod

- [x] 2.1 Crear `features/user-profile/schemas/profileSchema.ts` con validación: `nombre` min 2 / max 80, `apellido` min 2 / max 80, `telefono` nullable (null | string que matchee `^\+?[\d\s\-\(\)]{6,30}$`), cadena vacía transformada a undefined
- [x] 2.2 Crear `features/user-profile/schemas/passwordSchema.ts` con `password_actual` requerido y `password_nuevo` min 8 / max 128

## 3. Hooks TanStack Query

- [x] 3.1 Crear `features/user-profile/hooks/useProfile.ts` — `useQuery({ queryKey: ['user-profile'], queryFn: getProfile })`
- [x] 3.2 Crear `features/user-profile/hooks/useUpdateProfile.ts` — `useMutation` con `mutationFn: updateProfile`, onSuccess invalida `['user-profile']` y actualiza `authStore.user` con los campos actualizados
- [x] 3.3 Crear `features/user-profile/hooks/useChangePassword.ts` — `useMutation` con `mutationFn: changePassword`, onSuccess llama `clearSession()` y navega a `/login`

## 4. Componentes

- [x] 4.1 Crear `features/user-profile/components/ProfileForm.tsx` — TanStack Form con campos nombre, apellido, teléfono (pre-cargados desde `ProfileRead`), validación onBlur con profileSchema, muestra errores inline y el email como campo read-only no editable; botón "Guardar" deshabilitado + spinner durante isPending; errores del backend mostrados como alert inline
- [x] 4.2 Crear `features/user-profile/components/PasswordModal.tsx` — `<dialog>` nativo controlado con `useRef` y `useState(isOpen)`, campos `password_actual` y `password_nuevo` con validación passwordSchema onBlur, errores del backend inline (401 → "Credenciales inválidas", 422 → detail del backend), botón Cancelar resetea el form y cierra el dialog; botón Guardar deshabilitado durante isPending

## 5. Página y routing

- [x] 5.1 Crear `pages/client/ProfilePage.tsx` — compone `ProfileForm` y un botón "Cambiar contraseña" que abre `PasswordModal`; usa `useProfile()` para cargar datos; skeleton mientras isLoading; mensaje de error + botón Reintentar si isError
- [x] 5.2 En `router/AppRoute.tsx` reemplazar el `PlaceholderPage` de la ruta `/cliente/perfil` por `<ProfilePage />`
