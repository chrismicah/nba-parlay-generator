import pytest
from tools.data_fetcher_tool import DataSourceManager, DataUnavailableError
import requests

def test_datasource_manager_fallback(monkeypatch):
    # Primary source raises Timeout
    def primary_source(*args, **kwargs):
        raise requests.exceptions.Timeout("Timeout!")

    # Fallback source returns dummy data
    fallback_data = {"data": [], "source": "fallback"}
    def fallback_source(*args, **kwargs):
        return fallback_data

    manager = DataSourceManager([primary_source, fallback_source])
    result = manager.get("dummy_arg")
    assert result == fallback_data

    # Primary source raises HTTPError
    def primary_source_http_error(*args, **kwargs):
        raise requests.exceptions.HTTPError("HTTP error!")

    manager = DataSourceManager([primary_source_http_error, fallback_source])
    result = manager.get("dummy_arg")
    assert result == fallback_data

    # If all sources fail, DataUnavailableError is raised
    manager = DataSourceManager([primary_source, primary_source])
    with pytest.raises(DataUnavailableError):
        manager.get("dummy_arg") 