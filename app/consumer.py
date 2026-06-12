"""Kafka consumer worker: incidents.raw → analyze_log → SavedIncident."""

import logging
import os
import time

from confluent_kafka import Consumer, KafkaError, Producer
from sqlmodel import Session

from app.database import create_db_and_tables, engine
from app.events.producer import kafka_configured
from app.events.schema import IncidentEvent
from app.events.user_resolution import resolve_incident_user_id
from app.incident_save import process_incident_event
from app.retrieval import warmup_playbook_index

logger = logging.getLogger(__name__)

_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "").strip()
_TOPIC = os.getenv("KAFKA_TOPIC_INCIDENTS", "incidents.raw").strip() or "incidents.raw"
_DLQ_TOPIC = os.getenv("KAFKA_TOPIC_DLQ", "incidents.dlq").strip() or "incidents.dlq"
_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "debugpilot-incidents")
_MAX_RETRIES = int(os.getenv("KAFKA_CONSUMER_MAX_RETRIES", "3"))


def _publish_dlq(event: IncidentEvent, error: str) -> None:
    if not _BOOTSTRAP:
        return
    producer = Producer({"bootstrap.servers": _BOOTSTRAP})
    payload = event.model_dump()
    payload["dlq_error"] = error
    producer.produce(
        _DLQ_TOPIC,
        key=event.external_id.encode("utf-8"),
        value=json_bytes(payload),
    )
    producer.flush(5)


def json_bytes(payload: dict) -> bytes:
    import json

    return json.dumps(payload).encode("utf-8")


def _process_message(payload: bytes) -> None:
    event = IncidentEvent.from_json_bytes(payload)
    actor = event.metadata.get("actor")
    actor_github_id = event.metadata.get("actor_github_id")
    if actor_github_id is not None:
        try:
            actor_github_id = int(actor_github_id)
        except (TypeError, ValueError):
            actor_github_id = None
    last_error: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with Session(engine) as session:
                user_id = resolve_incident_user_id(
                    session,
                    actor=actor,
                    actor_github_id=actor_github_id,
                )
                saved = process_incident_event(session, event, user_id)
                if saved:
                    logger.info(
                        "Processed incident event %s → saved incident %s",
                        event.external_id,
                        saved.id,
                    )
                return
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Attempt %s/%s failed for %s: %s",
                attempt,
                _MAX_RETRIES,
                event.external_id,
                exc,
            )
            time.sleep(min(2**attempt, 30))

    if last_error is not None:
        _publish_dlq(event, str(last_error))
        raise last_error


def run_consumer() -> None:
    if not kafka_configured():
        raise SystemExit("KAFKA_BOOTSTRAP_SERVERS is required for the consumer")

    logging.basicConfig(level=logging.INFO)
    create_db_and_tables()
    warmup_playbook_index()

    consumer = Consumer(
        {
            "bootstrap.servers": _BOOTSTRAP,
            "group.id": _GROUP,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([_TOPIC])
    logger.info("Consumer subscribed to %s (group=%s)", _TOPIC, _GROUP)

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise RuntimeError(msg.error())

            try:
                _process_message(msg.value())
                consumer.commit(message=msg, asynchronous=False)
            except Exception:
                logger.exception("Failed to process message at offset %s", msg.offset())
    finally:
        consumer.close()


if __name__ == "__main__":
    run_consumer()
