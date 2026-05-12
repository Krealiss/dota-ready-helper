# Contributing to Dota Ready Helper

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)
- Relevant logs from `logs/` folder

### Suggesting Features

Feature requests are welcome! Please:
- Check if the feature was already suggested
- Clearly describe the feature and its benefits
- Explain how it would work

### Pull Requests

1. **Fork and clone** the repository
2. **Create a branch** for your feature: `git checkout -b feature/your-feature-name`
3. **Make your changes** following the code style guidelines
4. **Test your changes** thoroughly
5. **Commit** with clear messages: `git commit -m "Add feature: description"`
6. **Push** to your fork: `git push origin feature/your-feature-name`
7. **Open a Pull Request** with a clear description

## Code Style Guidelines

### Python Code
- Follow PEP 8 style guide
- Use type hints where possible
- Add docstrings for functions and classes
- Keep functions focused and small
- Use meaningful variable names

### Example:
```python
def find_button(image_path: str, confidence: float = 0.8) -> Optional[tuple]:
    """
    Find button on screen using template matching.
    
    Args:
        image_path: Path to template image
        confidence: Minimum confidence threshold (0.0-1.0)
        
    Returns:
        Tuple of (x, y) coordinates if found, None otherwise
    """
    # Implementation
    pass
```

### Commit Messages
- Use present tense: "Add feature" not "Added feature"
- Be descriptive but concise
- Reference issues when applicable: "Fix #123: Description"

### Testing
- Test your changes manually before submitting
- Ensure the bot responds correctly to Telegram commands
- Verify image recognition works with your changes
- Check that hotkeys still function

## Project Structure

Understanding the codebase:
- `main.py` - Entry point, initializes all components
- `config.py` - Configuration loading from `.env`
- `dota_helper.py` - Core game detection logic
- `telegram_bot.py` - Telegram bot handlers
- `image_recognition.py` - OpenCV-based image matching
- `stats_tracker.py` - Statistics collection
- `error_handler.py` - Error handling and crash reports
- `gui.py` - GUI interface (if enabled)

## Development Setup

1. Install development dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` from `.env.example`:
```bash
cp .env.example .env
```

3. Add your test Telegram bot credentials to `.env`

4. Run in development mode:
```bash
python main.py
```

## Areas for Contribution

We especially welcome contributions in:
- 🐛 Bug fixes
- 🎨 UI/UX improvements
- 📝 Documentation improvements
- 🌍 Translations
- ⚡ Performance optimizations
- 🧪 Test coverage
- 🔧 New features (discuss first in issues)

## Questions?

Feel free to open an issue with the `question` label if you need help or clarification.

Thank you for contributing! 🎉
