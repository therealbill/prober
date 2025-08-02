from abc import ABC, abstractmethod
import threading
import time
import random
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
        self.consecutive_failures = 0  # Track consecutive failures for backoff
        self._running = False
        self._thread = None
        self._stop_event = Event()
        
        # Store backoff configuration
        self.backoff_base_interval = config.get("backoff_base_interval", 300)
        self.backoff_max_interval = config.get("backoff_max_interval", 3600)
        self.backoff_multiplier = config.get("backoff_multiplier", 2.0)
        self.backoff_max_failures = config.get("backoff_max_failures", 5)
        
        # Initialize circuit breaker
        self.circuit_breaker = pybreaker.CircuitBreaker(
            fail_max=config.get("circuit_breaker_failure_threshold", 5),
            reset_timeout=config.get("circuit_breaker_recovery_timeout", 60),
            name=f"{self.__class__.__name__}_breaker"
        )

    def _calculate_backoff_interval(self) -> float:
        """
        Calculate the next probe interval based on consecutive failures.
        Uses exponential backoff with jitter to prevent thundering herd.
        
        Returns:
            float: Interval in seconds for next probe attempt
        """
        if self.consecutive_failures == 0:
            # No failures, use normal interval
            return self.collection_interval
        
        # Cap failures for backoff calculation
        failures = min(self.consecutive_failures, self.backoff_max_failures)
        
        # Calculate exponential backoff: base_interval * (multiplier ^ failures)
        backoff_interval = self.backoff_base_interval * (self.backoff_multiplier ** failures)
        
        # Cap at maximum interval
        backoff_interval = min(backoff_interval, self.backoff_max_interval)
        
        # Add jitter: ±20% randomization to prevent thundering herd
        jitter = random.uniform(-0.2, 0.2)
        jittered_interval = backoff_interval * (1 + jitter)
        
        # Ensure minimum interval of 30 seconds
        return max(jittered_interval, 30.0)

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
                self.consecutive_failures += 1
                logger.warning(
                    f"{self.__class__.__name__} probe check failed. Total failures: {self.total_failures}, Consecutive: {self.consecutive_failures}"
                )
                EMAIL_PROBE_SUCCESS.labels(
                    probe=self.__class__.__name__,
                ).set(0.0)
            else:
                # Reset consecutive failures on success
                self.consecutive_failures = 0
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
            self.consecutive_failures += 1
            logger.error(f"{self.__class__.__name__} probe execution error: {str(e)}")
            EMAIL_PROBE_SUCCESS.labels(
                probe=self.__class__.__name__,
            ).set(0.0)
            return False

    def _run(self):
        """
        Internal method to run the probe in a loop with exponential backoff.
        """
        while self._running:
            self.execute()
            
            # Calculate next interval based on failures and circuit breaker state
            if self.circuit_breaker.current_state == 'open':
                # Circuit breaker is open, use normal interval
                interval = self.collection_interval
                # Reset consecutive failures when circuit breaker opens
                # (circuit breaker will handle the backoff)
                self.consecutive_failures = 0
            else:
                # Circuit breaker is closed, use backoff calculation
                interval = self._calculate_backoff_interval()
            
            # Use Event.wait() instead of time.sleep() for interruptible sleep
            if self._stop_event.wait(interval):
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
