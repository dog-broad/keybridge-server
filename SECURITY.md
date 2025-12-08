# Security Policy

## Supported Versions

We actively support the latest version of the KeyBridge Server. Security updates are applied to the current release.

## Security Configuration

### Secret Key Management

**IMPORTANT**: The default secret key (`keybridge-secret-key-change-in-production`) is for development purposes only. **You must change this in production!**

#### Server Configuration

The server uses environment variables for configuration. Set the `SECRET_KEY` environment variable in your `.env` file:

```bash
# .env
SECRET_KEY=your-strong-random-secret-key-here
```

Generate a strong secret key:
```bash
# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Using OpenSSL
openssl rand -base64 32
```

#### Android App Configuration

The Android app currently uses a hardcoded default secret key for simplicity. **For production use, ensure both the server and client use the same secret key.**

**Note**: In a production environment, consider:
- Using a secure key exchange mechanism
- Implementing per-session key generation
- Using certificate-based authentication

### Encryption

- **Algorithm**: AES-256-GCM
- **Key Derivation**: PBKDF2-HMAC-SHA256
- **Iterations**: 100,000
- **Salt**: `keybridge_salt` (static, consider making this configurable)

### Authentication

- Token-based authentication with expiration
- Maximum authentication attempts: 3 (configurable)
- Token expiry: 60 minutes (configurable)

### Rate Limiting

- Default: 300 requests per minute per connection
- Configurable via `RATE_LIMIT` environment variable

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public issue. Instead, please email the maintainers privately with:

1. A description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

We will respond within 48 hours and work with you to address the issue before public disclosure.

## Security Best Practices

1. **Change the default secret key** before deploying to production
2. **Use environment variables** for all sensitive configuration
3. **Keep dependencies updated** - regularly update `requirements.txt`
4. **Use HTTPS/WSS** in production (consider using a reverse proxy like nginx)
5. **Restrict network access** - only allow connections from trusted networks
6. **Monitor logs** for suspicious activity
7. **Use firewall rules** to restrict access to the WebSocket port
8. **Run with minimal privileges** - don't run the server as root/administrator unless necessary

## Known Limitations

- The current implementation uses a static salt for key derivation. Consider making this configurable.
- The Android app uses a hardcoded secret key. For production, implement a secure key exchange.
- No certificate-based authentication (currently token-based only)
- No built-in HTTPS/WSS support (use a reverse proxy)

## Security Updates

We recommend:
- Subscribing to repository notifications for security updates
- Regularly checking for dependency vulnerabilities
- Using tools like `pip-audit` or `safety` to check for known vulnerabilities

