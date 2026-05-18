-- Script idempotente para eliminar pedidos huérfanos en PENDIENTE sin pago aprobado
-- 
-- Un pedido "huérfano" es aquel en estado PENDIENTE que no tiene un Pago asociado
-- con mp_status='approved'. Estos pedidos quedaron colgados en el flow viejo cuando
-- el cliente cerraba el navegador antes de pagar.
--
-- Uso: Ejecutar manualmente en dev/testing. NO ejecutar automáticamente en producción.
-- Decision D7: cleanup en dev/testing manual, prod manual caso por caso.

BEGIN;

-- Log de pedidos que se van a eliminar (para auditoría)
CREATE TEMP TABLE IF NOT EXISTS orphan_orders_log AS
SELECT 
    o.id as pedido_id,
    o.usuario_id,
    o.estado_codigo,
    o.created_at,
    o.total,
    (SELECT COUNT(*) FROM order_items oi WHERE oi.pedido_id = o.id) as cantidad_items
FROM orders o
WHERE o.estado_codigo = 'PENDIENTE'
    AND NOT EXISTS (
        SELECT 1 
        FROM pagos p 
        WHERE p.pedido_id = o.id 
            AND p.mp_status = 'approved'
    );

-- Mostrar cuántos pedidos huérfanos se encontraron
DO $$
DECLARE
    orphan_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO orphan_count FROM orphan_orders_log;
    
    IF orphan_count = 0 THEN
        RAISE NOTICE 'No se encontraron pedidos huérfanos. Nada que limpiar.';
    ELSE
        RAISE NOTICE 'Se encontraron % pedidos huérfanos para eliminar:', orphan_count;
        RAISE NOTICE 'Ver tabla temporal orphan_orders_log para detalles.';
    END IF;
END $$;

-- Eliminar items de pedidos huérfanos (referencias en order_items)
DELETE FROM order_items oi
WHERE oi.pedido_id IN (
    SELECT o.id 
    FROM orders o
    WHERE o.estado_codigo = 'PENDIENTE'
        AND NOT EXISTS (
            SELECT 1 
            FROM pagos p 
            WHERE p.pedido_id = o.id 
                AND p.mp_status = 'approved'
        )
);

-- Eliminar historial de estado de pedidos huérfanos
DELETE FROM order_state_history osh
WHERE osh.pedido_id IN (
    SELECT o.id 
    FROM orders o
    WHERE o.estado_codigo = 'PENDIENTE'
        AND NOT EXISTS (
            SELECT 1 
            FROM pagos p 
            WHERE p.pedido_id = o.id 
                AND p.mp_status = 'approved'
        )
);

-- Finalmente, eliminar los pedidos huérfanos
DELETE FROM orders o
WHERE o.estado_codigo = 'PENDIENTE'
    AND NOT EXISTS (
        SELECT 1 
        FROM pagos p 
        WHERE p.pedido_id = o.id 
            AND p.mp_status = 'approved'
    );

-- Confirmar eliminación
DO $$
DECLARE
    deleted_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO deleted_count FROM orphan_orders_log;
    
    IF deleted_count > 0 THEN
        RAISE NOTICE 'Limpieza completada: % pedidos huérfanos eliminados.', deleted_count;
        RAISE NOTICE 'Detalles guardados en tabla temporal orphan_orders_log (solo para esta sesión).'
    ELSE
        RAISE NOTICE 'Limpieza completada: No había pedidos huérfanos.';
    END IF;
END $$;

COMMIT;
