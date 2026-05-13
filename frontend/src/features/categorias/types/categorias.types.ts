export interface CategoriaRead {
  id: number;
  nombre: string;
  padre_id: number | null;
}

export interface CategoriaTreeNode extends CategoriaRead {
  subcategorias: CategoriaTreeNode[];
}

export interface CategoriaCreate {
  nombre: string;
  padre_id?: number | null;
}

export interface CategoriaUpdate {
  nombre?: string;
  padre_id?: number | null;
}
