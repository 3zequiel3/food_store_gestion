import { useQuery } from '@tanstack/react-query';
import { getProduct } from '../services/products.service';

/**
 * Hook para el detalle de un producto.
 *
 * `enabled: id > 0` evita disparar la query si el param del router aún no fue parseado.
 */
export function useProduct(id: number) {
  return useQuery({
    queryKey: ['products', id],
    queryFn: () => getProduct(id),
    enabled: id > 0,
  });
}
