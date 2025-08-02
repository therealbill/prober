"""
Main application class for email server probes.
"""

import threading
import time
import json
import psutil
import signal
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import start_http_server, generate_latest, CONTENT_TYPE_LATEST
from loguru import logger
from .metrics import EMAIL_PROBE_SUCCESS, RESOURCE_MEMORY_USAGE_MB, RESOURCE_THREAD_COUNT, RESOURCE_STATUS_INFO
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


class ProberHTTPHandler(BaseHTTPRequestHandler):
    """
    Custom HTTP handler for metrics and health endpoints.
    """
    
    def __init__(self, probes, resource_config, *args, **kwargs):
        self.probes = probes
        self.resource_config = resource_config
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests for metrics and health endpoints."""
        if self.path == '/metrics':
            self._serve_metrics()
        elif self.path == '/health':
            self._serve_health()
        else:
            self._serve_404()
    
    def _serve_metrics(self):
        """Serve Prometheus metrics."""
        try:
            metrics_output = generate_latest()
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(metrics_output)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error generating metrics: {str(e)}".encode())
    
    def _serve_health(self):
        """Serve health status with resource monitoring."""
        try:
            healthy_probes = sum(1 for probe in self.probes if probe.is_healthy())
            total_probes = len(self.probes)
            health_percentage = healthy_probes / total_probes if total_probes > 0 else 0
            
            # Get resource status
            resource_status = self._get_resource_status()
            
            # Overall health considers both probes and resources
            probe_healthy = health_percentage >= 0.5  # 50% threshold
            resource_healthy = resource_status["status"] != "warning"
            is_healthy = probe_healthy and resource_healthy
            
            response = {
                "status": "healthy" if is_healthy else "unhealthy",
                "healthy_probes": healthy_probes,
                "total_probes": total_probes,
                "health_percentage": round(health_percentage, 2),
                "resources": resource_status
            }
            
            status_code = 200 if is_healthy else 503
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error generating health status: {str(e)}".encode())
    
    def _serve_404(self):
        """Serve 404 response."""
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")
    
    def _get_resource_status(self):
        """Get current resource status and warnings."""
        if not self.resource_config.get("resource_check_enabled", True):
            return {"status": "disabled", "message": "Resource monitoring disabled"}
        
        try:
            # Get current process info
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            thread_count = threading.active_count()
            
            # Check against warning thresholds
            memory_warning = self.resource_config.get("resource_memory_warning_mb", 256)
            thread_warning = self.resource_config.get("resource_thread_warning_count", 50)
            
            warnings = []
            if memory_mb > memory_warning:
                warnings.append(f"Memory usage ({memory_mb:.1f}MB) exceeds warning threshold ({memory_warning}MB)")
            
            if thread_count > thread_warning:
                warnings.append(f"Thread count ({thread_count}) exceeds warning threshold ({thread_warning})")
            
            status = "warning" if warnings else "ok"
            
            return {
                "status": status,
                "memory_mb": round(memory_mb, 1),
                "thread_count": thread_count,
                "warnings": warnings,
                "thresholds": {
                    "memory_warning_mb": memory_warning,
                    "thread_warning_count": thread_warning
                }
            }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to get resource status: {str(e)}"
            }

    def log_message(self, format, *args):
        """Override to use loguru instead of default logging."""
        logger.debug(f"HTTP {format % args}")


def create_handler_class(probes, resource_config):
    """Create a handler class with probes and resource config bound to it."""
    class BoundHandler(ProberHTTPHandler):
        def __init__(self, *args, **kwargs):
            self.probes = probes
            self.resource_config = resource_config
            BaseHTTPRequestHandler.__init__(self, *args, **kwargs)
    return BoundHandler


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
        self.config = config
        self.resource_monitor_thread = None
        self._shutdown_event = threading.Event()

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
        self._http_server = None
        self._http_thread = None

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
            "circuit_breaker_failure_threshold",
            "circuit_breaker_recovery_timeout",
        }

        missing = required_fields - set(config.keys())
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

    def start(self):
        """
        Start the application:
        1. Start custom HTTP server for metrics and health
        2. Start all probes
        """
        try:
            self._running = True
            
            # Start resource monitoring if enabled
            if self.config.get("resource_check_enabled", True):
                self._start_resource_monitoring()
            
            # Start custom HTTP server for metrics and health endpoints
            handler_class = create_handler_class(self.probes, self.config)
            self._http_server = HTTPServer(('', self.metrics_port), handler_class)
            self._http_thread = threading.Thread(target=self._http_server.serve_forever, daemon=True)
            self._http_thread.start()
            logger.info(
                f"Started HTTP server on port {self.metrics_port} (metrics: /metrics, health: /health)"
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
        Stop all probes and HTTP server gracefully with a timeout.
        """
        if not self._running:
            return
            
        self._running = False
        logger.info("Stopping application...")
        
        # Signal shutdown event
        self._shutdown_event.set()
        
        # Stop resource monitoring
        if self.resource_monitor_thread:
            logger.info("Stopping resource monitoring...")
            self.resource_monitor_thread.join(timeout=5)
            if self.resource_monitor_thread.is_alive():
                logger.warning("Resource monitoring thread did not stop gracefully")
        
        # Stop HTTP server
        if self._http_server:
            logger.info("Stopping HTTP server...")
            self._http_server.shutdown()
            if self._http_thread:
                self._http_thread.join(timeout=5)
                if self._http_thread.is_alive():
                    logger.warning("HTTP server thread did not stop gracefully")
        
        # Stop all probes concurrently
        logger.info("Stopping all probes...")
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
                
        logger.info("Application stopped")

    def _start_resource_monitoring(self):
        """Start the resource monitoring thread."""
        self.resource_monitor_thread = threading.Thread(
            target=self._resource_monitor_loop, 
            daemon=True,
            name="ResourceMonitor"
        )
        self.resource_monitor_thread.start()
        logger.info("Started resource monitoring")

    def _resource_monitor_loop(self):
        """Resource monitoring loop that runs in a separate thread."""
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Get current process info
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    thread_count = threading.active_count()
                    
                    # Update metrics
                    RESOURCE_MEMORY_USAGE_MB.set(memory_mb)
                    RESOURCE_THREAD_COUNT.set(thread_count)
                    
                    # Check for warnings
                    memory_warning = self.config.get("resource_memory_warning_mb", 256)
                    thread_warning = self.config.get("resource_thread_warning_count", 50)
                    
                    warnings = []
                    if memory_mb > memory_warning:
                        warnings.append(f"Memory usage high: {memory_mb:.1f}MB > {memory_warning}MB")
                    if thread_count > thread_warning:
                        warnings.append(f"Thread count high: {thread_count} > {thread_warning}")
                    
                    # Update status info
                    status = "warning" if warnings else "ok"
                    RESOURCE_STATUS_INFO.info({
                        "status": status,
                        "memory_mb": str(round(memory_mb, 1)),
                        "thread_count": str(thread_count),
                        "warnings": "; ".join(warnings) if warnings else "none"
                    })
                    
                    # Log warnings if any
                    if warnings and self.config.get("enable_enhanced_logging", True):
                        for warning in warnings:
                            logger.warning(f"Resource monitoring: {warning}")
                    
                except Exception as e:
                    logger.error(f"Error in resource monitoring: {str(e)}")
                
                # Wait 30 seconds or until shutdown signal
                if self._shutdown_event.wait(30):
                    break
                    
        except Exception as e:
            logger.error(f"Resource monitoring loop failed: {str(e)}")

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
