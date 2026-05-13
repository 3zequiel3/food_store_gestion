const ROLE_STYLES: Record<string, string> = {
  ADMIN: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  STOCK: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  PEDIDOS: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  CLIENT: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
};

interface RoleBadgeProps {
  rol: string;
}

export function RoleBadge({ rol }: RoleBadgeProps) {
  const styles = ROLE_STYLES[rol] ?? 'bg-muted text-muted-foreground';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${styles}`}>
      {rol}
    </span>
  );
}
