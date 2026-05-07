import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../../shared/stores'
import { register as registerUser } from '../api/authService'

const registerSchema = z.object({
  nombre: z.string().min(2, 'Mínimo 2 caracteres').max(80, 'Máximo 80 caracteres'),
  apellido: z.string().min(2, 'Mínimo 2 caracteres').max(80, 'Máximo 80 caracteres'),
  email: z.string().regex(/^[^\s@]+@[^\s@]+\.[^\s@]+$/, 'Ingresá un email válido'),
  password: z.string().min(8, 'La contraseña debe tener al menos 8 caracteres'),
})

type RegisterFormValues = z.infer<typeof registerSchema>

export const RegisterForm: React.FC = () => {
  const navigate = useNavigate()
  const [emailError, setEmailError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) })

  const onSubmit = async (values: RegisterFormValues) => {
    setEmailError(null)
    try {
      const result = await registerUser(values)
      useAuthStore.getState().login(
        { accessToken: result.accessToken, refreshToken: result.refreshToken },
        result.user
      )
      navigate('/')
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 409) {
        setEmailError('Este email ya está registrado')
      }
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <div>
        <label className="block text-gray-700 dark:text-gray-300 font-medium mb-2">
          Nombre
        </label>
        <input
          type="text"
          placeholder="Tu nombre"
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary dark:bg-gray-700 dark:text-white"
          {...register('nombre')}
        />
        {errors.nombre && (
          <p className="mt-1 text-sm text-red-500">{errors.nombre.message}</p>
        )}
      </div>

      <div>
        <label className="block text-gray-700 dark:text-gray-300 font-medium mb-2">
          Apellido
        </label>
        <input
          type="text"
          placeholder="Tu apellido"
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary dark:bg-gray-700 dark:text-white"
          {...register('apellido')}
        />
        {errors.apellido && (
          <p className="mt-1 text-sm text-red-500">{errors.apellido.message}</p>
        )}
      </div>

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
        {emailError && (
          <p className="mt-1 text-sm text-red-500">{emailError}</p>
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

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full bg-primary text-white py-2 rounded-lg font-semibold hover:bg-primary-dark transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {isSubmitting ? 'Creando cuenta...' : 'Crear cuenta'}
      </button>
    </form>
  )
}
