# Authentication Integration Guide

This document describes how authentication is integrated across all services in the Smart Home Energy Monitoring system.

## Overview

The authentication system uses JWT tokens issued by the `auth_service` and verified by all other services. This ensures secure access to protected endpoints and real-time data.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Mobile App    │    │   IoT Devices   │
│   (React)       │    │   (React Native)│    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Gateway / Load Balancer                  │
└─────────────────────────────────────────────────────────────────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Auth Service   │    │  Chat Service   │    │Telemetry Service│
│  (Port 8000)    │    │  (Port 8001)    │    │  (Port 8002)   │
│                 │    │                 │    │                 │
│ • Login         │    │ • Query         │    │ • Device Data   │
│ • Register      │    │ • History       │    │ • User Summary  │
│ • Token Verify  │    │ • Intents       │    │ • Analytics     │
│ • Profile       │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    WebSocket Service                            │
│                    (Port 8003)                                 │
│                                                                 │
│ • Real-time Chat                                               │
│ • Live Energy Updates                                          │
│ • Device Status                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Authentication Flow

### 1. User Registration & Login
1. User registers/logs in through the `auth_service`
2. `auth_service` validates credentials and issues JWT token
3. Token contains user ID, email, role, and expiration time

### 2. Token Verification
1. Client includes JWT token in `Authorization: Bearer <token>` header
2. Each service verifies token with `auth_service` via `/verify-token` endpoint
3. If `auth_service` is unavailable, services fall back to local JWT verification
4. User data is cached in Redis for performance

### 3. Protected Endpoints
All sensitive endpoints require valid JWT tokens:
- Chat queries and history
- Device telemetry data
- User-specific analytics
- WebSocket connections

## Service Integration

### Auth Service (`auth_service`)
- **Port**: 8000
- **Endpoints**:
  - `POST /register` - User registration
  - `POST /login` - User authentication
  - `POST /verify-token` - Token verification
  - `POST /logout` - Token blacklisting
  - `GET /profile` - User profile
  - `GET /users` - Admin user management

### Chat Service (`chat_service`)
- **Port**: 8001
- **Authentication**: Required for all endpoints
- **Protected Endpoints**:
  - `POST /query` - Process chat queries
  - `GET /history` - Get chat history
  - `GET /intents` - Get supported intents

### Telemetry Service (`telemetry_service`)
- **Port**: 8002
- **Authentication**: Required for user-specific endpoints
- **Protected Endpoints**:
  - `GET /user/devices` - User device summary
  - `GET /user/summary` - User energy summary
  - `GET /device/{id}` - Device telemetry (with auth)
  - `DELETE /device/{id}/telemetry` - Delete telemetry data

### WebSocket Service (`websocket_service`)
- **Port**: 8003
- **Authentication**: Required for all real-time features
- **Protected Features**:
  - Chat messages
  - Device telemetry subscriptions
  - Energy updates
  - Room subscriptions

## Security Features

### 1. Token Blacklisting
- Logout endpoint blacklists tokens in Redis
- Blacklisted tokens are rejected during verification
- Automatic cleanup when tokens expire

### 2. Role-Based Access Control
- Admin endpoints require admin role
- User endpoints only return user's own data
- Device access verified against user ownership

### 3. Rate Limiting & Caching
- Redis caching for user data and tokens
- Configurable token expiration times
- Fallback authentication when auth service is down

## Configuration

### Environment Variables
```bash
# Auth Service
JWT_SECRET=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REDIS_URL=redis://localhost:6379

# Other Services
AUTH_SERVICE_URL=http://localhost:8000
REDIS_URL=redis://localhost:6379
```

### Redis Configuration
- User data caching: 5 minutes
- Token blacklisting: Same as token expiration
- Connection pooling for high availability

## Usage Examples

### Frontend Authentication
```javascript
// Login
const response = await fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password })
});

const { access_token } = await response.json();

// Use token for authenticated requests
const chatResponse = await fetch('/api/chat/query', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ question: 'How much energy...' })
});
```

### WebSocket Authentication
```javascript
const ws = new WebSocket('ws://localhost:8003');

ws.onopen = () => {
  // Authenticate immediately after connection
  ws.send(JSON.stringify({
    type: 'authentication',
    payload: { token: access_token }
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'authentication' && data.message === 'Authentication successful') {
    // Now can send other messages
    ws.send(JSON.stringify({
      type: 'subscribe',
      payload: { room: 'energy_updates' }
    }));
  }
};
```

## Testing

Run the authentication integration test:
```bash
cd backend
python test_auth_integration.py
```

This will test:
- User registration and login
- Token verification
- Protected endpoint access
- Unauthenticated access rejection

## Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Check if token is expired
   - Verify token format in Authorization header
   - Ensure auth service is running

2. **403 Forbidden**
   - Check user role permissions
   - Verify user owns the requested resource

3. **500 Internal Server Error**
   - Check Redis connection
   - Verify database connectivity
   - Check service logs for detailed errors

### Debug Mode
Enable debug logging by setting:
```bash
ENVIRONMENT=development
```

This will show detailed error messages and enable service documentation endpoints.

## Security Best Practices

1. **Token Management**
   - Use HTTPS in production
   - Implement token refresh mechanism
   - Set appropriate expiration times

2. **Rate Limiting**
   - Implement per-user rate limiting
   - Monitor for suspicious activity
   - Use Redis for distributed rate limiting

3. **Input Validation**
   - Validate all user inputs
   - Sanitize data before database operations
   - Use parameterized queries

4. **Monitoring**
   - Log authentication attempts
   - Monitor failed login attempts
   - Track token usage patterns
