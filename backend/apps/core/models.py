# apps.core — реэкспорт моделей из nested packages, чтобы Django
# обнаружил их через INSTALLED_APPS=['apps.core'].
# OutboxEvent живёт в apps.core.outbox.models — здесь только импорт.
from apps.core.outbox.models import OutboxEvent

__all__ = ["OutboxEvent"]
