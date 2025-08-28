# Smart Home Energy Monitoring with Conversational AI

A comprehensive platform for monitoring smart home energy consumption through natural language queries and interactive dashboards.

## 🏗️ System Architecture

The system is built as a microservices architecture with four main backend services:

- **Auth Service** (Port 8000): Handles user authentication, JWT tokens, and role management
- **Telemetry Service** (Port 8001): Ingests and stores device energy consumption data
- **Chat Service** (Port 8002): Processes natural language queries and returns structured responses
- **WebSocket Service** (Port 8003): Provides real-time communication and live energy updates
- **Frontend** (Port 3000): React SPA with authentication, device management, and chat interface
- **PostgreSQL** (Port 5432): Primary data store for users, devices, and telemetry
- **Redis** (Port 6379): Caching and real-time messaging

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for backend services)

### Running the System
```bash
# Clone and setup
git clone git@github.com:faizanhaider/smart-home-energy.git
cd smart-home-energy

# Start all services
docker-compose up -d

# The system will be available at:
# Frontend: http://localhost:3000
# Auth API: http://localhost:8000
# Telemetry API: http://localhost:8001
# Chat API: http://localhost:8002
# WebSocket: ws://localhost:8003
```

### Generate Sample Data
```bash
# Run the telemetry simulation script
cd backend/telemetry_service
python scripts/generate_telemetry.py
```

## 📚 API Documentation

### Auth Service (`/api/auth`)
- `POST /register` - User registration
- `POST /login` - User authentication
- `GET /profile` - Get user profile (protected)
- `POST /verify-token` - Verify JWT token validity

### Telemetry Service (`/api/telemetry`)
- `POST /` - Submit device telemetry
- `GET /device/:deviceId` - Get device telemetry data
- `GET /user/:userId/devices` - Get user's devices
- `GET /analytics/energy-cost` - Calculate energy costs
- `GET /analytics/trends` - Analyze energy consumption trends

### Chat Service (`/api/chat`)
- `POST /query` - Submit natural language question
- `GET /history` - Get chat history (protected)
- `GET /intents` - Get supported query intents

### WebSocket Service (`ws://localhost:8003`)
- Real-time device telemetry updates
- Live energy consumption monitoring
- System notifications
- User authentication and subscription management

## 💬 Example Queries

The conversational AI can handle questions like:
- "How much energy did my fridge use yesterday?"
- "Which of my devices are using the most power?"
- "What's my total energy consumption this week?"
- "Show me the top 3 energy-consuming devices today"
- "Calculate my energy costs for this month"

## 🧪 Testing

```bash
# Run Python backend integration tests
cd backend
python test_auth_integration

# Individual services have their own tests
```

## 🔧 Development

### Project Structure
```
smart-home-energy/
├── backend/
│   ├── auth_service/          # Authentication service
│   ├── telemetry_service/     # Data ingestion service
│   ├── chat_service/          # AI query service
│   ├── websocket_service/     # Real-time communication
│   └── shared/                # Shared models and utilities
├── frontend/                  # React application
├── database/                  # Database migrations and seeds
└── docker-compose.yml         # Service orchestration
```

### Adding New Services
1. Create service directory in `backend/`
2. Add Dockerfile and requirements.txt
3. Update `docker-compose.yml`
4. Add service to API gateway if needed

## 📊 Data Flow

1. **Device Telemetry**: IoT devices send energy data to Telemetry Service
2. **Data Storage**: Telemetry Service stores data in PostgreSQL with timestamps
3. **Real-time Updates**: WebSocket Service broadcasts live updates to connected clients
4. **User Queries**: Users ask questions through Chat Service
5. **Query Processing**: Chat Service interprets intent and queries relevant data
6. **Response Generation**: Structured responses with summaries and time-series data
7. **Frontend Display**: React app renders responses and visualizations

## 🚧 Assumptions & Limitations

- **Data Granularity**: Telemetry data is collected at 1-minute intervals
- **Device Identification**: Devices are identified by UUIDs
- **Time Zones**: All timestamps are stored in UTC
- **Query Complexity**: Natural language queries are processed using rule-based parsing and OpenAI integration
- **Real-time Updates**: WebSocket service provides live updates for connected clients
- **Authentication**: JWT-based authentication with Redis session management

## 🔮 Future Enhancements

- Machine learning for energy consumption predictions
- Advanced analytics and reporting
- Mobile app support
- Integration with smart home platforms (Alexa, Google Home)
- Energy efficiency recommendations
- Cost optimization algorithms

## 📝 License

MIT License - see LICENSE file for details
