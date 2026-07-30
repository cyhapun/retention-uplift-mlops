## MODIFIED Requirements

### Requirement: Paired prediction comparison

The system SHALL compare predictions for the same baseline row slice and simulated row slice while preserving row pairing and SHALL provide aggregate and recommendation-change summaries. In demo-local history mode, it SHALL expose the completed compact summary without requiring durable simulation or prediction metadata.

#### Scenario: Predictions complete

- **WHEN** the champion model successfully scores both datasets
- **THEN** the result SHALL include row count, model reference, affected feature context, before/after average uplift, and recommendation-change count/share when policy comparison is enabled
- **AND** SHALL include action distributions when policy comparison is enabled
- **AND** SHALL provide a structured in-memory response and downloadable result artifact
- **AND** SHALL make a compact summary available for browser-local history

#### Scenario: A recommendation changes

- **WHEN** the policy recommendation for a paired row differs between baseline and simulated inputs
- **THEN** the result SHALL count that row as changed
- **AND** SHALL not create a production decision log or feedback record for that row

### Requirement: Temporary prediction artifact lifecycle

Prediction result artifacts SHALL use the existing simulation named volume and retention policy, SHALL be finalized atomically, and SHALL be removed or marked unavailable after expiry or an unverified restart. In demo-local history mode, only the compact browser summary may remain after artifact expiry.

#### Scenario: Prediction artifact expires

- **WHEN** the configured result expiry is reached
- **THEN** the system SHALL remove the result artifact during cleanup
- **AND** SHALL return an expired/not-found response for subsequent downloads
- **AND** SHALL not require durable prediction metadata in demo-local mode
- **AND** SHALL keep any browser-local summary clearly marked as historical synthetic data without an active download

## ADDED Requirements

### Requirement: Browser-owned Simulation Lab history

The Simulation Lab UI SHALL save bounded completed scenario and prediction summaries in the current browser when demo-local history is enabled.

#### Scenario: Completed lab result is saved

- **WHEN** a synthetic scenario or prediction comparison completes
- **THEN** the UI SHALL save its compact summary locally
- **AND** SHALL not save full Parquet/CSV contents or raw feature rows in `localStorage`

#### Scenario: Browser history is displayed

- **WHEN** the operator returns to Simulation Lab in the same browser
- **THEN** the UI SHALL show recent browser-local synthetic results
- **AND** SHALL provide a clear-history action without requiring persistence details in the primary workflow
