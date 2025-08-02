# Prober Robustness Improvement Plan

This document outlines a 5-phase plan to improve the robustness and production-readiness of the email probe monitoring system.

## Implementation Order: 1 → 2 → 3 → 4 → 5

### Dependencies
- **Phase 1** provides configuration foundation for all other phases
- **Phase 2** can be implemented independently but benefits from Phase 1
- **Phase 3** integrates with Phase 2 (circuit breaker + backoff)
- **Phase 4** builds on Phase 3 (categorized errors enhance retry logic)  
- **Phase 5** can run parallel to Phase 4 but benefits from Phase 2's health system

---

## Phase 1: Configuration Validation with Pydantic
**Status**: ✅ Completed  
**Priority**: Foundation phase - implemented first  
**Estimated Effort**: 1 day (completed)

### Objective
Implement robust configuration management with proper validation using Pydantic's native environment variable handling

### Implementation Tasks (Completed)
1. **Add Pydantic dependencies**
   - [x] Add `pydantic-settings` to `pyproject.toml` dependencies
   - [x] Refactor `prober/config.py` to use Pydantic BaseSettings
   - [x] Define `ProberConfig` class with field validation and validation_alias

2. **Implement environment variable handling**
   - [x] Use Pydantic's native `validation_alias` for environment variables
   - [x] Configure model to accept both field names and aliases
   - [x] Simplify `load_config()` function to use Pydantic instantiation

3. **Add field validation**
   - [x] IP address validation for server_ip and expected_ip
   - [x] Port range validation (1-65535)
   - [x] Required field validation for hostnames and credentials
   - [x] Collection interval bounds checking (30s-3600s)

### Configuration Approach
- Uses Pydantic's built-in environment variable handling
- Maintains backward compatibility with existing tests
- Provides clear validation error messages
- No external secrets management providers needed initially

### Files Modified
- `prober/config.py` (refactored to use validation_alias)
- All existing tests continue to pass

---

## Phase 2: Basic Circuit Breaker and Health Endpoint
**Status**: ✅ Completed  
**Priority**: High - Core reliability feature  
**Estimated Effort**: 1 day (completed)

### Objective
Add basic circuit breaker pattern and simple health monitoring

### Implementation Tasks (Completed)
1. **Add circuit breaker dependency and basic setup**
   - [x] Add `pybreaker` dependency: `poetry add pybreaker`
   - [x] Add circuit breaker configuration to `prober/config.py`
   - [x] Use pybreaker's default in-memory storage

2. **Integrate circuit breaker into Probe base class**
   - [x] Add circuit breaker instance to `Probe.__init__()`
   - [x] Wrap `_execute_check()` calls with circuit breaker
   - [x] Handle `CircuitBreakerError` when circuit is open

3. **Add custom HTTP server with health endpoint**
   - [x] Replace `start_http_server` with custom `HTTPServer`
   - [x] Serve both `/metrics` and `/health` endpoints
   - [x] Return HTTP 200/503 based on >50% probes healthy
   - [x] JSON response with health status and probe counts

4. **Essential configuration options**
   - [x] `CIRCUIT_BREAKER_FAILURE_THRESHOLD` (default: 5)
   - [x] `CIRCUIT_BREAKER_RECOVERY_TIMEOUT` (default: 60s)

### Configuration Options Added
- `CIRCUIT_BREAKER_FAILURE_THRESHOLD=5`
- `CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60`

### Files Modified/Created
- `prober/config.py` (modified - added circuit breaker configuration fields)
- `prober/probe.py` (modified - integrated pybreaker circuit breaker)
- `prober/app.py` (modified - custom HTTP server with /health endpoint)
- `tests/test_app.py` (modified - updated tests for new HTTP server)
- `tests/test_probe.py` (modified - added circuit breaker config to test fixtures)

### Key Features Added
- **Circuit breaker protection**: Each probe wrapped with pybreaker.CircuitBreaker
- **Health monitoring**: `/health` endpoint returns JSON with probe status
- **Graceful degradation**: Circuit breakers prevent cascading failures
- **Load balancer ready**: Health endpoint suitable for load balancer health checks

---

## Phase 3: Simple Exponential Backoff and Jitter
**Status**: ✅ Completed  
**Priority**: High - Prevents service overload  
**Estimated Effort**: 1 day (completed)

### Objective
Add basic exponential backoff with jitter to prevent service overload during failures

### Implementation Tasks (Completed)
1. **Add failure tracking to Probe base class**
   - [x] Add `consecutive_failures` counter to `probe.py`
   - [x] Track failures in `execute()` method
   - [x] Reset counter on successful execution

2. **Implement backoff calculation**
   - [x] Add `_calculate_backoff_interval()` method to `Probe`
   - [x] Use formula: `min(base_interval * (multiplier ^ failures), max_interval)`
   - [x] Add jitter: `interval * (1 + random(-0.2, 0.2))`

3. **Add backoff configuration to config.py**
   - [x] Add backoff configuration fields with validation
   - [x] Integrate with existing Pydantic configuration system

4. **Integrate with existing circuit breaker**
   - [x] Use calculated interval in `_run()` method
   - [x] Reset backoff when circuit breaker state changes
   - [x] Maintain normal interval when circuit is closed

5. **Simple testing**
   - [x] Add unit tests for backoff calculation
   - [x] Test jitter randomization
   - [x] Test integration with circuit breaker

### Configuration Options Added
- `BACKOFF_BASE_INTERVAL=300` (default probe interval)
- `BACKOFF_MAX_INTERVAL=3600` (maximum 1 hour)
- `BACKOFF_MULTIPLIER=2.0` (double each failure)
- `BACKOFF_MAX_FAILURES=5` (cap at 5 failures)

### Files Modified/Created
- `prober/config.py` (modified - added backoff configuration fields)
- `prober/probe.py` (modified - added backoff logic and failure tracking)
- `tests/test_probe.py` (modified - added comprehensive backoff tests)
- `tests/test_app.py` (modified - updated test fixtures for backoff config)

### Key Features Added
- **Consecutive failure tracking**: Separate from total failures for backoff calculation
- **Exponential backoff**: Formula-based interval calculation with configurable parameters
- **Jitter implementation**: ±20% randomization to prevent thundering herd
- **Circuit breaker integration**: Resets backoff when circuit breaker opens
- **Configuration validation**: Full Pydantic validation for all backoff parameters
- **Comprehensive testing**: Unit tests for all backoff scenarios and edge cases

---

## Phase 4: Categorized Error Handling System
**Status**: Not Started  
**Priority**: Medium - Improves alerting intelligence  
**Estimated Effort**: 3 days

### Objective
Implement intelligent error categorization with type-specific handling strategies

### Implementation Tasks
1. **Create error classification system**
   - [ ] Add `prober/errors.py` with exception hierarchy
   - [ ] Define error categories: `NetworkError`, `AuthenticationError`, `ConfigurationError`, `DNSError`, `CertificateError`
   - [ ] Create `ErrorClassifier` to categorize standard exceptions

2. **Enhance probe error handling**
   - [ ] Modify each probe's `_execute_check()` to raise categorized exceptions
   - [ ] Update `Probe.execute()` to handle different error types appropriately
   - [ ] Add error category to Prometheus metrics labels

3. **Implement category-specific retry policies**
   - [ ] Network errors: aggressive retry with backoff
   - [ ] Authentication errors: minimal retry, escalate quickly
   - [ ] Configuration errors: no retry, immediate alert
   - [ ] DNS errors: moderate retry with longer intervals
   - [ ] Certificate errors: daily retry only

4. **Add enhanced alerting thresholds**
   - [ ] Configuration for category-specific failure thresholds
   - [ ] Different alerting channels per error category
   - [ ] Escalation rules based on error persistence

5. **Logging and observability improvements**
   - [ ] Structured logging with error categories
   - [ ] Add error category distribution metrics
   - [ ] Create dashboard templates for error analysis

### Configuration Options Added
- Error category retry policies
- Category-specific failure thresholds
- Alerting configuration per category

### Files Modified/Created
- `prober/errors.py` (new)
- `prober/probe.py` (modified)
- All probe files in `prober/probes/` (modified)
- `prober/metrics.py` (modified)

---

## Phase 5: Resource Management and Graceful Degradation
**Status**: Not Started  
**Priority**: Medium - Production stability  
**Estimated Effort**: 3-4 days

### Objective
Implement comprehensive resource management and graceful degradation under stress

### Implementation Tasks
1. **Add connection pooling and resource limits**
   - [ ] Create `prober/resources.py` with `ConnectionPool` class
   - [ ] Implement SMTP/HTTP connection reuse where possible
   - [ ] Add global limits: max concurrent probes, max connections per probe

2. **Implement resource monitoring**
   - [ ] Add memory usage tracking per probe
   - [ ] Monitor thread count and connection count
   - [ ] Create resource exhaustion detection logic

3. **Enhance graceful shutdown**
   - [ ] Implement cascading timeouts: probe-level → application-level
   - [ ] Add resource cleanup validation in `app.py`
   - [ ] Improve signal handling with resource state checks

4. **Add load shedding mechanisms**
   - [ ] Implement probe priority system (critical vs. optional)
   - [ ] Add probe suspension under resource pressure
   - [ ] Create degraded mode with reduced probe frequency

5. **Resource configuration and monitoring**
   - [ ] Add resource limit configuration options
   - [ ] Create resource utilization metrics
   - [ ] Implement automatic probe disabling under extreme load
   - [ ] Add resource health to overall health endpoint from Phase 2

6. **Testing and validation**
   - [ ] Create resource stress tests
   - [ ] Test graceful degradation scenarios
   - [ ] Validate cleanup under various failure conditions

### Configuration Options Added
- `MAX_CONCURRENT_PROBES=20`
- `MAX_CONNECTIONS_PER_PROBE=5`
- `MEMORY_LIMIT_MB=512`
- `RESOURCE_CHECK_INTERVAL=60`
- Probe priority configuration

### Files Modified/Created
- `prober/resources.py` (new)
- `prober/app.py` (modified)
- `prober/probe.py` (modified)
- `tests/test_resources.py` (new)

---

## Progress Tracking

### Overall Status
- [x] Phase 1: Configuration Validation with Pydantic (Completed)
- [x] Phase 2: Basic Circuit Breaker and Health Endpoint (Completed)
- [x] Phase 3: Simple Exponential Backoff and Jitter (Completed)
- [ ] Phase 4: Categorized Error Handling System
- [ ] Phase 5: Resource Management and Graceful Degradation

### Notes
- Each phase includes comprehensive testing and documentation updates
- Backward compatibility maintained throughout implementation
- All phases integrate with existing Prometheus metrics system
- Configuration changes documented in CLAUDE.md after each phase

### Development Environment Setup
**Required for all phases:**
1. **Virtual Environment**: Always use Poetry for dependency management
   ```bash
   poetry env use python3.13  # Ensure Python 3.11+ is used
   poetry install              # Install dependencies in virtual environment
   poetry run <command>        # Run all commands through Poetry
   ```

2. **Context7 Access**: Leverage context7 MCP server for library documentation
   - Use context7 for up-to-date API documentation before implementing
   - Research best practices and examples for new libraries
   - Validate implementation approaches against current documentation

### Enhanced Implementation Approach with Context7

**Key Improvements based on library research:**

1. **Prometheus Metrics Enhancements**:
   - Use `prometheus_client.Gauge.set_function()` for dynamic metrics  
   - Implement proper multiprocess support with `MultiProcessCollector`
   - Add exemplars to metrics for better observability
   - Use restricted registries for efficient metric filtering

2. **Circuit Breaker Implementation**:
   - Use `pybreaker` library (mature, well-documented) ✅ Completed
   - Implement custom listeners for logging and metrics integration
   - Default to in-memory storage, optional Redis for multi-instance scaling
   - Configure success thresholds for gradual recovery

3. **Simple Backoff Implementation**:
   - Direct integration with existing Probe class
   - Basic exponential calculation with jitter
   - Integration with circuit breaker state
   - Minimal configuration overhead

4. **Better Error Handling**:
   - Use exception exclusion patterns in circuit breakers
   - Implement custom listener classes for different probe types
   - Add async support for future scalability

5. **Resource Management**:
   - Leverage Prometheus' built-in process collectors
   - Use context managers for resource cleanup
   - Implement proper graceful shutdown patterns

### Testing Strategy
- Unit tests for new components
- Integration tests for probe behavior
- Load testing for resource management
- Chaos engineering for failure scenarios

---

## Future Enhancements

The following features were originally planned for earlier phases but moved to future enhancements to avoid over-engineering:

### Advanced Secrets Management
- **Secrets provider abstraction**: Create `prober/secrets.py` with `SecretsProvider` interface
- **External secrets providers**: Implement `VaultSecretsProvider` and `AWSSecretsProvider`
- **Secrets provider selection**: Environment variable-based provider selection
- **Secrets rotation**: Automatic credential refresh capabilities

### Configuration Schema and Documentation
- **JSON schema generation**: Create `config-schema.json` for external tooling
- **Advanced documentation**: Comprehensive configuration guides beyond current CLAUDE.md
- **Configuration validation tools**: External validation utilities
- **Environment variable reference**: Detailed reference tables and examples

### Advanced Security Features
- **Configuration drift detection**: Monitor and alert on configuration changes
- **Secrets masking**: Advanced log sanitization for sensitive values
- **Configuration encryption**: Encrypted configuration file support
- **Audit logging**: Configuration access and change tracking

### Advanced Circuit Breaker Features
- **Distributed circuit breaker state**: Redis integration for multi-instance deployments
- **Custom CircuitBreakerListener**: Advanced metrics integration and logging
- **Exception exclusions**: Complex categorization for transient vs permanent errors
- **Async support**: `call_async()` integration for future scalability
- **Advanced health management**: `HealthManager` class with sophisticated probe status tracking
- **Detailed health responses**: Individual probe statuses in health endpoint
- **Success threshold configuration**: Gradual recovery settings

### Advanced Retry Strategy Features (Originally in Phase 3)
- **Retry strategy framework**: `RetryStrategy` base class with multiple implementations
- **Multiple retry strategies**: Both exponential backoff and fixed interval strategies
- **Advanced metrics integration**: Exemplars, `MultiProcessCollector`, dynamic retry metrics
- **Complex testing strategy**: Integration tests, multiprocess behavior testing
- **Comprehensive failure categorization**: Different backoff strategies per error type

### Implementation Priority
These enhancements should be considered when:
- The system is deployed in highly regulated environments
- Multiple instances require centralized secrets management
- External tooling needs programmatic configuration access
- Advanced security compliance is required
- Distributed deployments need shared circuit breaker state
- Complex error handling and recovery patterns are needed

Last Updated: 2025-08-02