"""Central notification point for hot routing configuration changes."""

from threading import RLock

from core.event_bus import event_bus
from core.events import ProfileConfigurationChangedEvent


class RoutingConfigurationService:
    def __init__(self):
        self.lock = RLock()
        self._generation = 0

    @property
    def generation(self):
        with self.lock:
            return self._generation

    def notify_changed(self, profile_id=None, area="profile"):
        with self.lock:
            self._generation += 1
            event = ProfileConfigurationChangedEvent(
                profile_id=profile_id,
                area=str(area),
            )
        try:
            event_bus.profileConfigurationChanged.emit(event)
            event_bus.dashboardRefreshRequested.emit()
        except Exception as error:
            event_bus.error(
                f"Configuración persistida, pero falló su notificación: {error}"
            )
        return self._generation


routing_configuration_service = RoutingConfigurationService()
