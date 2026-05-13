import { useQuery } from '@tanstack/react-query';
import { getPaymentMethods } from '../services/paymentMethods.service';

/**
 * Hook para obtener las formas de pago habilitadas.
 *
 * Uses TanStack Query with staleTime of 5 minutes since payment
 * methods rarely change during a session.
 */

const STALE_TIME_MS = 5 * 60 * 1000; // 5 minutes

export function usePaymentMethods() {
  return useQuery({
    queryKey: ['paymentMethods'],
    queryFn: getPaymentMethods,
    staleTime: STALE_TIME_MS,
  });
}
