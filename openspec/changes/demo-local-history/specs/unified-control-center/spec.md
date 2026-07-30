## MODIFIED Requirements

### Requirement: Decision playground

The Control Center SHALL provide a form for submitting a valid decision request to FastAPI, SHALL present the decision response in business-readable terms with progressive disclosure for technical references, and SHALL add a compact browser-local history when demo-local history is enabled.

#### Scenario: Successful decision request

- **WHEN** an operator submits a valid user reference, estimated customer value, and feature payload
- **THEN** the dashboard SHALL call the decision API
- **AND** SHALL show treatment probability, control probability, uplift score, expected incremental value, ROI, recommended action, and decision reason with plain-language explanations
- **AND** SHALL make the decision identifier available as a secondary technical reference
- **AND** SHALL save a bounded display summary in the current browser when demo-local history is enabled

#### Scenario: Invalid decision request

- **WHEN** required features or estimated customer value are missing or invalid
- **THEN** the dashboard SHALL show field-level or API validation feedback in natural language
- **AND** SHALL not display the result as a successful decision
- **AND** SHALL not write an invalid result to browser history

## ADDED Requirements

### Requirement: Browser-local history presentation

The Control Center SHALL provide readable recent-history sections for demo decisions, feedback summaries, and Simulation Lab summaries without requiring durable PostgreSQL history.

#### Scenario: History is available

- **WHEN** valid local history exists after client hydration
- **THEN** the relevant task page SHALL show bounded recent entries
- **AND** SHALL provide concise clear-history controls

#### Scenario: History is empty

- **WHEN** no valid local history exists
- **THEN** the page SHALL show an explanatory empty state
- **AND** SHALL point the operator to the action that creates the first demo result
