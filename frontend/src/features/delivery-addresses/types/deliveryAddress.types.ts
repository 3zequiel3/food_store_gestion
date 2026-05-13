export interface DireccionRead {
  id: number;
  usuario_id: number;
  calle: string;
  numero: string;
  piso_depto: string | null;
  ciudad: string;
  codigo_postal: string;
  referencia: string | null;
  es_principal: boolean;
}

export interface DireccionCreate {
  calle: string;
  numero: string;
  piso_depto?: string;
  ciudad: string;
  codigo_postal: string;
  referencia?: string;
}

export type DireccionUpdate = Partial<DireccionCreate>;
