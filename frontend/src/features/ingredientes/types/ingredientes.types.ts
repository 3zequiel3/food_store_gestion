export interface IngredienteRead {
  id: number;
  nombre: string;
  es_alergeno: boolean;
}

export interface PaginatedIngredientes {
  items: IngredienteRead[];
  total: number;
  page: number;
  limit: number;
}

export interface IngredienteCreate {
  nombre: string;
  es_alergeno?: boolean;
}

export interface IngredienteUpdate {
  nombre?: string;
  es_alergeno?: boolean;
}

/** Ingrediente asignado a un producto, con flag es_removible del pivot */
export interface IngredienteAsignado {
  id: number;
  nombre: string;
  es_alergeno: boolean;
  es_removible: boolean;
}
