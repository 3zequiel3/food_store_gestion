import { useSearchParams } from 'react-router-dom';
import { useProducts } from '../../features/products/hooks/useProducts';
import { SearchBar } from '../../features/products/components/filters/SearchBar';
import { CategoryFilter } from '../../features/products/components/filters/CategoryFilter';
import { AllergenFilter } from '../../features/products/components/filters/AllergenFilter';
import { ActiveFilterChips } from '../../features/products/components/filters/ActiveFilterChips';
import { ProductGrid } from '../../features/products/components/ProductGrid';
import { Pagination } from '../../features/products/components/Pagination';
import type { ProductFilters } from '../../features/products/types/products.types';

/**
 * CatalogPage — página principal del catálogo de productos.
 *
 * D1: todos los filtros se leen de searchParams (URL-first state).
 * D2: paginación clásica con keepPreviousData.
 * Compone: SearchBar + CategoryFilter + AllergenFilter + ActiveFilterChips + ProductGrid + Pagination.
 */
export function CatalogPage() {
  const [searchParams] = useSearchParams();

  // 5.2 — Parsear filtros desde la URL
  const filters = parseFiltersFromSearchParams(searchParams);

  const { data, isLoading } = useProducts(filters);

  // 5.3 — isEmpty se pasa a ProductGrid para el mensaje vacío
  const isEmpty = !isLoading && (data?.total ?? 0) === 0;

  const currentPage = filters.page ?? 1;
  const limit = filters.limit ?? 20;

  return (
    <div className="flex flex-col gap-6 p-4 sm:p-6 max-w-7xl mx-auto w-full">
      {/* Encabezado */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Catálogo</h1>
        {data && !isLoading && (
          <p className="text-sm text-muted-foreground mt-1">
            {data.total} producto{data.total !== 1 ? 's' : ''} encontrado{data.total !== 1 ? 's' : ''}
          </p>
        )}
      </div>

      {/* Panel de filtros */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 rounded-xl border border-border bg-card p-4">
        <div className="sm:col-span-2 lg:col-span-1">
          <SearchBar />
        </div>
        <CategoryFilter />
        <AllergenFilter />
      </div>

      {/* Chips de filtros activos */}
      <ActiveFilterChips />

      {/* Grid de productos */}
      <ProductGrid
        products={data?.items ?? []}
        isLoading={isLoading}
        isEmpty={isEmpty}
      />

      {/* Paginación */}
      {data && data.total > 0 && (
        <Pagination
          total={data.total}
          currentPage={currentPage}
          limit={limit}
        />
      )}
    </div>
  );
}

/** Parsea los searchParams de la URL a ProductFilters tipados */
function parseFiltersFromSearchParams(searchParams: URLSearchParams): ProductFilters {
  const filters: ProductFilters = {
    disponible: true, // Siempre filtrar por disponibles en el catálogo cliente
  };

  const page = searchParams.get('page');
  if (page) filters.page = parseInt(page, 10);

  const limit = searchParams.get('limit');
  if (limit) filters.limit = parseInt(limit, 10);

  const search = searchParams.get('search');
  if (search) filters.search = search;

  const categoriaId = searchParams.get('categoria_id');
  if (categoriaId) filters.categoria_id = parseInt(categoriaId, 10);

  const excluirAlergenos = searchParams.get('excluir_alergenos');
  if (excluirAlergenos === 'true') filters.excluir_alergenos = true;

  const excluirIds = searchParams.getAll('excluir_alergeno_ids').map(Number).filter(Boolean);
  if (excluirIds.length > 0) filters.excluir_alergeno_ids = excluirIds;

  return filters;
}
