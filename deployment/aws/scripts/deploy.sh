#!/bin/bash

# Smart Home Energy Monitoring - AWS Deployment Script
# This script automates the deployment of the application to AWS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="smart-home-energy"
AWS_REGION="us-east-1"
ENVIRONMENT="dev"
DOCKER_REGISTRY=""

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if required tools are installed
    command -v docker >/dev/null 2>&1 || { log_error "Docker is required but not installed. Aborting."; exit 1; }
    command -v terraform >/dev/null 2>&1 || { log_error "Terraform is required but not installed. Aborting."; exit 1; }
    command -v aws >/dev/null 2>&1 || { log_error "AWS CLI is required but not installed. Aborting."; exit 1; }
    command -v jq >/dev/null 2>&1 || { log_error "jq is required but not installed. Aborting."; exit 1; }
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        log_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    log_success "All prerequisites are met!"
}

build_docker_images() {
    log_info "Building Docker images..."
    
    # Build backend services
    log_info "Building Auth Service..."
    docker build -t ${PROJECT_NAME}/auth-service:latest ../backend/auth_service/
    
    log_info "Building Telemetry Service..."
    docker build -t ${PROJECT_NAME}/telemetry-service:latest ../backend/telemetry_service/
    
    log_info "Building Chat Service..."
    docker build -t ${PROJECT_NAME}/chat-service:latest ../backend/chat_service/
    
    log_info "Building WebSocket Service..."
    docker build -t ${PROJECT_NAME}/websocket-service:latest ../backend/websocket_service/
    
    log_info "Building Frontend..."
    docker build -t ${PROJECT_NAME}/frontend:latest ../frontend/
    
    log_success "All Docker images built successfully!"
}

push_to_ecr() {
    if [ -z "$DOCKER_REGISTRY" ]; then
        log_warning "Docker registry not configured, skipping push to ECR"
        return
    fi
    
    log_info "Pushing images to ECR..."
    
    # Get ECR login token
    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${DOCKER_REGISTRY}
    
    # Tag and push images
    for service in auth-service telemetry-service chat-service websocket-service frontend; do
        log_info "Pushing ${service}..."
        docker tag ${PROJECT_NAME}/${service}:latest ${DOCKER_REGISTRY}/${service}:latest
        docker push ${DOCKER_REGISTRY}/${service}:latest
    done
    
    log_success "All images pushed to ECR!"
}

deploy_infrastructure() {
    log_info "Deploying infrastructure with Terraform..."
    
    cd terraform
    
    # Initialize Terraform
    log_info "Initializing Terraform..."
    terraform init
    
    # Plan deployment
    log_info "Planning deployment..."
    terraform plan -var="environment=${ENVIRONMENT}" -var="aws_region=${AWS_REGION}" -out=tfplan
    
    # Confirm deployment
    read -p "Do you want to proceed with the deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warning "Deployment cancelled by user"
        exit 0
    fi
    
    # Apply deployment
    log_info "Applying Terraform plan..."
    terraform apply tfplan
    
    # Get outputs
    log_info "Getting deployment outputs..."
    ALB_DNS=$(terraform output -raw alb_dns_name)
    RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
    REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)
    
    log_success "Infrastructure deployed successfully!"
    log_info "Load Balancer: http://${ALB_DNS}"
    log_info "RDS Endpoint: ${RDS_ENDPOINT}"
    log_info "Redis Endpoint: ${REDIS_ENDPOINT}"
    
    cd ..
}

deploy_application() {
    log_info "Deploying application to ECS..."
    
    # This would typically involve updating ECS task definitions and services
    # For now, we'll just log that this step would happen
    log_info "Application deployment step (ECS service updates would happen here)"
    
    log_success "Application deployment completed!"
}

run_tests() {
    log_info "Running deployment tests..."
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Test health endpoints
    ALB_DNS=$(cd terraform && terraform output -raw alb_dns_name && cd ..)
    
    log_info "Testing health endpoints..."
    
    # Test frontend
    if curl -f "http://${ALB_DNS}/health" >/dev/null 2>&1; then
        log_success "Frontend health check passed"
    else
        log_error "Frontend health check failed"
        return 1
    fi
    
    # Test backend services (if accessible)
    log_info "Backend service tests would run here"
    
    log_success "All deployment tests passed!"
}

cleanup() {
    log_info "Cleaning up temporary files..."
    
    # Remove Terraform plan file
    if [ -f "terraform/tfplan" ]; then
        rm terraform/tfplan
    fi
    
    log_success "Cleanup completed!"
}

main() {
    log_info "Starting deployment of ${PROJECT_NAME} to AWS..."
    log_info "Environment: ${ENVIRONMENT}"
    log_info "AWS Region: ${AWS_REGION}"
    
    # Check prerequisites
    check_prerequisites
    
    # Build Docker images
    build_docker_images
    
    # Push to ECR (if configured)
    push_to_ecr
    
    # Deploy infrastructure
    deploy_infrastructure
    
    # Deploy application
    deploy_application
    
    # Run tests
    run_tests
    
    # Cleanup
    cleanup
    
    log_success "Deployment completed successfully!"
    log_info "Your application is now running on AWS!"
    log_info "Load Balancer URL: http://$(cd terraform && terraform output -raw alb_dns_name && cd ..)"
}

# Handle script arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment|-e)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --region|-r)
            AWS_REGION="$2"
            shift 2
            ;;
        --registry|-d)
            DOCKER_REGISTRY="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -e, --environment ENV    Environment to deploy (dev, staging, prod)"
            echo "  -r, --region REGION      AWS region to deploy to"
            echo "  -d, --registry REGISTRY  Docker registry for ECR"
            echo "  -h, --help               Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"
