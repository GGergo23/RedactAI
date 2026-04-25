# RedactAI
![Banner](/assets/images/banner.png)

RedactAI is a locally running desktop application, which automatically detects and applies redactions to image files.

## Features

- **Automatic Redaction**: RedactAI uses advanced algorithms to identify sensitive information in documents and applies redactions automatically, ensuring that confidential data is protected.
- **User-Friendly Interface**: The application features an intuitive interface that allows users to easily upload documents, review detected redactions, and make manual adjustments if necessary.
- **Support for Image Files**: RedactAI supports various image formates for redaction
- **Customizable Redaction Settings**: Users can customize redaction settings to specify the types of information they want to redact, such as names, addresses, or financial data.
- **Local Processing**: All redaction processes are performed locally on the user's machine, ensuring that sensitive information is not transmitted over the internet, enhancing security and privacy.

## Contributing

### Technologies Used
- Python 3.14
- `uv` for dependency management and virtual environments.
- PyQt6 for the user interface.

### Important Commands
```uv sync``` - Install dependencies and set up the virtual environment.  
```uv run app``` - Run the application.  
```uv run pytest``` - Run tests.  
```uv run black src test``` - Run black for formatting.  
```uv run flake8 src test``` - Run flake8 for linting.  

### Repository Structure
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

### Code of Conduct
- Always create a new branch for your work.
- Make sure to implement tests for your changes. (Note: mirror the folder structure of `src` in the `tests` folder)
- When your work is complete, create a merge request.

## Disclaimer

### Goal of the project

This project is created as a project for the Advanced Software Engineering course at ELTE University.

### Use of Generative AI during development

- GenAI solutions were used to generate code snippets, documentation and custom image files.
- All  assets were reviewed by a human developer to ensure quality and accuracy.
