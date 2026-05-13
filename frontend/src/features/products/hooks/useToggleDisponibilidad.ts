import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { toggleDisponibilidad } from '../services/admin-products.service';

export function useToggleDisponibilidad() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => toggleDisponibilidad(id),
    onSuccess() {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
    onError() {
      toast.error('Error al cambiar disponibilidad');
    },
  });
}
