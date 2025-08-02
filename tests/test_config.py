"""
Tests for configuration management.
"""

import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError

from prober.config import ProberConfig, load_config, config_to_dict


class TestProberConfig:
    """Test cases for ProberConfig model."""
    
    def test_valid_config(self):
        """Test configuration with all valid values."""
        config_data = {
            'collection_interval': 300,
            'server_ip': '192.168.1.1',
            'server_hostname': 'mail.example.com',
            'mx_domain': 'example.com',
            'expected_ip': '192.168.1.1',
            'http_port': 80,
            'https_port': 443,
            'mail_port': 25,
            'smtp_port': 587,
            'smtp_username': 'testuser',
            'smtp_password': 'testpass',
            'metrics_export_port': 9101,
        }
        
        config = ProberConfig(**config_data)
        assert config.collection_interval == 300
        assert config.server_ip == '192.168.1.1'
        assert config.server_hostname == 'mail.example.com'
    
    def test_default_values(self):
        """Test that default values are applied correctly."""
        config_data = {
            'server_ip': '192.168.1.1',
            'server_hostname': 'mail.example.com',
            'mx_domain': 'example.com',
            'expected_ip': '192.168.1.1',
            'smtp_username': 'testuser',
            'smtp_password': 'testpass',
        }
        
        config = ProberConfig(**config_data)
        assert config.collection_interval == 300  # default
        assert config.http_port == 80  # default
        assert config.https_port == 443  # default
        assert config.mail_port == 25  # default
        assert config.smtp_port == 587  # default
        assert config.metrics_export_port == 9101  # default
    
    def test_invalid_ip_addresses(self):
        """Test validation of IP address fields."""
        config_data = {
            'server_ip': 'invalid-ip',
            'server_hostname': 'mail.example.com',
            'mx_domain': 'example.com',
            'expected_ip': '192.168.1.1',
            'smtp_username': 'testuser',
            'smtp_password': 'testpass',
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ProberConfig(**config_data)
        
        assert 'server_ip must be a valid IP address' in str(exc_info.value)
    
    def test_invalid_expected_ip(self):
        """Test validation of expected_ip field."""
        config_data = {
            'server_ip': '192.168.1.1',
            'server_hostname': 'mail.example.com',
            'mx_domain': 'example.com',
            'expected_ip': 'not-an-ip',
            'smtp_username': 'testuser',
            'smtp_password': 'testpass',
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ProberConfig(**config_data)
        
        assert 'expected_ip must be a valid IP address' in str(exc_info.value)
    
    def test_empty_hostname_validation(self):
        """Test validation of hostname fields."""
        config_data = {
            'server_ip': '192.168.1.1',
            'server_hostname': '',  # Empty hostname
            'mx_domain': 'example.com',
            'expected_ip': '192.168.1.1',
            'smtp_username': 'testuser',
            'smtp_password': 'testpass',
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ProberConfig(**config_data)
        
        assert 'Hostname cannot be empty' in str(exc_info.value)
    
    def test_empty_mx_domain_validation(self):
        """Test validation of mx_domain field."""
        config_data = {
            'server_ip': '192.168.1.1',
            'server_hostname': 'mail.example.com',
            'mx_domain': '   ',  # Whitespace only
            'expected_ip': '192.168.1.1',
            'smtp_username': 'testuser',
            'smtp_password': 'testpass',
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ProberConfig(**config_data)
        
        assert 'Hostname cannot be empty' in str(exc_info.value)
    
    def test_empty_credentials_validation(self):
        """Test validation of SMTP credentials."""
        config_data = {
            'server_ip': '192.168.1.1',
            'server_hostname': 'mail.example.com',
            'mx_domain': 'example.com',
            'expected_ip': '192.168.1.1',
            'smtp_username': '',  # Empty username
            'smtp_password': 'testpass',
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ProberConfig(**config_data)
        
        assert 'SMTP credentials cannot be empty' in str(exc_info.value)
    
    def test_port_range_validation(self):
        """Test validation of port number ranges."""
        config_data = {
            'server_ip': '192.168.1.1',
            'server_hostname': 'mail.example.com',
            'mx_domain': 'example.com',
            'expected_ip': '192.168.1.1',
            'smtp_username': 'testuser',
            'smtp_password': 'testpass',
            'http_port': 70000,  # Invalid port number
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ProberConfig(**config_data)
        
        assert 'less than or equal to 65535' in str(exc_info.value)
    
    def test_collection_interval_validation(self):
        """Test validation of collection interval bounds."""
        config_data = {
            'server_ip': '192.168.1.1',
            'server_hostname': 'mail.example.com',
            'mx_domain': 'example.com',
            'expected_ip': '192.168.1.1',
            'smtp_username': 'testuser',
            'smtp_password': 'testpass',
            'collection_interval': 10,  # Too low
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ProberConfig(**config_data)
        
        assert 'greater than or equal to 30' in str(exc_info.value)
    
    def test_metrics_port_minimum(self):
        """Test validation of metrics port minimum value."""
        config_data = {
            'server_ip': '192.168.1.1',
            'server_hostname': 'mail.example.com',
            'mx_domain': 'example.com',
            'expected_ip': '192.168.1.1',
            'smtp_username': 'testuser',
            'smtp_password': 'testpass',
            'metrics_export_port': 500,  # Below 1024
        }
        
        with pytest.raises(ValidationError) as exc_info:
            ProberConfig(**config_data)
        
        assert 'greater than or equal to 1024' in str(exc_info.value)


class TestConfigLoading:
    """Test cases for configuration loading functions."""
    
    @patch.dict(os.environ, {
        'PROBE_COLLECTION_INTERVAL': '600',
        'EMAIL_SERVER_IP': '10.0.0.1',
        'EMAIL_SERVER_HOSTNAME': 'test.example.com',
        'EMAIL_MX_DOMAIN': 'example.com',
        'EMAIL_EXPECTED_MX_IP': '10.0.0.1',
        'EMAIL_SERVER_HTTP_PORT': '8080',
        'EMAIL_SERVER_HTTPS_PORT': '8443',
        'EMAIL_SERVER_SMTP_PORT': '2525',
        'EMAIL_SERVER_SMTP_SECURE_PORT': '5875',
        'EMAIL_SMTP_USERNAME': 'testuser',
        'EMAIL_SMTP_PASSWORD': 'testpass',
        'METRICS_EXPORT_PORT': '9102',
    })
    def test_load_config_from_environment(self):
        """Test loading configuration from environment variables."""
        config = load_config()
        
        assert config.collection_interval == 600
        assert config.server_ip == '10.0.0.1'
        assert config.server_hostname == 'test.example.com'
        assert config.mx_domain == 'example.com'
        assert config.expected_ip == '10.0.0.1'
        assert config.http_port == 8080
        assert config.https_port == 8443
        assert config.mail_port == 2525
        assert config.smtp_port == 5875
        assert config.smtp_username == 'testuser'
        assert config.smtp_password == 'testpass'
        assert config.metrics_export_port == 9102
    
    @patch.dict(os.environ, {
        'EMAIL_SERVER_IP': 'invalid-ip',
        'EMAIL_SERVER_HOSTNAME': 'test.example.com',
        'EMAIL_MX_DOMAIN': 'example.com',
        'EMAIL_EXPECTED_MX_IP': '10.0.0.1',
        'EMAIL_SMTP_USERNAME': 'testuser',
        'EMAIL_SMTP_PASSWORD': 'testpass',
    })
    def test_load_config_validation_error(self):
        """Test that load_config raises ValueError on validation errors."""
        with pytest.raises(ValueError) as exc_info:
            load_config()
        
        assert 'Configuration validation failed' in str(exc_info.value)
    
    @patch.dict(os.environ, {
        'EMAIL_SERVER_IP': '192.168.1.1',
        'EMAIL_SERVER_HOSTNAME': 'mail.example.com',
        'EMAIL_MX_DOMAIN': 'example.com',
        'EMAIL_EXPECTED_MX_IP': '192.168.1.1',
        'EMAIL_SMTP_USERNAME': 'testuser',
        'EMAIL_SMTP_PASSWORD': 'testpass',
    })
    def test_config_to_dict(self):
        """Test converting ProberConfig to dictionary."""
        config = load_config()
        config_dict = config_to_dict(config)
        
        assert isinstance(config_dict, dict)
        assert config_dict['server_ip'] == '192.168.1.1'
        assert config_dict['server_hostname'] == 'mail.example.com'
        assert config_dict['collection_interval'] == 300  # default value
    
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_required_fields(self):
        """Test behavior when required environment variables are missing."""
        with pytest.raises(ValueError) as exc_info:
            load_config()
        
        assert 'Configuration validation failed' in str(exc_info.value)


if __name__ == '__main__':
    pytest.main([__file__])