import { useMutation, useQueryClient } from '@tanstack/react-query';
import { transicionarEstado } from '../services/orders.service';

interface TransitionArgs {
  id: number;
  estado_codigo_destino: string;
  motivo?: string;
}

export function useTransitionOrderState() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, estado_codigo_destino, motivo }: TransitionArgs) =>
      transicionarEstado(id, estado_codigo_destino, motivo),
    onSuccess(_data, variables) {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['orders', variables.id] });
    },
  });
}
