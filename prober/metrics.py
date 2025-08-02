from prometheus_client import Gauge, Info

# Gauge for probe success/failure with labels for probe name and error type
EMAIL_PROBE_SUCCESS = Gauge(
    'email_probe_success_count',
    'Count of probe execution successes and failures',
    ['probe', 'error_type']
)

# Resource monitoring metrics
RESOURCE_MEMORY_USAGE_MB = Gauge(
    'email_prober_memory_usage_mb',
    'Current memory usage in megabytes'
)

RESOURCE_THREAD_COUNT = Gauge(
    'email_prober_thread_count',
    'Current number of active threads'
)

RESOURCE_STATUS_INFO = Info(
    'email_prober_resource_status',
    'Resource status information and warnings'
)
