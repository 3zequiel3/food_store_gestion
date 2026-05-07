import { useEffect } from 'react'
import { useUIStore } from '../stores'
import type { Toast } from '../types/ui'

const levelStyles: Record<Toast['level'], string> = {
  error: 'bg-red-600 border-red-700',
  success: 'bg-green-600 border-green-700',
  warning: 'bg-yellow-500 border-yellow-600',
  info: 'bg-blue-600 border-blue-700',
}

const levelLabels: Record<Toast['level'], string> = {
  error: 'Error',
  success: 'Éxito',
  warning: 'Atención',
  info: 'Info',
}

const DEFAULT_DURATION = 4000

function ToastItem({ toast }: { toast: Toast }) {
  const dismissToast = useUIStore((s) => s.dismissToast)

  useEffect(() => {
    const timer = setTimeout(() => {
      dismissToast(toast.id)
    }, toast.durationMs ?? DEFAULT_DURATION)
    return () => clearTimeout(timer)
  }, [toast.id, toast.durationMs, dismissToast])

  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 rounded-lg border text-white shadow-lg min-w-[280px] max-w-sm ${levelStyles[toast.level]}`}
      role="alert"
    >
      <span className="text-xs font-bold uppercase tracking-wide shrink-0 mt-0.5">
        {levelLabels[toast.level]}
      </span>
      <p className="flex-1 text-sm">{toast.message}</p>
      <button
        onClick={() => dismissToast(toast.id)}
        className="shrink-0 text-white/80 hover:text-white leading-none text-lg"
        aria-label="Cerrar"
      >
        ×
      </button>
    </div>
  )
}

export const ToastContainer: React.FC = () => {
  const toasts = useUIStore((s) => s.toasts)

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} />
      ))}
    </div>
  )
}
