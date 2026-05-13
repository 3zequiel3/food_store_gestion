import { useQuery } from '@tanstack/react-query';
import { getCategorias } from '../services/categorias.service';

export function useCategorias() {
  return useQuery({
    queryKey: ['categorias'],
    queryFn: getCategorias,
    staleTime: 30_000,
  });
}
