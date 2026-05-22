/**
 * TanStack Query hooks for ingredient availability (Faltantes).
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { getFaltantes, resolverFaltante } from '../services/availability.service';
import type { ResolveRequest } from '../types/availability.types';

export const FALTANTES_QUERY_KEY = ['availability', 'faltantes'] as const;

/** Query hook: returns open shortage list. */
export function useFaltantes(enabled = true) {
  return useQuery({
    queryKey: FALTANTES_QUERY_KEY,
    queryFn: getFaltantes,
    enabled,
    staleTime: 30_000,
  });
}

/** Mutation hook: resolve a shortage with a friendly label. */
export function useResolverFaltante() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      ingredienteId,
      accion,
    }: {
      ingredienteId: number;
      accion?: ResolveRequest['accion'];
    }) => resolverFaltante(ingredienteId, { accion }),

    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: FALTANTES_QUERY_KEY });
      const label = data.rows_closed === 1 ? '1 reporte cerrado' : `${data.rows_closed} reportes cerrados`;
      toast.success('Faltante resuelto', { description: label });
    },

    onError: () => {
      toast.error('Error al resolver el faltante');
    },
  });
}
