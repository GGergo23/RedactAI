# AGENTS.md

## Project overview
RedactAI is a locally running desktop application, which automatically detects and applies redactions to documents (images for now).

## Preferred language version and development tools
Python 3.14
Use `uv` for dependency management and virtual environments.
Use `black` for code formatting.
Use `flake8` for linting.

## How to set up the development environment
1. Clone the repository:
```bash
git clone <repository-url>
```
2. Install dependencies and create the virtual environment:
```bash
uv sync
```
3. Activate the virtual environment:
```bash
uv shell
```

After development, you can run tests and linting with:
```bash
uv run pytest
uv run flake8 src tests
uv run black --check src tests
```

## Project structure
```text
.
├── pyproject.toml
├── README.md
├── AGENTS.md
├── assets/
│   ├── models/ # pre-trained models detection
│   ├── images/ # ui assets
├── src/
│   ├── ui/ # user interface components and logic
│   ├── ai/ # ai models and related logic
│   ├── redact_engine/ # core redaction logic and algorithms
│   ├── pipeline/ # orchestration of the redaction process, connecting the UI, AI, and redaction engine
│   ├── persistence/ # data storage and management, such as saving user settings or exporting redacted documents
│   ├── main.py # entry point for the application
└── tests/ # unit and integration tests, mirroring the folder structure of src
│   ├── assets/ # assets for testing
│   ...
```

## Required Workflow

- Always create a new branch before making changes.
- When the work is complete, create a merge request.
- In the merge request description, include an executive summary of:
	- what was changed,
	- why it was changed,
	- the result or validation outcome.
- Prefer small, focused changes over broad refactors.
- Preserve existing project conventions unless the task explicitly asks for a change.

## Code Quality
- Follow stardard Python coding conventions.
- Use descriptive variable and function names.
- Always use snake case for variables and functions, and PascalCase for classes.
- Write modular, reusable code with clear interfaces.
- Include docstrings for all public functions and classes.
- Write unit tests for all new functionality and ensure existing tests pass.
- Use type hints for all function signatures and class attributes.
- Use defensive programming practices, especially when handling external data or executing trades.
- Prefer shorter, atomic functions.

## Testing
- Use `uv run pytest` for running tests.
- When creating tests, mirror the folder structure of `src` in the `tests` folder for better organization and maintainability.
- For every new feature (exluding the UI), create unit tests that cover the expected behavior, edge cases, and error handling.
- Aim for high test coverage, especially for critical logic.

## Pull request template

"""
### Summary
<!-- Provide a brief summary of the changes made in this pull request. -->
### Motivation
<!-- Explain the motivation behind these changes. Why were they necessary? -->
### Implementation
<!-- Describe the implementation details. What was changed and how? -->
### Validation
<!-- Describe how you validated the changes. What tests were run and what were the results? -->
### Additional Notes
<!-- Include any additional information or context that may be relevant to reviewers. -->
"""

## Explicit boundaries
Never commit secrets, API keys, or sensitive information to the repository.
Use environment variables or secure vaults for managing sensitive data.
Always review code for security implications, especially when handling external data or executing trades.
Don't suggest `pip install` commands in code snippets. Use `uv` for dependency management and virtual environments.
Before adding a new dependency, consider if it is necessary (eg. there is an alternative already in the dependencies) and if there are lighter alternatives. Always prefer standard library solutions whenever reasonable.

## Project-specific warnings
None at this time