"""
Configuration management for the email probe system.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from loguru import logger
import ipaddress
from typing import Dict, Any


class ProberConfig(BaseSettings):
    """Main configuration model for the email probe system."""
    
    # Probe timing
    collection_interval: int = Field(
        default=300,
        description="Probe collection interval in seconds",
        ge=30,  # Minimum 30 seconds
        le=3600,  # Maximum 1 hour
        validation_alias='PROBE_COLLECTION_INTERVAL'
    )
    
    # Server connection details
    server_ip: str = Field(
        description="Email server IP address for ping tests",
        validation_alias='EMAIL_SERVER_IP'
    )
    server_hostname: str = Field(
        description="Email server hostname for connection tests",
        validation_alias='EMAIL_SERVER_HOSTNAME'
    )
    
    # DNS configuration
    mx_domain: str = Field(
        description="Domain to check MX records for",
        validation_alias='EMAIL_MX_DOMAIN'
    )
    expected_ip: str = Field(
        description="Expected IP address for MX record validation",
        validation_alias='EMAIL_EXPECTED_MX_IP'
    )
    
    # Port configuration
    http_port: int = Field(
        default=80, 
        ge=1, 
        le=65535,
        validation_alias='EMAIL_SERVER_HTTP_PORT'
    )
    https_port: int = Field(
        default=443, 
        ge=1, 
        le=65535,
        validation_alias='EMAIL_SERVER_HTTPS_PORT'
    )
    mail_port: int = Field(
        default=25, 
        ge=1, 
        le=65535,
        validation_alias='EMAIL_SERVER_SMTP_PORT'
    )
    smtp_port: int = Field(
        default=587, 
        ge=1, 
        le=65535,
        validation_alias='EMAIL_SERVER_SMTP_SECURE_PORT'
    )
    
    # SMTP authentication
    smtp_username: str = Field(
        description="SMTP username for authenticated tests",
        validation_alias='EMAIL_SMTP_USERNAME'
    )
    smtp_password: str = Field(
        description="SMTP password for authenticated tests",
        validation_alias='EMAIL_SMTP_PASSWORD'
    )
    
    # Metrics configuration
    metrics_export_port: int = Field(
        default=9101,
        description="Port for Prometheus metrics export",
        ge=1024,
        le=65535,
        validation_alias='METRICS_EXPORT_PORT'
    )
    
    # Validation methods
    @field_validator('server_ip')
    @classmethod
    def validate_server_ip(cls, v: str) -> str:
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('server_ip must be a valid IP address')
    
    @field_validator('expected_ip')
    @classmethod
    def validate_expected_ip(cls, v: str) -> str:
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('expected_ip must be a valid IP address')
    
    @field_validator('mx_domain', 'server_hostname')
    @classmethod
    def validate_hostnames(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError('Hostname cannot be empty')
        return v.strip()
    
    @field_validator('smtp_username', 'smtp_password')
    @classmethod
    def validate_credentials(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError('SMTP credentials cannot be empty')
        return v.strip()
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        validate_by_name=True,  # Allow field names
        validate_by_alias=True  # Allow aliases (env vars)
    )


def load_config() -> ProberConfig:
    """
    Load and validate configuration from environment variables.
    
    Returns:
        ProberConfig: Validated configuration object
        
    Raises:
        ValueError: If configuration validation fails
    """
    try:
        return ProberConfig()
    except Exception as e:
        # Enhanced error messaging
        error_msg = f"Configuration validation failed: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)


def config_to_dict(config: ProberConfig) -> Dict[str, Any]:
    """
    Convert ProberConfig to dictionary for backward compatibility.
    
    Args:
        config: ProberConfig instance
        
    Returns:
        Dict containing configuration values
    """
    return config.model_dump()