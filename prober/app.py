"""
Main application class for email server probes.
"""

import threading
import time
from prometheus_client import start_http_server
from loguru import logger
from .metrics import EMAIL_PROBE_SUCCESS
from prober.probes.dns_probe import DNSMXDomainProbe, DNSMXIPProbe
from prober.probes.connectivity_probe import (
    IPPingProbe,
    HTTPPortProbe,
    HTTPSPortProbe,
    MailPortProbe,
    SMTPPortProbe,
)
from prober.probes.security_probe import (
    HTTPSCertificateProbe,
    SMTPCertificateProbe,
)
from prober.probes.mail_probe import AuthenticatedSMTPSendProbe, UnauthenticatedSMTPProbe


class EmailProbeApp:
    """
    Main application class that manages all probes and metrics.
    """

    def __init__(self, config: dict):
        """
        Initialize the application with configuration.

        Args:
            config (dict): Configuration dictionary containing all required settings
        """
        self._validate_config(config)

        # Create configs for unauthenticated SMTP probes
        smtp_unauth_config = {
            "collection_interval": config["collection_interval"],
            "server_hostname": config["server_hostname"],
            "smtp_port": config["mail_port"],  # Port 25
        }

        smtps_unauth_config = {
            "collection_interval": config["collection_interval"],
            "server_hostname": config["server_hostname"],
            "smtp_port": config["smtp_port"],  # Port 587
        }

        # Initialize all probes
        self.probes = [
            # DNS probes
            DNSMXDomainProbe(config),
            DNSMXIPProbe(config),
            
            # Connectivity probes
            IPPingProbe(config),
            
            # HTTPPortProbe(config),
            HTTPSPortProbe(config),
            MailPortProbe(config),
            SMTPPortProbe(config),
            
            # Security probes
            HTTPSCertificateProbe(config),
            # SMTPCertificateProbe(config),
            
            # Authenticated Mail probes
            # AuthenticatedSMTPSendProbe(config),
            
            # Unauthenticated SMTP probes for both ports
            UnauthenticatedSMTPProbe(smtp_unauth_config),  # Port 25
            UnauthenticatedSMTPProbe(smtps_unauth_config),  # Port 587
        ]

        self.metrics_port = config["metrics_export_port"]
        self._running = False

    def _validate_config(self, config: dict):
        """
        Validate that all required configuration is present.

        Args:
            config (dict): Configuration dictionary to validate

        Raises:
            ValueError: If any required configuration is missing
        """
        required_fields = {
            "collection_interval",
            "server_ip",
            "server_hostname",
            "mx_domain",
            "http_port",
            "https_port",
            "mail_port",
            "smtp_port",
            "smtp_username",
            "smtp_password",
            "metrics_export_port",
            "expected_ip",
        }

        missing = required_fields - set(config.keys())
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

    def start(self):
        """
        Start the application:
        1. Start Prometheus metrics server
        2. Start all probes
        """
        try:
            self._running = True
            # Start Prometheus metrics server
            start_http_server(self.metrics_port)
            logger.info(
                f"Started Prometheus metrics server on port {self.metrics_port}"
            )

            # Start all probes
            for probe in self.probes:
                probe.start_probe()
                logger.info(f"Started probe: {probe.__class__.__name__}")

        except Exception as e:
            logger.error(f"Failed to start application: {str(e)}")
            self.stop()
            raise

    def stop(self):
        """
        Stop all probes gracefully with a timeout.
        """
        if not self._running:
            return
            
        self._running = False
        logger.info("Stopping all probes...")
        
        # Stop all probes concurrently
        stop_threads: list[threading.Thread] = []
        for probe in self.probes:
            thread = threading.Thread(
                target=lambda p: p.stop_probe(),
                args=(probe,)
            )
            thread.start()
            stop_threads.append(thread)
        
        # Wait for all probes to stop with timeout
        timeout = 10  # Give probes 10 seconds to stop
        start_time = time.time()
        for thread in stop_threads:
            remaining = max(0, timeout - (time.time() - start_time))
            thread.join(timeout=remaining)
            if thread.is_alive():
                logger.warning("Some probes did not stop gracefully within timeout")
                break
                
        logger.info("All probes stopped")

    def is_running(self):
        """
        Check if the application is running.

        Returns:
            bool: True if running, False otherwise
        """
        return self._running


def main():
    """
    Main entry point for the email probe system.
    """
    import time
    from .config import load_config, config_to_dict
    
    with open('pyproject.toml','r') as fh:
        pyproject_raw = fh.readlines()
    version = next((l for l in pyproject_raw if 'version' in l))
    logger.info(f"Welcome to Prober {version}")

    # Load and validate configuration
    try:
        prober_config = load_config()
        config = config_to_dict(prober_config)
        logger.info("Configuration loaded and validated successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        exit(1)

    try:
        app = EmailProbeApp(config)
        app.start()

        # Set up signal handlers
        import signal

        def handle_signal(signum, frame):
            logger.info("Received shutdown signal")
            app.stop()
            exit(0)

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        # Keep the main thread running with interruptible sleep
        stop_event = threading.Event()
        while app.is_running() and not stop_event.wait(1):
            pass

    except Exception as e:
        logger.exception(f"Application error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
