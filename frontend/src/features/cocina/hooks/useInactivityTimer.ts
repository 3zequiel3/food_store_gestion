import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../auth/stores/authStore';

/**
 * Auto-logout por inactividad.
 *
 * - Escucha eventos de actividad del usuario (mousemove, keydown, click, touchstart).
 * - Tras 15 minutos sin actividad, llama a `clearSession()` y redirige a `/login`.
 * - EXCLUYE la ruta `/cocina`: cuando el pathname empieza con `/cocina`, el timer
 *   no se activa (la pantalla de cocina vive encendida durante el turno).
 */
const INACTIVITY_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutos
const ACTIVITY_EVENTS = ['mousemove', 'keydown', 'click', 'touchstart'] as const;

export function useInactivityTimer() {
  const navigate = useNavigate();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const clearSessionRef = useRef(() => useAuthStore.getState().clearSession());

  useEffect(() => {
    function resetTimer() {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }

      // Excluir /cocina del auto-logout
      if (window.location.pathname.startsWith('/cocina')) {
        return;
      }

      timerRef.current = setTimeout(() => {
        clearSessionRef.current();
        navigate('/login', { replace: true });
      }, INACTIVITY_TIMEOUT_MS);
    }

    // Iniciar el timer al montar
    resetTimer();

    // Escuchar eventos de actividad
    for (const event of ACTIVITY_EVENTS) {
      window.addEventListener(event, resetTimer, { passive: true });
    }

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      for (const event of ACTIVITY_EVENTS) {
        window.removeEventListener(event, resetTimer);
      }
    };
  }, [navigate]);
}
