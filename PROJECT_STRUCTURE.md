# Smart Home Energy Monitoring - Project Structure

## 🏗️ Architecture Overview

This project uses a modern microservices architecture with AWS cloud services for scalability and reliability.

### Backend Services (FastAPI + Node.js)
- **Auth Service** (FastAPI): User authentication, JWT management, role-based access
- **Telemetry Service** (FastAPI): Device data ingestion and storage
- **Chat Service** (FastAPI): Natural language query processing and AI responses
- **WebSocket Service** (Node.js): Real-time communication for live updates and chat

### Frontend (React.js)
- **React SPA**: Modern UI with authentication, device management, and real-time chat
- **Real-time Updates**: WebSocket integration for live energy consumption data
- **Responsive Design**: Mobile-first approach with modern UI components

### Database & Storage
- **PostgreSQL**: Primary database for users, devices, and telemetry (RDS)
- **Redis**: Caching and session management (ElastiCache)
- **S3**: Static file storage and data backups

## 📁 Folder Structure

```
smart-home-energy/
├── backend/                          # Backend services
│   ├── auth_service/                 # FastAPI authentication service
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── main.py
│   ├── telemetry_service/            # FastAPI telemetry service
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── main.py
│   ├── chat_service/                 # FastAPI AI chat service
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── main.py
│   ├── websocket_service/            # Node.js WebSocket service
│   │   ├── src/
│   │   ├── package.json
│   │   ├── Dockerfile
│   │   └── server.js
│   └── shared/                       # Shared utilities and models
│       ├── models/                   # Database models and schemas
│       ├── database/                 # Database connection and migrations
│       └── utils/                    # Common utilities e.g Auth
├── frontend/                         # React frontend application
│   ├── src/
│   │   ├── components/               # Reusable UI components
│   │   ├── pages/                    # Page components
│   │   └── services/                 # API service calls
│   ├── public/
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
├── deployment/                       # Deployment configurations
│   ├── aws/                         # AWS-specific deployments
│   │   ├── terraform/               # Infrastructure as Code
│   │   │   ├── modules/             # Reusable Terraform modules
│   │   │   └── environments/        # Environment-specific configs
│   │   └── scripts/                 # Deployment scripts
├── database/                         # Database schemas and migrations
│   ├── init.sql                     # Initial database setup
├── .github/                         # GitHub Actions CI/CD
├── README.md                        # Project overview
└── PROJECT_STRUCTURE.md             # This file
```

## 🔧 Local Development

### Prerequisites
- Docker and Docker Compose
- Python 3.9+
- Node.js 18+
- AWS CLI (for deployment)

### Quick Start
```bash
# Start all services locally
docker-compose up -d

# Access services
# Frontend: http://localhost:3000
# Auth API: http://localhost:8000
# Telemetry API: http://localhost:8001
# Chat API: http://localhost:8002
# WebSocket: ws://localhost:8003
```