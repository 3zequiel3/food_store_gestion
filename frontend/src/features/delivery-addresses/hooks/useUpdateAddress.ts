import { useMutation, useQueryClient } from '@tanstack/react-query';
import { updateAddress } from '../services/deliveryAddresses.service';
import type { DireccionUpdate } from '../types/deliveryAddress.types';

export function useUpdateAddress() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: DireccionUpdate }) =>
      updateAddress(id, data),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['addresses'] });
    },
  });
}
