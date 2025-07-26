# Security Documentation

## Overview

QuranBot implements comprehensive security measures to protect against various attack vectors and ensure safe operation. This document outlines all security features, best practices, and configuration guidelines.

## Security Features

### 1. Rate Limiting

#### Sliding Window Rate Limiting

- **Purpose**: Prevents API abuse and spam attacks
- **Implementation**: `RateLimiter` class with sliding window algorithm
- **Default**: 10 requests per minute per user
- **Scope**: Per-user, per-command, and global limits

```python
@rate_limit(limit=5, window=60)
async def sensitive_command(ctx):
    # Command implementation
    pass
```

#### Token Bucket Rate Limiting

- **Purpose**: Prevents burst attacks while allowing legitimate usage
- **Implementation**: Token bucket algorithm with configurable refill rates
- **Use Cases**: High-frequency commands, audio controls

### 2. Input Validation and Sanitization

#### Malicious Input Detection

- **SQL Injection**: Detects and blocks SQL injection attempts
- **XSS Prevention**: Filters script tags and JavaScript execution attempts
- **Command Injection**: Prevents shell command injection
- **Path Traversal**: Blocks directory traversal attacks

```python
@validate_input
async def command_with_input(ctx, user_input: str):
    # Input is automatically validated before execution
    pass
```

#### Input Sanitization

- **Length Limits**: Configurable maximum input lengths
- **Unicode Normalization**: Prevents Unicode-based bypass attempts
- **Character Filtering**: Removes or escapes dangerous characters

### 3. Permission and Access Control

#### Admin-Only Commands

```python
@require_admin
async def admin_command(ctx):
    # Only admin users can execute this command
    pass
```

#### Guild-Based Permissions

- **Isolation**: Permissions are isolated per Discord server
- **Role-Based**: Integration with Discord role system
- **Escalation Prevention**: Users cannot elevate their own permissions

### 4. Data Protection and Privacy

#### Sensitive Data Sanitization

- **Logging**: Automatically redacts tokens, passwords, and API keys
- **Configuration**: Removes sensitive data from configuration files
- **URLs**: Sanitizes query parameters containing secrets

#### User Data Anonymization

- **User IDs**: Hashed for logging and analytics
- **Message Content**: Sanitized before logging
- **Timestamps**: Preserved for legitimate use

### 5. Configuration Security

#### Environment Variable Validation

- **Token Format**: Validates Discord token format and length
- **ID Validation**: Ensures Discord IDs are valid integers
- **Path Security**: Validates file paths for safety

#### Secure Defaults

- **No Hardcoded Secrets**: All sensitive data in environment variables
- **Template Files**: `.env.example` with placeholder values
- **File Permissions**: Secure default permissions for configuration files

## Security Configuration

### Environment Variables

```bash
# Security Configuration
RATE_LIMIT_PER_MINUTE=10
USE_WEBHOOK_LOGGING=true

# Admin Configuration
ADMIN_USER_ID=123456789012345678
DEVELOPER_ID=123456789012345678

# Discord Configuration (use placeholders in .env.example)
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

### File Permissions

Ensure configuration files have secure permissions:

```bash
chmod 600 config/.env
chmod 644 config/.env.example
```

### Git Security

The `.gitignore` file is configured to prevent accidental commits of sensitive data:

```gitignore
# Environment files
config/.env
*.env

# Sensitive data patterns
*token*
*TOKEN*
*key*
*KEY*
*.token
*.key
```

## Security Best Practices

### 1. Development Security

#### Code Review

- All security-related code requires review
- Input validation must be tested
- Rate limiting should be verified
- Permission checks must be comprehensive

#### Testing

- Security tests in `tests/test_security_comprehensive.py`
- Rate limiting tests with concurrent scenarios
- Input validation tests with known attack vectors
- Permission escalation prevention tests

### 2. Deployment Security

#### Environment Setup

1. Copy `config/.env.example` to `config/.env`
2. Fill in actual values (never commit real `.env`)
3. Set secure file permissions
4. Verify all required variables are set

#### VPS Security

- Use SSH key authentication
- Disable password authentication
- Keep system updated
- Use firewall rules
- Monitor access logs

### 3. Operational Security

#### Monitoring

- Log all security events
- Monitor rate limiting violations
- Track failed authentication attempts
- Alert on suspicious patterns

#### Incident Response

1. **Detection**: Automated alerts for security events
2. **Analysis**: Review logs and patterns
3. **Containment**: Rate limiting and blocking
4. **Recovery**: Restore normal operation
5. **Documentation**: Update security measures

## Attack Vector Protection

### 1. Discord API Abuse

- **Rate Limiting**: Prevents API quota exhaustion
- **Token Protection**: Secure token storage and validation
- **Webhook Security**: Validates webhook URLs and sanitizes data

### 2. Command Injection

- **Input Validation**: Filters shell commands and scripts
- **Path Validation**: Prevents directory traversal
- **Sanitization**: Removes dangerous characters

### 3. Data Extraction

- **Access Controls**: Admin-only sensitive commands
- **Data Sanitization**: Removes PII from logs
- **Permission Isolation**: Guild-based access control

### 4. Resource Exhaustion

- **Rate Limiting**: Prevents spam and DoS attempts
- **Memory Management**: Cleanup of expired rate limit data
- **Concurrent Limits**: Controls parallel operations

## Security Testing

### Automated Tests

Run the comprehensive security test suite:

```bash
# Run all security tests
pytest tests/test_security_comprehensive.py -v

# Run specific test categories
pytest tests/test_security_comprehensive.py::TestRateLimiterSecurity -v
pytest tests/test_security_comprehensive.py::TestInputValidationSecurity -v
pytest tests/test_security_comprehensive.py::TestPermissionSecurity -v
```

### Manual Testing

#### Rate Limiting

1. Send commands rapidly to test rate limits
2. Verify different users have isolated limits
3. Test global rate limiting under load

#### Input Validation

1. Test with known SQL injection payloads
2. Attempt XSS attacks in text inputs
3. Try command injection in various fields

#### Permissions

1. Test admin commands with non-admin users
2. Verify guild isolation
3. Attempt permission escalation

## Security Monitoring

### Log Analysis

Security events are logged with structured data:

```json
{
  "event": "rate_limit_exceeded",
  "user_id": "[REDACTED]",
  "command": "verse",
  "timestamp": "2025-01-15T10:30:00Z",
  "details": {
    "limit": 10,
    "window": 60,
    "current_count": 11
  }
}
```

### Alerts

Configure alerts for:

- Rate limiting violations
- Failed authentication attempts
- Input validation failures
- Permission escalation attempts
- Suspicious activity patterns

## Compliance and Auditing

### Data Protection

- PII sanitization in logs
- User data anonymization
- Secure data transmission
- Access logging

### Audit Trail

- All admin actions logged
- Configuration changes tracked
- Security events recorded
- User interactions monitored

## Incident Response

### Security Incident Procedure

1. **Immediate Response**
   - Stop any ongoing attack
   - Enable additional rate limiting
   - Block suspicious users if necessary

2. **Investigation**
   - Review security logs
   - Analyze attack patterns
   - Identify compromised data

3. **Containment**
   - Update security measures
   - Patch vulnerabilities
   - Strengthen configurations

4. **Recovery**
   - Restore normal operation
   - Verify system integrity
   - Update documentation

5. **Prevention**
   - Update security tests
   - Improve monitoring
   - Train team on new threats

## Contact and Reporting

For security concerns or to report vulnerabilities:

1. **Internal Team**: Contact project maintainers
2. **Security Issues**: Create private issue or contact directly
3. **Documentation**: Update this document with new security measures

## Version History

- **v3.0.0**: Initial security framework implementation
- **v3.1.0**: Added comprehensive rate limiting
- **v3.2.0**: Enhanced input validation and sanitization
- **v3.3.0**: Implemented permission system and access controls
- **v3.4.0**: Added data protection and privacy features
- **v3.5.0**: Comprehensive security testing and documentation
