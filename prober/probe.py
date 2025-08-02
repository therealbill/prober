from abc import ABC, abstractmethod
import threading
import time
from threading import Event
from loguru import logger
import pybreaker
from .metrics import EMAIL_PROBE_SUCCESS


class Probe(ABC):
    """
    Abstract base class for all probes.
    Each probe is responsible for its own polling loop and metrics.
    """

    def __init__(self, config: dict):
        """
        Initialize the probe with configuration.

        Args:
            config (dict): Configuration dictionary containing collection_interval
        """
        self.collection_interval = config.get(
            "collection_interval", 300
        )  # Default 5 minutes
        self.total_failures = 0
        self._running = False
        self._thread = None
        self._stop_event = Event()
        
        # Initialize circuit breaker
        self.circuit_breaker = pybreaker.CircuitBreaker(
            fail_max=config.get("circuit_breaker_failure_threshold", 5),
            reset_timeout=config.get("circuit_breaker_recovery_timeout", 60),
            name=f"{self.__class__.__name__}_breaker"
        )

    @abstractmethod
    def _execute_check(self) -> bool:
        """
        Execute the actual probe check.
        Must be implemented by concrete probe classes.

        Returns:
            bool: True if check passes, False otherwise
        """
        pass

    def execute(self) -> bool:
        """
        Execute the probe check with circuit breaker protection.

        Returns:
            bool: True if check passes, False otherwise
        """
        try:
            # Use circuit breaker to wrap the actual check
            result = self.circuit_breaker(self._execute_check)()
            if not result:
                self.total_failures += 1
                logger.warning(
                    f"{self.__class__.__name__} probe check failed. Total failures: {self.total_failures}"
                )
                EMAIL_PROBE_SUCCESS.labels(
                    probe=self.__class__.__name__,
                ).set(0.0)
            else:
                EMAIL_PROBE_SUCCESS.labels(
                    probe=self.__class__.__name__,
                ).set(1.0)
            return result
        except pybreaker.CircuitBreakerError:
            # Circuit breaker is open, probe is temporarily disabled
            logger.warning(f"{self.__class__.__name__} circuit breaker is open, skipping probe")
            EMAIL_PROBE_SUCCESS.labels(
                probe=self.__class__.__name__,
            ).set(0.0)
            return False
        except Exception as e:
            self.total_failures += 1
            logger.error(f"{self.__class__.__name__} probe execution error: {str(e)}")
            EMAIL_PROBE_SUCCESS.labels(
                probe=self.__class__.__name__,
            ).set(0.0)
            return False

    def _run(self):
        """
        Internal method to run the probe in a loop.
        """
        while self._running:
            self.execute()
            # Use Event.wait() instead of time.sleep() for interruptible sleep
            if self._stop_event.wait(self.collection_interval):
                break

    def start_probe(self):
        """
        Start the probe's polling loop in a separate thread.
        """
        if self._thread is not None and self._thread.is_alive():
            logger.warning(f"{self.__class__.__name__} probe already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop_probe(self):
        """
        Stop the probe's polling loop.
        """
        if not self._running:
            return
            
        self._running = False
        self._stop_event.set()  # Signal the thread to stop
        
        if self._thread is not None:
            # Add timeout to prevent hanging
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logger.warning(f"{self.__class__.__name__} probe thread did not stop gracefully")
            self._thread = None
            
        self._stop_event.clear()  # Reset the event for potential future use
    
    def is_healthy(self) -> bool:
        """
        Check if probe is currently healthy (circuit breaker closed and recent success).
        
        Returns:
            bool: True if probe is healthy, False otherwise
        """
        return self.circuit_breaker.current_state == 'closed'
