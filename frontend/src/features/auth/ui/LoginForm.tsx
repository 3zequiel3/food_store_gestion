import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../../shared/stores'
import { useUIStore } from '../../../shared/stores'
import { login } from '../api/authService'

const loginSchema = z.object({
  email: z.string().regex(/^[^\s@]+@[^\s@]+\.[^\s@]+$/, 'Ingresá un email válido'),
  password: z.string().min(1, 'La contraseña es requerida'),
})

type LoginFormValues = z.infer<typeof loginSchema>

export const LoginForm: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const [credentialError, setCredentialError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) })

  const onSubmit = async (values: LoginFormValues) => {
    setCredentialError(null)
    try {
      const result = await login(values)
      useAuthStore.getState().login(
        { accessToken: result.accessToken, refreshToken: result.refreshToken },
        result.user
      )
      const from = (location.state as { from?: Location })?.from
      navigate(from ? `${from.pathname}${from.search ?? ''}` : '/', { replace: true })
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 401) {
        setCredentialError('Credenciales inválidas')
      } else if (status === 429) {
        useUIStore.getState().pushToast({
          id: crypto.randomUUID(),
          message: 'Demasiados intentos, intentá de nuevo más tarde',
          level: 'error',
        })
      }
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <div>
        <label className="block text-gray-700 dark:text-gray-300 font-medium mb-2">
          Email
        </label>
        <input
          type="email"
          placeholder="tu@email.com"
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary dark:bg-gray-700 dark:text-white"
          {...register('email')}
        />
        {errors.email && (
          <p className="mt-1 text-sm text-red-500">{errors.email.message}</p>
        )}
      </div>

      <div>
        <label className="block text-gray-700 dark:text-gray-300 font-medium mb-2">
          Contraseña
        </label>
        <input
          type="password"
          placeholder="••••••••"
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary dark:bg-gray-700 dark:text-white"
          {...register('password')}
        />
        {errors.password && (
          <p className="mt-1 text-sm text-red-500">{errors.password.message}</p>
        )}
      </div>

      {credentialError && (
        <p className="text-sm text-red-500 text-center">{credentialError}</p>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full bg-primary text-white py-2 rounded-lg font-semibold hover:bg-primary-dark transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {isSubmitting ? 'Iniciando sesión...' : 'Iniciar sesión'}
      </button>
    </form>
  )
}
