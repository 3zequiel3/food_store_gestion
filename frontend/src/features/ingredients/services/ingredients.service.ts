import { apiClient } from '../../../api/client';
import { ENDPOINTS } from '../../../lib/constants/endpoints';

/** Ingrediente alérgeno (simplificado — solo id y nombre para el filtro) */
export interface AllergenIngrediente {
  id: number;
  nombre: string;
  es_alergeno: boolean;
}

/**
 * Servicio de ingredientes.
 * Para el filtro de alérgenos solo se necesitan los ingredientes marcados como alérgenos.
 */

/** GET /ingredientes/?es_alergeno=true — ingredientes declarados alérgenos */
export async function getAllergenIngredients(): Promise<AllergenIngrediente[]> {
  const response = await apiClient.get<AllergenIngrediente[]>(ENDPOINTS.ingredientes.list, {
    params: { es_alergeno: true },
  });
  return response.data;
}
