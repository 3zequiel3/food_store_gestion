import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { FolderTree, Carrot, X } from 'lucide-react';

interface MobileMoreDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

const MORE_ITEMS = [
  {
    label: 'Categorías',
    path: '/admin/categorias',
    icon: <FolderTree className="h-5 w-5" />,
  },
  {
    label: 'Ingredientes',
    path: '/admin/ingredientes',
    icon: <Carrot className="h-5 w-5" />,
  },
];

/**
 * Drawer bottom-up para items secundarios del BottomNav admin.
 * Usa <dialog> nativo para accesibilidad (focus trap nativo, ESC).
 */
export function MobileMoreDrawer({ isOpen, onClose }: MobileMoreDrawerProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  // Nota: NO cerrar acá en route change — el padre (AppLayout) ya lo hace via
  // su useEffect en [location.pathname]. Si poníamos un useEffect local con
  // `onClose` en deps, el `onClose` inline del padre (nueva referencia cada
  // render) disparaba un loop infinito de setState.

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      dialog.showModal();
    } else {
      dialog.close();
    }
  }, [isOpen]);

  // Cerrar al hacer clic en el backdrop (fuera del dialog)
  const handleBackdropClick = (e: React.MouseEvent<HTMLDialogElement>) => {
    if (e.target === dialogRef.current) {
      onClose();
    }
  };

  return (
    <dialog
      ref={dialogRef}
      onClick={handleBackdropClick}
      onClose={onClose}
      className="
        fixed bottom-16 left-0 right-0 m-0 max-w-none w-full
        rounded-t-2xl bg-chrome border-t border-border p-0
        backdrop:bg-black/50 backdrop:backdrop-blur-sm
        open:animate-in open:slide-in-from-bottom-4
      "
      aria-label="Más opciones"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <span className="text-sm font-medium text-foreground">Más opciones</span>
        <button
          type="button"
          onClick={onClose}
          className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          aria-label="Cerrar"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Items */}
      <nav className="p-3">
        {MORE_ITEMS.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            onClick={onClose}
            className="flex h-12 items-center gap-3 rounded-lg px-3 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          >
            {item.icon}
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      {/* Safe area bottom padding */}
      <div className="h-safe-area-inset-bottom" />
    </dialog>
  );
}
