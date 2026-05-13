import { useMutation, useQueryClient } from '@tanstack/react-query';
import { advanceOrderState } from '../services/orders.service';
import type { EstadoCodigo } from '../types/orders.types';

interface AdvanceArgs {
  id: number;
  nuevo_estado: EstadoCodigo;
  motivo?: string;
}

export function useAdvanceOrderState() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, nuevo_estado, motivo }: AdvanceArgs) =>
      advanceOrderState(id, nuevo_estado, motivo),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}
