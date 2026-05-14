import { describe, it, expect } from 'vitest';
import { diffIngredientes } from '../diff-ingredientes';
import type { IngredienteAsignado } from '../../types/ingredientes.types';

const tomate: IngredienteAsignado = { id: 1, nombre: 'Tomate', es_alergeno: false, es_removible: true };
const lechuga: IngredienteAsignado = { id: 2, nombre: 'Lechuga', es_alergeno: false, es_removible: true };
const queso: IngredienteAsignado = { id: 3, nombre: 'Queso', es_alergeno: false, es_removible: false };

describe('diffIngredientes', () => {
  it('returns empty array when no changes', () => {
    const original = [tomate, lechuga];
    const current = [tomate, lechuga];
    const changes = diffIngredientes(original, current);
    expect(changes).toEqual([]);
  });

  it('detects added ingredient', () => {
    const original = [tomate];
    const current = [tomate, queso];
    const changes = diffIngredientes(original, current);
    expect(changes).toHaveLength(1);
    expect(changes[0]).toEqual({ type: 'add', ingrediente: queso });
  });

  it('detects removed ingredient', () => {
    const original = [tomate, lechuga];
    const current = [tomate];
    const changes = diffIngredientes(original, current);
    expect(changes).toHaveLength(1);
    expect(changes[0]).toEqual({ type: 'remove', ingrediente: lechuga });
  });

  it('detects es_removible toggle (update)', () => {
    const tomateNoRemovible = { ...tomate, es_removible: false };
    const original = [tomateNoRemovible];
    const current = [tomate];
    const changes = diffIngredientes(original, current);
    expect(changes).toHaveLength(1);
    expect(changes[0]).toEqual({ type: 'update', before: tomateNoRemovible, after: tomate });
  });

  it('handles add + remove + update in single diff', () => {
    const original = [tomate, lechuga];
    const current = [tomate, queso]; // lechuga removed, queso added
    // Also toggle tomate's es_removible
    const tomateToggled = { ...tomate, es_removible: false };
    const currentWithToggle = [tomateToggled, queso];

    const changes = diffIngredientes(original, currentWithToggle);
    expect(changes).toHaveLength(3);

    const types = changes.map((c) => c.type);
    expect(types).toContain('remove');
    expect(types).toContain('add');
    expect(types).toContain('update');
  });

  it('handles empty original (all adds)', () => {
    const original: IngredienteAsignado[] = [];
    const current = [tomate, lechuga];
    const changes = diffIngredientes(original, current);
    expect(changes).toHaveLength(2);
    expect(changes.every((c) => c.type === 'add')).toBe(true);
  });

  it('handles empty current (all removes)', () => {
    const original = [tomate, lechuga];
    const current: IngredienteAsignado[] = [];
    const changes = diffIngredientes(original, current);
    expect(changes).toHaveLength(2);
    expect(changes.every((c) => c.type === 'remove')).toBe(true);
  });

  it('ignores idempotent es_removible (same value)', () => {
    const original = [tomate];
    const current = [tomate]; // same es_removible
    const changes = diffIngredientes(original, current);
    expect(changes).toEqual([]);
  });
});
