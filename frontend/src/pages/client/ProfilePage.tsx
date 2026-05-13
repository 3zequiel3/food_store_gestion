import { useState } from 'react';
import { KeyRound, User } from 'lucide-react';
import { useProfile } from '../../features/user-profile/hooks/useProfile';
import { ProfileForm } from '../../features/user-profile/components/ProfileForm';
import { PasswordModal } from '../../features/user-profile/components/PasswordModal';

export function ProfilePage() {
  const { data: profile, isLoading, isError, refetch } = useProfile();
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);

  if (isLoading) {
    return <ProfileSkeleton />;
  }

  if (isError || !profile) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
        <p className="text-sm text-muted-foreground">
          No se pudo cargar tu perfil. Verificá tu conexión.
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg px-4 py-8 flex flex-col gap-8">
      {/* Datos personales */}
      <section className="flex flex-col gap-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
            <User className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">Mi perfil</h1>
            <p className="text-sm text-muted-foreground">Editá tus datos personales</p>
          </div>
        </div>

        <ProfileForm profile={profile} />
      </section>

      {/* Separador */}
      <div className="border-t border-border" />

      {/* Seguridad */}
      <section className="flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
            <KeyRound className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-foreground">Contraseña</h2>
            <p className="text-sm text-muted-foreground">
              Al cambiarla, vas a tener que volver a iniciar sesión.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setPasswordModalOpen(true)}
          className="h-11 w-full rounded-lg border border-border text-sm font-medium text-foreground hover:bg-accent transition-colors"
        >
          Cambiar contraseña
        </button>
      </section>

      <PasswordModal
        isOpen={passwordModalOpen}
        onClose={() => setPasswordModalOpen(false)}
      />
    </div>
  );
}

function ProfileSkeleton() {
  const shimmer = 'animate-shimmer bg-[length:200%_100%] bg-gradient-to-r from-muted/50 via-muted to-muted/50';
  return (
    <div className="mx-auto max-w-lg px-4 py-8 flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <div className={`h-10 w-10 rounded-full ${shimmer}`} />
        <div className="flex flex-col gap-2">
          <div className={`h-4 w-32 rounded ${shimmer}`} />
          <div className={`h-3 w-48 rounded ${shimmer}`} />
        </div>
      </div>
      {[...Array(4)].map((_, i) => (
        <div key={i} className="flex flex-col gap-2">
          <div className={`h-3 w-20 rounded ${shimmer}`} />
          <div className={`h-11 w-full rounded-lg ${shimmer}`} />
        </div>
      ))}
      <div className={`h-11 w-full rounded-lg ${shimmer}`} />
    </div>
  );
}
