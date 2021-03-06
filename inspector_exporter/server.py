import os
import logging
import time
import sys
import signal
import traceback

from pythonjsonlogger import jsonlogger
from prometheus_client import start_http_server, Gauge
from prometheus_client.core import REGISTRY
from inspector_exporter.collector import InspectorMetricsCollector


def config_from_env():
    config = {}
    config["port"] = int(os.getenv("APP_PORT", 9000))
    config["host"] = os.getenv("APP_HOST", "0.0.0.0")
    config["log_level"] = os.getenv("LOG_LEVEL", "INFO")
    config["account_id"] = os.getenv("AWS_ACCOUNT_ID", None)
    config["refresh_interval"] = int(os.getenv("CACHE_REFRESH_INTERVAL", 1800))

    return config


def setup_logging(log_level):
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logHandler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)


def main(config):
    try:
        shutdown = False

        # Setup logging
        setup_logging(config["log_level"])
        logger = logging.getLogger()

        # Register signal handler
        def _on_sigterm(signal, frame):
            logging.getLogger().warning("exporter is shutting down")
            nonlocal shutdown
            shutdown = True

        signal.signal(signal.SIGINT, _on_sigterm)
        signal.signal(signal.SIGTERM, _on_sigterm)

        # Set the up metric value, which will be steady to 1 for the entire app lifecycle
        upMetric = Gauge(
            "aws_inspector_exporter_up",
            "always 1 - can by used to check if it's running",
        )

        upMetric.set(1)

        # Register our custom collector
        logger.warning("collecting initial metrics")
        inspector_collector = InspectorMetricsCollector(config["account_id"])
        REGISTRY.register(inspector_collector)

        # Start server
        start_http_server(config["port"], config["host"])
        logger.warning(
            f"exporter listening on http://{config['host']}:{config['port']}/"
        )

        logger.info(
            f"caches will be refreshed every {config['refresh_interval']} seconds"
        )
        loop_count = 0
        while not shutdown:
            if loop_count == 0:
                inspector_collector.refresh_caches()

            loop_count += 1
            time.sleep(1)

            # reset loop every refresh_interval seconds
            if loop_count >= config["refresh_interval"]:
                loop_count = 0

        logger.info("exporter has shutdown")
    except Exception:
        logger.exception(f"Uncaught Exception: {traceback.format_exc()}")
        sys.exit(1)


def run():
    main(config_from_env())


if __name__ == "__main__":
    run()
