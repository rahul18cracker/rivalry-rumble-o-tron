"""Unit tests for configuration management."""

import os
from unittest.mock import patch

import pytest

from src.config import Config, get_config


@pytest.mark.unit
class TestConfig:
    def test_config_loads(self):
        config = get_config()
        assert config is not None

    def test_config_has_defaults(self):
        config = Config()
        assert config.model_name == "claude-sonnet-4-20250514"
        assert config.model_temperature == 0.0
        assert len(config.default_companies) == 3

    def test_config_default_companies(self):
        config = Config()
        assert "DataDog" in config.default_companies
        assert "Dynatrace" in config.default_companies

    def test_config_loads_api_keys_from_env(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key", "TAVILY_API_KEY": "tav-key"}):
            config = Config()
            assert config.anthropic_api_key == "test-key"
            assert config.tavily_api_key == "tav-key"

    def test_config_validates_missing_keys(self):
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            # Force empty keys regardless of .env file
            config.anthropic_api_key = ""
            config.tavily_api_key = ""
            errors = config.validate()
            assert "ANTHROPIC_API_KEY not set" in errors
            assert "TAVILY_API_KEY not set" in errors

    def test_config_validates_no_errors_when_present(self):
        config = Config()
        config.anthropic_api_key = "present"
        config.tavily_api_key = "present"
        errors = config.validate()
        assert errors == []

    def test_ticker_mapping_known_companies(self):
        config = Config()
        assert config.get_ticker("DataDog") == "DDOG"
        assert config.get_ticker("Dynatrace") == "DT"
        assert config.get_ticker("Cisco") == "CSCO"
        assert config.get_ticker("Splunk") == "CSCO"
        assert config.get_ticker("AppDynamics") == "CSCO"

    def test_ticker_mapping_unknown_company(self):
        config = Config()
        assert config.get_ticker("UnknownCompany") is None
