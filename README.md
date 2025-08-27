# Smart Home Energy Monitoring with Conversational AI

A comprehensive platform for monitoring smart home energy consumption through natural language queries and interactive dashboards.

## 🏗️ System Architecture

The system is built as a microservices architecture with three main backend services:

- **Auth Service** (Port 8000): Handles user authentication, JWT tokens, and role management
- **Telemetry Service** (Port 8001): Ingests and stores device energy consumption data
- **Chat Service** (Port 8002): Processes natural language queries and returns structured responses
- **Frontend** (Port 3000): React SPA with authentication, device management, and chat interface
- **PostgreSQL** (Port 5432): Primary data store for users, devices, and telemetry

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)

### Running the System
```bash
# Clone and setup
git clone <repository-url>
cd smart-home-energy

# Start all services
docker-compose up -d

# The system will be available at:
# Frontend: http://localhost:3000
# Auth API: http://localhost:8000
# Telemetry API: http://localhost:8001
# Chat API: http://localhost:8002
```

### Generate Sample Data
```bash
# Run the telemetry simulation script
python scripts/generate_telemetry.py
```

## 📚 API Documentation

### Auth Service (`/api/auth`)
- `POST /register` - User registration
- `POST /login` - User authentication
- `GET /profile` - Get user profile (protected)

### Telemetry Service (`/api/telemetry`)
- `POST /` - Submit device telemetry
- `GET /device/:deviceId` - Get device telemetry data
- `GET /user/:userId/devices` - Get user's devices

### Chat Service (`/api/chat`)
- `POST /query` - Submit natural language question
- `GET /history` - Get chat history (protected)

## 💬 Example Queries

The conversational AI can handle questions like:
- "How much energy did my fridge use yesterday?"
- "Which of my devices are using the most power?"
- "What's my total energy consumption this week?"
- "Show me the top 3 energy-consuming devices today"

## 🧪 Testing

```bash
# Run unit tests
npm test

# Run integration tests
npm run test:integration
```

## 🔧 Development

### Project Structure
```
smart-home-energy/
├── services/
│   ├── auth-service/          # Authentication service
│   ├── telemetry-service/     # Data ingestion service
│   └── chat-service/          # AI query service
├── frontend/                  # React application
├── database/                  # Database migrations and seeds
├── docker-compose.yml         # Service orchestration
└── scripts/                   # Utility scripts
```

### Adding New Services
1. Create service directory in `services/`
2. Add Dockerfile
3. Update `docker-compose.yml`
4. Add service to API gateway if needed

## 📊 Data Flow

1. **Device Telemetry**: IoT devices send energy data to Telemetry Service
2. **Data Storage**: Telemetry Service stores data in PostgreSQL with timestamps
3. **User Queries**: Users ask questions through Chat Service
4. **Query Processing**: Chat Service interprets intent and queries relevant data
5. **Response Generation**: Structured responses with summaries and time-series data
6. **Frontend Display**: React app renders responses and visualizations

## 🚧 Assumptions & Limitations

- **Data Granularity**: Telemetry data is collected at 1-minute intervals
- **Device Identification**: Devices are identified by UUIDs
- **Time Zones**: All timestamps are stored in UTC
- **Query Complexity**: Natural language queries are processed using rule-based parsing
- **Real-time Updates**: Frontend polls for updates every 30 seconds

## 🔮 Future Enhancements

- Real-time WebSocket updates
- Machine learning for energy consumption predictions
- Advanced analytics and reporting
- Mobile app support
- Integration with smart home platforms (Alexa, Google Home)

## 📝 License

MIT License - see LICENSE file for details
