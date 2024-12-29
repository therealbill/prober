"""
Connectivity probe implementations for checking server reachability.
"""

import socket
import subprocess
import platform
from prober.probe import Probe
from loguru import logger


class IPPingProbe(Probe):
    """
    Probe that checks if a server IP is pingable.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.server_ip = config.get("server_ip")
        if not self.server_ip:
            raise ValueError("server_ip must be specified in config")

    def _get_ping_command(self) -> list:
        """Get the appropriate ping command for the current OS."""
        if platform.system().lower() == "windows":
            return ["ping", "-n", "1", "-w", "1000", self.server_ip]
        return ["ping", "-c", "1", "-W", "1", self.server_ip]

    def _execute_check(self) -> bool:
        """
        Check if the server IP responds to ping.

        Returns:
            bool: True if ping succeeds, False otherwise
        """
        try:
            cmd = self._get_ping_command()
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,  # Don't raise on non-zero exit
            )
            return result.returncode == 0

        except subprocess.SubprocessError as e:
            logger.error(f"Error executing ping command: {self.server_ip} {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in ping check: {self.server_ip} {str(e)}")
            return False


class PortProbe(Probe):
    """
    Base class for probes that check port connectivity.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.server_hostname = config.get("server_hostname")
        if not self.server_hostname:
            raise ValueError("server_hostname must be specified in config")
        self.port = self._get_port_from_config(config)

    def _get_port_from_config(self, config: dict) -> int:
        """
        Get the port number from config. Must be implemented by subclasses.

        Args:
            config (dict): Configuration dictionary

        Returns:
            int: Port number to check
        """
        raise NotImplementedError("Subclasses must implement _get_port_from_config")

    def _execute_check(self) -> bool:
        """
        Check if the specified port is open and accepting connections.

        Returns:
            bool: True if port is open, False otherwise
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 second timeout

        try:
            sock.connect((self.server_hostname, self.port))
            logger.success(
                f"Probe Success: Port Check on {self.server_hostname}:{self.port}"
            )
            return True
        except socket.error as e:
            logger.warning(
                f"Failed to connect to {self.server_hostname}:{self.port} - {str(e)}"
            )
            return False
        finally:
            sock.close()


class HTTPPortProbe(PortProbe):
    """Probe that checks HTTP port (80) connectivity."""

    def _get_port_from_config(self, config: dict) -> int:
        port = config.get("http_port")
        if not port:
            raise ValueError("http_port must be specified in config")
        return port


class HTTPSPortProbe(PortProbe):
    """Probe that checks HTTPS port (443) connectivity."""

    def _get_port_from_config(self, config: dict) -> int:
        port = config.get("https_port")
        if not port:
            raise ValueError("https_port must be specified in config")
        return port


class MailPortProbe(PortProbe):
    """Probe that checks mail port (25) connectivity."""

    def _get_port_from_config(self, config: dict) -> int:
        port = config.get("mail_port")
        if not port:
            raise ValueError("mail_port must be specified in config")
        return port


class SMTPPortProbe(PortProbe):
    """Probe that checks SMTP port (587) connectivity."""

    def _get_port_from_config(self, config: dict) -> int:
        port = config.get("smtp_port")
        if not port:
            raise ValueError("smtp_port must be specified in config")
        return port
