import { useQuery } from '@tanstack/react-query';
import { listUsers } from '../services/admin-users.service';
import type { AdminUsersFilters } from '../types/admin-users.types';

export function useAdminUsers(filters: AdminUsersFilters) {
  return useQuery({
    queryKey: ['admin-users', filters],
    queryFn: () => listUsers(filters),
    staleTime: 30_000,
  });
}
