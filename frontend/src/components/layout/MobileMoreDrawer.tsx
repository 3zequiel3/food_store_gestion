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

export function MobileMoreDrawer({ isOpen, onClose }: MobileMoreDrawerProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      dialog.showModal();
    } else {
      dialog.close();
    }
  }, [isOpen]);

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
        rounded-t-2xl bg-glass backdrop-blur-xl border-t border-glass-border p-0
        backdrop:bg-black/60 backdrop:backdrop-blur-sm
        open:animate-in open:slide-in-from-bottom-4
      "
      aria-label="Más opciones"
    >
      <div className="flex items-center justify-between border-b border-glass-border px-4 py-3">
        <span className="text-sm font-medium text-foreground">Más opciones</span>
        <button
          type="button"
          onClick={onClose}
          className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-glass-hover hover:text-foreground transition-colors"
          aria-label="Cerrar"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <nav className="p-3">
        {MORE_ITEMS.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            onClick={onClose}
            className="flex h-12 items-center gap-3 rounded-lg px-3 text-sm text-muted-foreground hover:bg-glass-hover hover:text-foreground transition-colors"
          >
            {item.icon}
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      <div className="h-safe-area-inset-bottom" />
    </dialog>
  );
}
