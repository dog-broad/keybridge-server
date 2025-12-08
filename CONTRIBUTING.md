# Contributing to KeyBridge Server

Thank you for your interest in contributing to the KeyBridge Server! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in the [Issues](../../issues) section
2. If not, create a new issue with:
   - A clear, descriptive title
   - Steps to reproduce the issue
   - Expected vs. actual behavior
   - Environment details (OS, Python version, etc.)
   - Relevant logs or error messages

### Suggesting Features

1. Check if the feature has already been suggested
2. Create a new issue with:
   - A clear description of the feature
   - Use cases and benefits
   - Any implementation ideas (optional)

### Pull Requests

1. **Fork the repository** and clone your fork
2. **Create a feature branch** from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**:
   - Follow the existing code style
   - Add comments for complex logic
   - Update documentation if needed
   - Add tests if applicable

4. **Test your changes**:
   ```bash
   # Activate virtual environment
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/macOS
   
   # Run tests (if available)
   python -m pytest tests/
   ```

5. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: Description of your changes"
   ```
   
   Use conventional commit messages:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `refactor:` for code refactoring
   - `test:` for test additions/changes
   - `chore:` for maintenance tasks

6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request**:
   - Target the `develop` branch
   - Provide a clear description of changes
   - Reference any related issues

## Development Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd keybridge-server
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/macOS
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file (copy from `.env.example`):
   ```bash
   cp src/.env.example src/.env
   ```

5. Run the server:
   ```bash
   python src/main.py
   ```

## Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines
- Use type hints where appropriate
- Keep functions focused and single-purpose
- Add docstrings for public functions and classes
- Maximum line length: 100 characters (soft limit)

## License Compliance

- All contributions must be compatible with Apache License 2.0
- New source files should include the Apache License header (see existing files for template)
- Update NOTICE file if adding third-party components
- Ensure any dependencies are compatible with Apache 2.0

## Security

- **Never commit sensitive data** (API keys, passwords, tokens)
- Use environment variables for configuration
- Review security implications of new features
- Report security vulnerabilities privately to maintainers

## Testing

- Write tests for new features when possible
- Ensure existing tests pass
- Test edge cases and error conditions

## Documentation

- Update README.md for user-facing changes
- Add docstrings for new functions/classes
- Update API documentation if applicable

## Questions?

Feel free to open an issue for questions or reach out to the maintainers.

Thank you for contributing! 🎉

