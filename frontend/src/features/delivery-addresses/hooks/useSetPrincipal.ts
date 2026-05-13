import { useMutation, useQueryClient } from '@tanstack/react-query';
import { setPrincipal } from '../services/deliveryAddresses.service';

export function useSetPrincipal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => setPrincipal(id),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['addresses'] });
    },
  });
}
