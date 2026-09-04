# Contributing to QASCS

Thank you for your interest in contributing to the Quantum-Aware Secure Communication System (QASCS)! This document provides guidelines for contributing to the project.

## 🎯 Ways to Contribute

There are many ways to contribute to QASCS:

1. **Report bugs** - Found an issue? Report it!
2. **Suggest features** - Have an idea? We'd love to hear it!
3. **Improve documentation** - Help others understand the project
4. **Write code** - Fix bugs or implement new features
5. **Review pull requests** - Help maintain code quality
6. **Answer questions** - Help other users in discussions

## 🐛 Reporting Bugs

Before creating a bug report:
1. Check if the bug has already been reported in [Issues](https://github.com/orgito1015/Quantum-Aware-Secure-Communication-System-QASCS-/issues)
2. Make sure you're using the latest version
3. Verify the bug is reproducible

To report a bug:
1. Go to the [Issues](https://github.com/orgito1015/Quantum-Aware-Secure-Communication-System-QASCS-/issues/new/choose) page
2. Select **"Bug Report"** template
3. Fill out all required sections
4. Add relevant labels
5. Submit the issue

## 💡 Suggesting Features

To suggest a new feature:
1. Check if the feature has already been requested
2. Go to [Issues](https://github.com/orgito1015/Quantum-Aware-Secure-Communication-System-QASCS-/issues/new/choose)
3. Select **"Feature Request"** template
4. Describe the problem and proposed solution
5. Explain why this feature would be useful
6. Submit the issue

## 🔧 Development Setup

### Prerequisites

- Python 3.10 or higher (matches `requires-python` in `pyproject.toml`; CI
  tests 3.10-3.13)
- Git
- Virtual environment tool (venv)

### Setting Up Your Environment

```bash
# Clone the repository
git clone https://github.com/orgito1015/Quantum-Aware-Secure-Communication-System-QASCS-.git
cd Quantum-Aware-Secure-Communication-System-QASCS-

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package in editable mode with dev dependencies
pip install -e ".[dev]"

# Or use the Makefile
make install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=qasccs --cov-report=html

# Run specific test file
pytest tests/test_quantum_risk_engine.py
```

### Code Quality

```bash
# Lint (this is what CI runs)
ruff check .

# Type-check (this is what CI runs)
mypy qasccs

# Optional: install pre-commit hooks so both run automatically before each commit
pip install pre-commit
pre-commit install
```

## 📝 Coding Standards

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Lint with [ruff](https://github.com/astral-sh/ruff) (`ruff check .`) — configured in `pyproject.toml`
- Maximum line length: 120 characters (see `[tool.ruff]` in `pyproject.toml`)
- Use type hints for all function signatures; `mypy qasccs` must pass

### Code Organization

```python
# Good: Clear, documented function with type hints
def assess_quantum_risk(
    data_lifetime_years: int,
    data_classification: str,
    current_year: int = 2026
) -> dict:
    """
    Assess quantum computing risk for given parameters.
    
    Args:
        data_lifetime_years: How long the data must remain secure
        data_classification: Data sensitivity level (low/medium/high)
        current_year: Current year for risk calculation
        
    Returns:
        Dictionary containing risk assessment and recommendations
    """
    # Implementation
    pass
```

### Documentation

- All public modules, classes, and functions must have docstrings
- Use Google-style docstrings
- Include examples in docstrings for complex functions
- Keep README and docs up to date with code changes

### Testing

- Write tests for all new features
- Maintain >80% code coverage
- Use descriptive test names: `test_quantum_risk_engine_high_risk_scenario`
- Include both positive and negative test cases

## 🔀 Pull Request Process

### Before Creating a Pull Request

1. **Create an issue first** - Discuss your changes before implementing them
2. **Fork the repository** - Work in your own fork
3. **Create a branch** - Use a descriptive branch name
   ```bash
   git checkout -b feature/add-kyber-support
   git checkout -b fix/server-connection-timeout
   ```
4. **Make your changes** - Follow coding standards
5. **Write tests** - Ensure your changes are tested
6. **Update documentation** - Document new features
7. **Run tests** - Make sure all tests pass
8. **Commit your changes** - Use clear commit messages

### Commit Message Format

Use conventional commits format:

```
type(scope): brief description

Longer description if needed.

Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `style`: Code style changes (formatting)
- `chore`: Maintenance tasks

Examples:
```
feat(quantum-risk): add support for Kyber-1024

Implements Kyber-1024 algorithm support in the quantum risk engine
for enhanced post-quantum security.

Fixes #42
```

```
fix(server): resolve connection timeout issue

Connection timeout was occurring due to incorrect socket configuration.
Updated timeout handling and added retry logic.

Fixes #56
```

### Creating the Pull Request

1. Push your branch to your fork
2. Go to the original repository
3. Click **"New Pull Request"**
4. Select your fork and branch
5. Fill out the PR template:
   - Clear title describing the change
   - Link to related issues
   - Description of changes
   - Testing performed
   - Checklist items completed
6. Request review from maintainers
7. Be responsive to feedback

### Pull Request Checklist

- [ ] Code follows project style guidelines
- [ ] Tests added for new functionality
- [ ] All tests pass locally
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] Branch is up to date with main
- [ ] No merge conflicts
- [ ] Self-review completed

## 👥 Code Review Process

### For Authors

- Respond to review comments promptly
- Be open to feedback and suggestions
- Make requested changes or explain why not
- Keep the PR focused and reasonably sized
- Update the PR when main branch changes

### For Reviewers

- Be constructive and respectful
- Focus on code quality and maintainability
- Check for security issues
- Verify tests are adequate
- Approve when satisfied or request changes

## 🏷️ Issue and PR Labels

Understanding our label system helps with project navigation:

### Type Labels
- `bug` - Something isn't working
- `enhancement` - New feature
- `documentation` - Documentation updates

### Priority Labels
- `priority-critical` - Urgent, immediate attention needed
- `priority-high` - Important, should be addressed soon
- `priority-medium` - Normal priority
- `priority-low` - Nice to have

### Status Labels
- `needs-triage` - Needs initial review
- `good-first-issue` - Good for newcomers
- `help-wanted` - Looking for contributors

## 🎓 Learning Resources

New to quantum cryptography or the project? Check out:

- [docs/threat-model.md](../docs/threat-model.md) - Understanding quantum threats
- [docs/pqc-integration.md](../docs/pqc-integration.md) - Post-quantum cryptography integration
- [docs/architecture.md](../docs/architecture.md) - Sequence/component diagrams
- [docs/scaling.md](../docs/scaling.md) - Running multiple replicas
- [README.md](../README.md) - Project overview and quick start
- [NIST PQC Project](https://csrc.nist.gov/projects/post-quantum-cryptography)

## 📞 Getting Help

- **Questions**: Open a [Discussion](https://github.com/orgito1015/Quantum-Aware-Secure-Communication-System-QASCS-/discussions)
- **Bugs**: Create a [Bug Report](https://github.com/orgito1015/Quantum-Aware-Secure-Communication-System-QASCS-/issues/new/choose)
- **Features**: Submit a [Feature Request](https://github.com/orgito1015/Quantum-Aware-Secure-Communication-System-QASCS-/issues/new/choose)

## 📜 Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms:

- Be respectful and inclusive
- Welcome newcomers
- Focus on what's best for the community
- Show empathy towards others
- Accept constructive criticism gracefully

## 🙏 Recognition

Contributors will be recognized in:
- GitHub contributors list
- Project documentation
- Release notes for significant contributions

Thank you for contributing to QASCS! 🎉
