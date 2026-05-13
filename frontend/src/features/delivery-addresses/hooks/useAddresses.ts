import { useQuery } from '@tanstack/react-query';
import { getAddresses } from '../services/deliveryAddresses.service';

export function useAddresses() {
  return useQuery({
    queryKey: ['addresses'],
    queryFn: getAddresses,
  });
}
