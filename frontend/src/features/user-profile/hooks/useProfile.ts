import { useQuery } from '@tanstack/react-query';
import { getProfile } from '../services/userProfile.service';

export function useProfile() {
  return useQuery({
    queryKey: ['user-profile'],
    queryFn: getProfile,
  });
}
