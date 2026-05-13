import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import type { AdminUserResponse } from '../types/admin-users.types';
import { ROLES } from '../types/admin-users.types';
import { useChangeRol } from '../hooks/useChangeRol';

interface ChangeRolModalProps {
  user: AdminUserResponse;
  onClose: () => void;
}

export function ChangeRolModal({ user, onClose }: ChangeRolModalProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set(user.roles));
  const { mutate, isPending } = useChangeRol(onClose);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  function toggle(rol: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(rol)) next.delete(rol); else next.add(rol);
      return next;
    });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (selected.size === 0) return;
    mutate({ id: user.id, payload: { roles: [...selected] } });
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-card border border-border rounded-lg w-full max-w-sm p-6 shadow-lg" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-foreground">Cambiar roles</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-accent text-muted-foreground"><X className="h-4 w-4" /></button>
        </div>
        <p className="text-sm text-muted-foreground mb-4">{user.nombre} {user.apellido}</p>
        <form onSubmit={handleSubmit} className="space-y-3">
          {ROLES.map((rol) => (
            <label key={rol} className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={selected.has(rol)}
                onChange={() => toggle(rol)}
                className="h-4 w-4 rounded border-border text-primary focus:ring-primary/40"
              />
              <span className="text-sm text-foreground">{rol}</span>
            </label>
          ))}
          {selected.size === 0 && (
            <p className="text-xs text-destructive">El usuario debe tener al menos un rol.</p>
          )}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 px-4 py-2 text-sm border border-border rounded-lg hover:bg-accent transition-colors">Cancelar</button>
            <button type="submit" disabled={isPending || selected.size === 0} className="flex-1 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50">
              {isPending ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
