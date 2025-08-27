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
│   │   ├── app/
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── main.py
│   ├── telemetry_service/            # FastAPI telemetry service
│   │   ├── app/
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── main.py
│   ├── chat_service/                 # FastAPI AI chat service
│   │   ├── app/
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
│       └── utils/                    # Common utilities
├── frontend/                         # React frontend application
│   ├── src/
│   │   ├── components/               # Reusable UI components
│   │   ├── pages/                    # Page components
│   │   ├── services/                 # API service calls
│   │   ├── utils/                    # Utility functions
│   │   └── styles/                   # CSS and styling
│   ├── public/
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
├── deployment/                       # Deployment configurations
│   ├── aws/                         # AWS-specific deployments
│   │   ├── terraform/               # Infrastructure as Code
│   │   │   ├── modules/             # Reusable Terraform modules
│   │   │   └── environments/        # Environment-specific configs
│   │   ├── cloudformation/          # CloudFormation templates
│   │   └── scripts/                 # Deployment scripts
│   ├── docker-compose.yml           # Local development
│   └── docker-compose.prod.yml      # Production-like local testing
├── database/                         # Database schemas and migrations
│   ├── init.sql                     # Initial database setup
│   └── migrations/                  # Database migration files
├── scripts/                          # Utility scripts
│   ├── generate_telemetry.py        # Telemetry data generator
│   └── deploy.sh                    # Deployment automation
├── docs/                            # Documentation
├── tests/                           # Test suites
├── .github/                         # GitHub Actions CI/CD
├── README.md                        # Project overview
└── PROJECT_STRUCTURE.md             # This file
```

## 🚀 AWS Services Architecture

### Core Infrastructure
- **VPC**: Private and public subnets across multiple AZs
- **EC2**: Application servers (can be replaced with ECS/Fargate)
- **RDS**: PostgreSQL database with Multi-AZ deployment
- **ElastiCache**: Redis for caching and session management
- **S3**: Static file storage and data backups
- **CloudFront**: CDN for frontend assets

### Application Services
- **ECS/Fargate**: Container orchestration (alternative to EC2)
- **Application Load Balancer**: Traffic distribution and SSL termination
- **Route 53**: DNS management and health checks
- **CloudWatch**: Monitoring, logging, and alerting
- **IAM**: Security and access management

### Development & Deployment
- **CodePipeline**: CI/CD pipeline automation
- **CodeBuild**: Build and test automation
- **CodeDeploy**: Deployment automation
- **S3**: Artifact storage
- **CloudFormation/Terraform**: Infrastructure as Code

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

## 🌐 Production Deployment

### AWS Deployment Options

#### Option 1: ECS/Fargate (Recommended)
- **Pros**: Serverless, auto-scaling, managed container service
- **Use Case**: Production workloads with variable traffic

#### Option 2: EC2 with Auto Scaling
- **Pros**: Full control, cost-effective for steady traffic
- **Use Case**: Predictable workloads, cost optimization

#### Option 3: Lambda + API Gateway
- **Pros**: Serverless, pay-per-use, auto-scaling
- **Use Case**: Event-driven workloads, cost optimization

### Deployment Commands
```bash
# Deploy to AWS using Terraform
cd deployment/aws/terraform/environments/dev
terraform init
terraform plan
terraform apply

# Deploy using CloudFormation
aws cloudformation deploy \
  --template-file deployment/aws/cloudformation/main.yaml \
  --stack-name smart-home-energy \
  --capabilities CAPABILITY_IAM
```

## 📊 Monitoring & Observability

### AWS CloudWatch
- **Metrics**: CPU, memory, database performance
- **Logs**: Centralized logging across all services
- **Alarms**: Automated alerting for critical issues
- **Dashboards**: Custom monitoring dashboards

### Application Monitoring
- **Health Checks**: Service health endpoints
- **Performance Metrics**: Response times, error rates
- **Business Metrics**: User activity, energy consumption trends

## 🔒 Security

### Network Security
- **VPC**: Private subnets for databases, public for load balancers
- **Security Groups**: Restrictive access controls
- **NACLs**: Network-level access control

### Application Security
- **JWT Tokens**: Secure authentication
- **HTTPS**: SSL/TLS encryption
- **IAM Roles**: Least privilege access
- **Secrets Management**: AWS Secrets Manager for sensitive data

## 💰 Cost Optimization

### Free Tier Benefits
- **EC2**: 750 hours/month for 12 months
- **RDS**: 750 hours/month for 12 months
- **S3**: 5GB storage for 12 months
- **CloudFront**: 1TB data transfer for 12 months

### Cost Optimization Strategies
- **Reserved Instances**: For predictable workloads
- **Spot Instances**: For non-critical workloads
- **Auto Scaling**: Scale down during low traffic
- **S3 Lifecycle**: Archive old data to cheaper storage

## 🚧 Development Phases

### Phase 1: Core Infrastructure
- [ ] AWS VPC and networking setup
- [ ] RDS PostgreSQL database
- [ ] Basic FastAPI services
- [ ] React frontend

### Phase 2: Real-time Features
- [ ] WebSocket service implementation
- [ ] Real-time chat functionality
- [ ] Live energy consumption updates

### Phase 3: Production Ready
- [ ] CI/CD pipeline setup
- [ ] Monitoring and alerting
- [ ] Security hardening
- [ ] Performance optimization

### Phase 4: Advanced Features
- [ ] Machine learning integration
- [ ] Advanced analytics
- [ ] Mobile app support
- [ ] Third-party integrations
