import pytest

from inspector_exporter.collector import InspectorMetricsCollector


def test_collector_without_values():
    with pytest.raises(TypeError):
        InspectorMetricsCollector()
