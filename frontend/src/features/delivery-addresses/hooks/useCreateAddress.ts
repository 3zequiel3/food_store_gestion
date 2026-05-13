import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createAddress } from '../services/deliveryAddresses.service';
import type { DireccionCreate } from '../types/deliveryAddress.types';

export function useCreateAddress() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: DireccionCreate) => createAddress(data),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['addresses'] });
    },
  });
}
