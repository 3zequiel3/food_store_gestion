## 1. CartDrawer — controles de cantidad e imagen

- [x] 1.1 En `CartDrawer.tsx`: reemplazar el div placeholder de imagen por `<img>` si `item.imagen_url` existe, mantener el div gris si no
- [x] 1.2 En `CartDrawer.tsx`: agregar hook `const updateQuantity = useCartStore((s) => s.updateQuantity)` y reemplazar la línea `{item.cantidad} × $...` por controles "−  cantidad  +" que llamen a `updateQuantity`

## 2. ProductDetailPage — personalización de ingredientes

- [x] 2.1 En `ProductDetailPage.tsx`: agregar estado `const [excluidos, setExcluidos] = useState<Set<number>>(new Set())` y función toggle que agrega/quita ids del Set
- [x] 2.2 En `ProductDetailPage.tsx`: en la sección de ingredientes, renderizar checkbox para cada ingrediente con `es_removible === true`; ingredientes no removibles se muestran solo como texto (sin checkbox)
- [x] 2.3 En `ProductDetailPage.tsx`: en `handleAgregar`, construir el string `personalizacion` a partir de `excluidos` y pasarlo a `addItem`; también aplicar `Number(producto.precio)` (fix consistency con ProductCard)
