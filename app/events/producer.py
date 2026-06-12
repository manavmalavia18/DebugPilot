import logging
import os

from app.events.schema import IncidentEvent

logger = logging.getLogger(__name__)

_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "").strip()
_TOPIC = os.getenv("KAFKA_TOPIC_INCIDENTS", "incidents.raw").strip() or "incidents.raw"
_producer = None


def kafka_configured() -> bool:
    return bool(_BOOTSTRAP)


def _get_producer():
    global _producer
    if _producer is not None:
        return _producer
    if not _BOOTSTRAP:
        return None

    from confluent_kafka import Producer

    _producer = Producer({"bootstrap.servers": _BOOTSTRAP})
    return _producer


def publish_incident_event(event: IncidentEvent) -> bool:
    """Publish an incident event. Returns True when sent, False when Kafka is disabled."""
    producer = _get_producer()
    if producer is None:
        logger.debug("Kafka not configured; skipping publish for %s", event.external_id)
        return False

    def _delivery(err, _msg):
        if err is not None:
            logger.error("Kafka delivery failed for %s: %s", event.external_id, err)

    producer.produce(
        _TOPIC,
        key=event.external_id.encode("utf-8"),
        value=event.to_json_bytes(),
        callback=_delivery,
    )
    producer.poll(0)
    producer.flush(5)
    return True
