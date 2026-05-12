# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| < 2.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Dota Ready Helper, please report it by:

1. **DO NOT** open a public issue
2. Send an email to the repository owner or create a private security advisory on GitHub
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work on a fix as soon as possible.

## Security Best Practices

### For Users

1. **Never share your `.env` file** - it contains sensitive tokens
2. **Keep your Telegram bot token private** - anyone with it can control your bot
3. **Use a dedicated bot** - don't reuse bots from other projects
4. **Review code before running** - especially if you're modifying the project
5. **Keep dependencies updated** - run `pip install -r requirements.txt --upgrade` regularly

### For Contributors

1. **Never commit `.env` files** - they're in `.gitignore` for a reason
2. **Don't hardcode secrets** - always use environment variables
3. **Validate user input** - especially in Telegram bot handlers
4. **Use secure dependencies** - check for known vulnerabilities
5. **Follow secure coding practices** - avoid SQL injection, XSS, etc.

## Known Security Considerations

### Telegram Bot Token
- The bot token gives full control over your bot
- Store it securely in `.env` file
- Never commit it to version control
- Regenerate it if compromised (via @BotFather)

### Screen Capture
- The tool captures screenshots for image recognition
- Screenshots are processed in memory and not saved by default
- Be aware of sensitive information on your screen

### Automation Risks
- This tool automates game actions
- Use at your own risk
- May violate game terms of service
- Authors are not responsible for consequences

## Secure Configuration

Example of secure `.env` setup:

```bash
# Use strong, unique tokens
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789

# Reasonable confidence thresholds
CONFIDENCE_ACCEPT=0.80
CONFIDENCE_SEARCHING=0.70

# Safe timing values
SCAN_INTERVAL=0.30
CLICK_COOLDOWN=1.00
MESSAGE_COOLDOWN=5.00
```

## Updates and Patches

Security updates will be released as soon as possible after a vulnerability is confirmed. Users are encouraged to:

- Watch the repository for updates
- Enable GitHub notifications for releases
- Update to the latest version promptly

## Disclaimer

This tool is provided "as is" without warranty of any kind. Users are responsible for:
- Compliance with game terms of service
- Security of their own systems
- Consequences of using automation tools

Use responsibly and at your own risk.
