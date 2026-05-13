import { useQuery } from '@tanstack/react-query';
import { getPaymentByOrder } from '../services/payments.service';

export function usePaymentByOrder(pedidoId: number | null) {
  return useQuery({
    queryKey: ['payments', 'pedido', pedidoId],
    queryFn: () => getPaymentByOrder(pedidoId!),
    enabled: pedidoId !== null,
    staleTime: 0,
  });
}
