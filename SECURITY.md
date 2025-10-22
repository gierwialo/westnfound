# Security Policy

## Supported Versions

This project is currently in active development. Security updates are provided for the latest version only.

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly by following these steps:

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Send details of the vulnerability to: **westnfoundvulnerabilities@radziel.com**
3. Alternatively, you can use GitHub's private vulnerability reporting feature or create a private security advisory
4. Include a description of the vulnerability, steps to reproduce, and potential impact
5. Allow reasonable time for the issue to be addressed before public disclosure

## Security Considerations

This application is designed for finding West Coast Swing dance events. When deploying to production:

### Required Security Measures

- Change `DJANGO_SECRET_KEY` to a strong, randomly generated value
- Set `DEBUG=False` in production environments
- Configure `DJANGO_ADMIN_URL` to a non-default value for admin panel security
- Use HTTPS in production (configure reverse proxy/load balancer)
- Restrict `ALLOWED_HOSTS` to your specific domain(s) in Django settings
- Keep dependencies updated regularly

### Recommended Practices

- Use strong passwords for Django admin accounts
- Regularly update Docker images and Python packages
- Monitor application logs for suspicious activity
- Implement rate limiting at the reverse proxy level
- Use firewall rules to restrict access to necessary ports only

## Responsible Disclosure

We appreciate security researchers and users who report vulnerabilities to us. We commit to:

- Acknowledging receipt of vulnerability reports promptly
- Providing regular updates on the fix progress
- Crediting reporters (if desired) once the issue is resolved
