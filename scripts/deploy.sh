#!/bin/bash
set -e

echo "🚀 Deploying DevOps Automation Stack..."

# Vérifier les prérequis
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed. Aborting." >&2; exit 1; }

# Vérifier le fichier .env
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before continuing."
    exit 1
fi

# Construire et démarrer les services
echo "📦 Building Docker images..."
docker-compose build

echo "🎬 Starting services..."
docker-compose up -d

# Attendre que les services soient prêts
echo "⏳ Waiting for services to be ready..."
sleep 10

# Vérifier l'état des services
echo "✅ Checking service health..."
docker-compose ps

# Afficher les URLs
echo ""
echo "✨ Deployment complete!"
echo "📊 Prometheus: http://localhost:9090"
echo "🔔 AlertManager: http://localhost:9093"
echo "🪝 Flask Webhook: http://localhost:5000"
echo ""
echo "📝 View logs: docker-compose logs -f"
echo "🛑 Stop services: docker-compose down"
