import { useSearchParams } from 'react-router-dom';
import { useProducts } from '../../features/products/hooks/useProducts';
import { SearchBar } from '../../features/products/components/filters/SearchBar';
import { CategoryFilter } from '../../features/products/components/filters/CategoryFilter';
import { AllergenFilter } from '../../features/products/components/filters/AllergenFilter';
import { ActiveFilterChips } from '../../features/products/components/filters/ActiveFilterChips';
import { ProductGrid } from '../../features/products/components/ProductGrid';
import { Pagination } from '../../features/products/components/Pagination';
import type { ProductFilters } from '../../features/products/types/products.types';

export function CatalogPage() {
  const [searchParams] = useSearchParams();

  const filters = parseFiltersFromSearchParams(searchParams);

  const { data, isLoading } = useProducts(filters);

  const isEmpty = !isLoading && (data?.total ?? 0) === 0;

  const currentPage = filters.page ?? 1;
  const limit = filters.limit ?? 20;

  return (
    <div className="flex flex-col gap-6 p-4 sm:p-6 max-w-7xl mx-auto w-full">
      <div>
        <h1 className="text-2xl font-bold text-foreground bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
          Catálogo
        </h1>
        {data && !isLoading && (
          <p className="text-sm text-muted-foreground mt-1">
            {data.total} producto{data.total !== 1 ? 's' : ''} encontrado{data.total !== 1 ? 's' : ''}
          </p>
        )}
      </div>

      <div className="flex justify-center">
        <div className="w-full max-w-md">
          <SearchBar />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 rounded-xl bg-glass backdrop-blur-xl border border-glass-border p-4 shadow-sm">
        <CategoryFilter />
        <AllergenFilter />
      </div>

      <ActiveFilterChips />

      <ProductGrid
        products={data?.items ?? []}
        isLoading={isLoading}
        isEmpty={isEmpty}
      />

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

function parseFiltersFromSearchParams(searchParams: URLSearchParams): ProductFilters {
  const filters: ProductFilters = {
    disponible: true,
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
