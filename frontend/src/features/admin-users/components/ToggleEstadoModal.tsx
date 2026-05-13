import { useEffect } from 'react';
import { X, AlertTriangle } from 'lucide-react';
import type { AdminUserResponse } from '../types/admin-users.types';
import { useChangeEstado } from '../hooks/useChangeEstado';

interface ToggleEstadoModalProps {
  user: AdminUserResponse;
  onClose: () => void;
}

export function ToggleEstadoModal({ user, onClose }: ToggleEstadoModalProps) {
  const { mutate, isPending } = useChangeEstado(onClose);
  const isDeactivating = user.is_active;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  function handleConfirm() {
    mutate({ id: user.id, payload: { is_active: !user.is_active } });
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-card border border-border rounded-lg w-full max-w-sm p-6 shadow-lg" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-foreground">
            {isDeactivating ? 'Desactivar cuenta' : 'Activar cuenta'}
          </h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-accent text-muted-foreground"><X className="h-4 w-4" /></button>
        </div>

        {isDeactivating && (
          <div className="flex items-start gap-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 mb-4">
            <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
            <p className="text-xs text-amber-800 dark:text-amber-300">
              Al desactivar la cuenta se revocarán todas las sesiones activas del usuario.
            </p>
          </div>
        )}

        <p className="text-sm text-foreground mb-6">
          ¿Confirmar {isDeactivating ? 'desactivación' : 'activación'} de la cuenta de{' '}
          <span className="font-semibold">{user.nombre} {user.apellido}</span>?
        </p>

        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 px-4 py-2 text-sm border border-border rounded-lg hover:bg-accent transition-colors">
            Cancelar
          </button>
          <button
            onClick={handleConfirm}
            disabled={isPending}
            className={`flex-1 px-4 py-2 text-sm rounded-lg transition-colors disabled:opacity-50 font-medium ${
              isDeactivating
                ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90'
                : 'bg-primary text-primary-foreground hover:bg-primary/90'
            }`}
          >
            {isPending ? 'Procesando...' : isDeactivating ? 'Desactivar' : 'Activar'}
          </button>
        </div>
      </div>
    </div>
  );
}
