import { useSearchParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  total: number;
  currentPage: number;
  limit: number;
}

export function Pagination({ total, currentPage, limit }: PaginationProps) {
  const [, setSearchParams] = useSearchParams();

  const totalPages = Math.ceil(total / limit);

  if (totalPages <= 1) return null;

  function goToPage(page: number) {
    setSearchParams((prev) => {
      const updated = new URLSearchParams(prev);
      updated.set('page', String(page));
      return updated;
    });
  }

  function getPageRange(): number[] {
    const delta = 2;
    const range: number[] = [];
    const start = Math.max(1, currentPage - delta);
    const end = Math.min(totalPages, currentPage + delta);

    for (let i = start; i <= end; i++) {
      range.push(i);
    }
    return range;
  }

  const pageRange = getPageRange();

  return (
    <nav aria-label="Navegación de páginas" className="flex items-center justify-center gap-1">
      <button
        type="button"
        onClick={() => goToPage(currentPage - 1)}
        disabled={currentPage <= 1}
        aria-label="Página anterior"
        className="flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium
          bg-glass backdrop-blur-sm border border-glass-border text-foreground hover:bg-glass-hover
          disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150"
      >
        <ChevronLeft className="h-4 w-4" />
        Anterior
      </button>

      {pageRange[0] > 1 && (
        <>
          <PageButton page={1} current={currentPage} onClick={goToPage} />
          {pageRange[0] > 2 && <span className="px-1 text-muted-foreground">…</span>}
        </>
      )}

      {pageRange.map((page) => (
        <PageButton key={page} page={page} current={currentPage} onClick={goToPage} />
      ))}

      {pageRange[pageRange.length - 1] < totalPages && (
        <>
          {pageRange[pageRange.length - 1] < totalPages - 1 && (
            <span className="px-1 text-muted-foreground">…</span>
          )}
          <PageButton page={totalPages} current={currentPage} onClick={goToPage} />
        </>
      )}

      <button
        type="button"
        onClick={() => goToPage(currentPage + 1)}
        disabled={currentPage >= totalPages}
        aria-label="Página siguiente"
        className="flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium
          bg-glass backdrop-blur-sm border border-glass-border text-foreground hover:bg-glass-hover
          disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150"
      >
        Siguiente
        <ChevronRight className="h-4 w-4" />
      </button>
    </nav>
  );
}

interface PageButtonProps {
  page: number;
  current: number;
  onClick: (page: number) => void;
}

function PageButton({ page, current, onClick }: PageButtonProps) {
  const isActive = page === current;
  return (
    <button
      type="button"
      onClick={() => onClick(page)}
      aria-label={`Página ${page}`}
      aria-current={isActive ? 'page' : undefined}
      className={`min-w-[2.25rem] px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150
        ${isActive
          ? 'bg-primary text-primary-foreground shadow-sm shadow-primary/30'
          : 'bg-glass backdrop-blur-sm border border-glass-border text-foreground hover:bg-glass-hover'
        }`}
    >
      {page}
    </button>
  );
}
