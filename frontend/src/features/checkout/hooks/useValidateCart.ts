import { useMutation } from '@tanstack/react-query';
import { getProduct } from '../../products/services/products.service';
import { useCartStore } from '../../cart/stores/cartStore';
import type { ValidationResult, StockIssue, PriceChange } from '../types/validation.types';

async function validateCartItems(
  items: { producto_id: number; nombre: string; cantidad: number; precio: number }[],
): Promise<ValidationResult> {
  const results = await Promise.all(items.map((item) => getProduct(item.producto_id)));

  const stockIssues: StockIssue[] = [];
  const priceChanges: PriceChange[] = [];

  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const producto = results[i];

    if (!producto.disponible || producto.stock_cantidad < item.cantidad) {
      stockIssues.push({
        producto_id: item.producto_id,
        nombre: item.nombre,
        stockDisponible: producto.stock_cantidad,
        disponible: producto.disponible,
      });
    } else if (Math.abs(Number(producto.precio) - item.precio) > 0.01) {
      priceChanges.push({
        producto_id: item.producto_id,
        nombre: item.nombre,
        precioAnterior: item.precio,
        precioNuevo: Number(producto.precio),
      });
    }
  }

  return { stockIssues, priceChanges };
}

export function useValidateCart() {
  const items = useCartStore((s) =>
    s.items.map((i) => ({
      producto_id: i.producto_id,
      nombre: i.nombre,
      cantidad: i.cantidad,
      precio: Number(i.precio),
    })),
  );

  return useMutation({
    mutationFn: () => validateCartItems(items),
  });
}
