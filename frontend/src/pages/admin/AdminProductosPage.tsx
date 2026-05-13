import { useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Package, Plus, Search } from 'lucide-react';
import { useProducts } from '../../features/products/hooks/useProducts';
import { ProductAdminRow } from '../../features/products/components/admin/ProductAdminRow';
import { ProductFormModal } from '../../features/products/components/admin/ProductFormModal';
import { DeleteProductModal } from '../../features/products/components/admin/DeleteProductModal';
import { Pagination } from '../../features/products/components/Pagination';
import type { ProductoRead } from '../../features/products/types/products.types';

const LIMIT = 20;

export function AdminProductosPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get('page') ?? '1');
  const search = searchParams.get('search') ?? '';

  const { data, isLoading, isError, refetch } = useProducts({
    page,
    limit: LIMIT,
    search: search || undefined,
  });

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editProduct, setEditProduct] = useState<ProductoRead | null>(null);
  const [deleteProduct, setDeleteProduct] = useState<ProductoRead | null>(null);

  const handleSearchChange = useCallback(
    (value: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (value) {
          next.set('search', value);
        } else {
          next.delete('search');
        }
        next.set('page', '1');
        return next;
      });
    },
    [setSearchParams],
  );

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
            <Package className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">Productos</h1>
            <p className="text-sm text-muted-foreground">
              {data ? `${data.total} productos` : 'Gestión del catálogo'}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Nuevo producto
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder="Buscar por nombre..."
          className="w-full pl-9 pr-4 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 max-w-sm"
        />
      </div>

      {/* Error */}
      {isError && (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <p className="text-sm text-muted-foreground">No se pudieron cargar los productos.</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Skeleton */}
      {isLoading && <TableSkeleton />}

      {/* Table */}
      {!isLoading && !isError && (
        <>
          {!data || data.items.length === 0 ? (
            <div className="flex flex-col items-center gap-4 py-20 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted">
                <Package className="h-7 w-7 text-muted-foreground/40" />
              </div>
              <div>
                <p className="font-medium text-foreground">No hay productos</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {search ? 'No hay resultados para la búsqueda.' : 'Creá el primer producto con el botón de arriba.'}
                </p>
              </div>
              {!search && (
                <button
                  type="button"
                  onClick={() => setShowCreateModal(true)}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
                >
                  <Plus className="h-4 w-4" />
                  Crear primer producto
                </button>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-border overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="bg-muted/50 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="px-4 py-3 w-12" />
                      <th className="px-4 py-3">Nombre</th>
                      <th className="px-4 py-3">Precio</th>
                      <th className="px-4 py-3">Stock</th>
                      <th className="px-4 py-3">Estado</th>
                      <th className="px-4 py-3 text-right">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((product) => (
                      <ProductAdminRow
                        key={product.id}
                        product={product}
                        onEdit={setEditProduct}
                        onDelete={setDeleteProduct}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {data && (
            <Pagination
              total={data.total}
              currentPage={data.page}
              limit={data.limit}
            />
          )}
        </>
      )}

      {/* Modals */}
      {showCreateModal && (
        <ProductFormModal onClose={() => setShowCreateModal(false)} />
      )}
      {editProduct && (
        <ProductFormModal
          producto={editProduct}
          onClose={() => setEditProduct(null)}
        />
      )}
      {deleteProduct && (
        <DeleteProductModal
          product={deleteProduct}
          onClose={() => setDeleteProduct(null)}
        />
      )}
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border border-border overflow-hidden">
      <div className="h-10 bg-muted/50" />
      {[...Array(6)].map((_, i) => (
        <div key={i} className="flex items-center gap-4 border-t border-border px-4 py-3">
          <div className="h-10 w-10 rounded-lg bg-muted flex-shrink-0" />
          <div className="flex-1 space-y-1.5">
            <div className="h-4 w-40 rounded bg-muted" />
            <div className="h-3 w-24 rounded bg-muted" />
          </div>
          <div className="h-4 w-16 rounded bg-muted" />
          <div className="h-4 w-8 rounded bg-muted" />
          <div className="h-5 w-20 rounded-full bg-muted" />
          <div className="ml-auto h-8 w-16 rounded bg-muted" />
        </div>
      ))}
    </div>
  );
}
