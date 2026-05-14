import { describe, expect, it } from 'vitest';
import type {
  CategoriaRead,
  ImagenRead,
  ProductoRead,
  ProductoDetail,
  ProductoCreate,
} from '../types/products.types';

describe('products.types.ts — type shape verification', () => {
  describe('CategoriaRead', () => {
    it('has padre_id (not parent_id)', () => {
      const cat: CategoriaRead = { id: 1, nombre: 'Bebidas', padre_id: null };
      expect(cat).toHaveProperty('padre_id');
      expect(cat).not.toHaveProperty('parent_id');
      expect(cat).not.toHaveProperty('slug');
    });

    it('padre_id can be null or number', () => {
      const leaf: CategoriaRead = { id: 1, nombre: 'Coca', padre_id: 5 };
      const root: CategoriaRead = { id: 5, nombre: 'Bebidas', padre_id: null };
      expect(leaf.padre_id).toBe(5);
      expect(root.padre_id).toBeNull();
    });
  });

  describe('ImagenRead', () => {
    it('has correct shape: id, url, orden, es_primaria', () => {
      const img: ImagenRead = {
        id: 1,
        url: 'https://example.com/img.jpg',
        orden: 0,
        es_primaria: true,
      };
      expect(img).toHaveProperty('id');
      expect(img).toHaveProperty('url');
      expect(img).toHaveProperty('orden');
      expect(img).toHaveProperty('es_primaria');
      expect(typeof img.id).toBe('number');
      expect(typeof img.url).toBe('string');
      expect(typeof img.orden).toBe('number');
      expect(typeof img.es_primaria).toBe('boolean');
    });
  });

  describe('ProductoRead', () => {
    it('has imagenes array', () => {
      const product: ProductoRead = {
        id: 1,
        nombre: 'Test',
        descripcion: null,
        precio: 10,
        imagen_url: null,
        disponible: true,
        stock_cantidad: 5,
        categoria_id: null,
        imagenes: [],
      };
      expect(product).toHaveProperty('imagenes');
      expect(Array.isArray(product.imagenes)).toBe(true);
    });

    it('keeps imagen_url for backward compat', () => {
      const product: ProductoRead = {
        id: 1,
        nombre: 'Test',
        descripcion: null,
        precio: 10,
        imagen_url: 'https://old.com/img.jpg',
        disponible: true,
        stock_cantidad: 5,
        categoria_id: null,
        imagenes: [],
      };
      expect(product).toHaveProperty('imagen_url');
    });
  });

  describe('ProductoDetail', () => {
    it('extends ProductoRead with categorias, ingredientes, imagenes', () => {
      const detail: ProductoDetail = {
        id: 1,
        nombre: 'Test',
        descripcion: null,
        precio: 10,
        imagen_url: null,
        disponible: true,
        stock_cantidad: 5,
        categoria_id: null,
        imagenes: [],
        categorias: [],
        ingredientes: [],
      };
      expect(detail).toHaveProperty('categorias');
      expect(detail).toHaveProperty('ingredientes');
      expect(detail).toHaveProperty('imagenes');
      expect(Array.isArray(detail.categorias)).toBe(true);
      expect(Array.isArray(detail.ingredientes)).toBe(true);
      expect(Array.isArray(detail.imagenes)).toBe(true);
    });
  });

  describe('ProductoCreate', () => {
    it('requires categoria_ids as array', () => {
      const payload: ProductoCreate = {
        nombre: 'Test',
        precio: 10,
        categoria_ids: [1, 2],
      };
      expect(payload).toHaveProperty('categoria_ids');
      expect(Array.isArray(payload.categoria_ids)).toBe(true);
    });

    it('supports optional ingrediente_ids', () => {
      const payload: ProductoCreate = {
        nombre: 'Test',
        precio: 10,
        categoria_ids: [1],
        ingrediente_ids: [{ ingrediente_id: 5, es_removible: true }],
      };
      expect(payload).toHaveProperty('ingrediente_ids');
      expect(payload.ingrediente_ids?.[0]).toHaveProperty('ingrediente_id');
      expect(payload.ingrediente_ids?.[0]).toHaveProperty('es_removible');
    });
  });
});
