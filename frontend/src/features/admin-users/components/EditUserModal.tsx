import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import type { AdminUserResponse } from '../types/admin-users.types';
import { useUpdateUser } from '../hooks/useUpdateUser';

interface EditUserModalProps {
  user: AdminUserResponse;
  onClose: () => void;
}

export function EditUserModal({ user, onClose }: EditUserModalProps) {
  const [nombre, setNombre] = useState(user.nombre);
  const [apellido, setApellido] = useState(user.apellido);
  const [telefono, setTelefono] = useState(user.telefono ?? '');
  const [errors, setErrors] = useState<{ nombre?: string; apellido?: string }>({});

  const { mutate, isPending } = useUpdateUser(onClose);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  function validate() {
    const errs: typeof errors = {};
    if (nombre.trim().length < 2) errs.nombre = 'Mínimo 2 caracteres';
    if (apellido.trim().length < 2) errs.apellido = 'Mínimo 2 caracteres';
    return errs;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    mutate({ id: user.id, payload: { nombre: nombre.trim(), apellido: apellido.trim(), telefono: telefono.trim() || null } });
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-card border border-border rounded-lg w-full max-w-md p-6 shadow-lg" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-foreground">Editar usuario</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-accent text-muted-foreground"><X className="h-4 w-4" /></button>
        </div>
        <p className="text-sm text-muted-foreground mb-4">{user.email}</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Nombre</label>
            <input value={nombre} onChange={(e) => setNombre(e.target.value)} className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
            {errors.nombre && <p className="text-xs text-destructive mt-1">{errors.nombre}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Apellido</label>
            <input value={apellido} onChange={(e) => setApellido(e.target.value)} className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
            {errors.apellido && <p className="text-xs text-destructive mt-1">{errors.apellido}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Teléfono</label>
            <input value={telefono} onChange={(e) => setTelefono(e.target.value)} className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" placeholder="Opcional" />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 px-4 py-2 text-sm border border-border rounded-lg hover:bg-accent transition-colors">Cancelar</button>
            <button type="submit" disabled={isPending} className="flex-1 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50">
              {isPending ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
