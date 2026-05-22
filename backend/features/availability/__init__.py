# features/availability — ingredient kitchen-availability domain (D6, Phase 6).
#
# Responsibilities:
#   - HistorialDisponibilidadIngrediente ORM model (append-on-report / close-on-resolve).
#   - IngredientAvailabilityService: report + resolve UoW operations.
#   - Open-shortage + resolved-history queries.
#   - Admin REST endpoints (list Faltantes + resolve).
#
# Transport (websocket) stays in features/websocket — this module is persistence + domain only.
