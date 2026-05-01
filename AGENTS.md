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

## First-time model setup (required once per machine)

The NLP detector requires the `en_core_web_sm` spaCy model, which must be downloaded and stored locally in `assets/models/` (not tracked in git due to size).

```bash
# Download the spaCy model
uv run python -c "
import urllib.request
import zipfile
from pathlib import Path

model_dir = Path('assets/models')
model_dir.mkdir(parents=True, exist_ok=True)

url = 'https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl'
wheel_path = model_dir / 'en_core_web_sm-3.8.0-py3-none-any.whl'

print('Downloading spaCy model...')
urllib.request.urlretrieve(url, wheel_path)

print('Extracting...')
with zipfile.ZipFile(wheel_path, 'r') as z:
    z.extractall(model_dir)

# Flatten the extracted directory structure
versioned = model_dir / 'en_core_web_sm' / 'en_core_web_sm-3.8.0'
if versioned.exists():
    import shutil
    for item in versioned.iterdir():
        dest = model_dir / 'en_core_web_sm' / item.name
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()
        shutil.move(str(item), str(dest))
    versioned.rmdir()

print('Model ready at assets/models/en_core_web_sm')
"
```

Verify the setup:
```bash
uv run python -c "from src.ai.detector import NLPDetector; NLPDetector().detect('test')"
```

If successful, you'll see the detector load without errors.

After development, you can run tests and linting with:
```bash
uv run pytest
uv run flake8 src tests
uv run black --check src tests
```

## CI/CD Pipeline

### Running checks locally before pushing

Before pushing your branch, run the same checks that CI will run:

```bash
# Install/update dependencies
uv sync

# Lint code
uv run flake8 src tests

# Check formatting
uv run black --check src tests
uv run isort --check-only src tests

# Auto-fix formatting issues
uv run black src tests
uv run isort src tests

# Run tests
uv run pytest tests
```

### Creating a pull request

1. Create a feature branch from `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feat/your-feature-name
   ```

2. Make your changes and commit:
   ```bash
   git add .
   git commit -m "feat: description of what you changed"
   ```

3. Push your branch:
   ```bash
   git push -u origin feat/your-feature-name
   ```

4. On GitHub, create a PR to `main`

5. Wait for the CI workflow to complete (usually 2–3 minutes)
   - Check the "Checks" tab on your PR
   - All checks must pass (✅) before merging

6. If checks fail:
   - Read the error logs
   - Fix issues locally
   - Commit and push again
   - CI will re-run automatically

7. Once all checks pass, merge your PR

### Creating a release

When you're ready to release a version:

```bash
# Ensure you're on main and everything is up to date
git checkout main
git pull origin main

# Create a version tag
git tag -a v0.1.0 -m "Release v0.1.0"

# Push the tag to GitHub
git push origin v0.1.0
```

The CI/CD system will automatically:
- Build PyInstaller bundles for Linux, macOS, and Windows
- Create a GitHub Release with download links
- The release appears under "Releases" in your repository

You can download the bundle directly from the Release page.

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

- Always create a new feature branch before making changes.
  - Use conventional branch names: `feat/feature-name`, `fix/bug-name`, `docs/documentation-name`
  - Example: `feat/ci-cd-setup`, `fix/import-error`, `docs/readme-update`
- Run linting and tests locally before pushing (see CI/CD Pipeline section)
- When the work is complete, create a pull request to `main`
- In the pull request description, include an executive summary of:
	- what was changed,
	- why it was changed,
	- the result or validation outcome.
- Prefer small, focused changes over broad refactors.
- Preserve existing project conventions unless the task explicitly asks for a change.

## Code Quality
- Follow standard Python coding conventions.
- Use descriptive variable and function names.
- Always use snake case for variables and functions, and PascalCase for classes.
- Write modular, reusable code with clear interfaces.
- Include docstrings for all public functions and classes.
- Write unit tests for all new functionality and ensure existing tests pass.
- Use type hints for all function signatures and class attributes.
- Use defensive programming practices, especially when handling external data or executing trades.
- Prefer shorter, atomic functions.

## Testing
- Use `uv run pytest tests` for running tests.
- Place all tests in the `tests/` directory.
- When creating tests, mirror the folder structure of `src` in the `tests` folder for better organization and maintainability.
- For every new feature (excluding the UI), create unit tests that cover the expected behavior, edge cases, and error handling.
- Aim for high test coverage, especially for critical logic.
- Test file naming convention: `test_*.py` or `*_test.py`

## Pull request template

```
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
```

## Explicit boundaries
- Never commit secrets, API keys, or sensitive information to the repository.
- Use environment variables or secure vaults for managing sensitive data.
- Always review code for security implications, especially when handling external data or executing trades.
- Don't suggest `pip install` commands in code snippets. Use `uv` for dependency management and virtual environments.
- Before adding a new dependency, consider if it is necessary (eg. there is an alternative already in the dependencies) and if there are lighter alternatives. Always prefer standard library solutions whenever reasonable.

## Project-specific warnings
None at this time