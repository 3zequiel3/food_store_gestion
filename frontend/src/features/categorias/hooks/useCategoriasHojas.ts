import { useQuery } from '@tanstack/react-query';
import { getCategoriasHojas } from '../services/categorias.service';

export function useCategoriasHojas() {
  return useQuery({
    queryKey: ['categorias', 'hojas'],
    queryFn: getCategoriasHojas,
    staleTime: 30_000,
  });
}
