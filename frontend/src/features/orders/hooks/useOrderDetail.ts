import { useQuery } from '@tanstack/react-query';
import { getOrderDetail } from '../services/orders.service';

export function useOrderDetail(id: number | null) {
  return useQuery({
    queryKey: ['orders', id],
    queryFn: () => getOrderDetail(id!),
    enabled: id !== null,
  });
}
