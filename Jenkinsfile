pipeline {
    agent any

    environment {
        APP_NAME        = "ride-mate-ml"
        IMAGE_NAME      = "ride-mate-ml"
        IMAGE_TAG       = "${BUILD_NUMBER}"
        CONTAINER_NAME  = "ride-mate-ml"
        APP_PORT        = "9090"
        ENV_FILE        = "/opt/jenkins-env/ride-mate-ml.env"
        GIT_BRANCH      = "main"
        REPO_URL        = "https://github.com/TishanGamage/ride-mate-ml"
        GIT_CREDENTIALS_ID = "github-finegrained-pat"
    }

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {

        stage('Clone Repository') {
            steps {
                echo "Cloning branch: ${GIT_BRANCH} from ${REPO_URL}"
                git branch: "${GIT_BRANCH}",
                    url: "${REPO_URL}",
                    credentialsId: "${GIT_CREDENTIALS_ID}"
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "Building image: ${IMAGE_NAME}:${IMAGE_TAG}"
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
                sh "docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest"
            }
        }

        stage('Stop Old Container') {
            steps {
                sh '''#!/bin/bash
set -euo pipefail

# Stop running container if it exists
if docker ps -q --filter "name=^${CONTAINER_NAME}$" | grep -q .; then
    echo "Stopping container: ${CONTAINER_NAME}"
    docker stop "${CONTAINER_NAME}"
fi

# Remove container (stopped or exited) if it exists
if docker ps -a -q --filter "name=^${CONTAINER_NAME}$" | grep -q .; then
    echo "Removing container: ${CONTAINER_NAME}"
    docker rm "${CONTAINER_NAME}"
fi
'''
            }
        }

        stage('Run Container') {
            steps {
                sh '''#!/bin/bash
set -euo pipefail

echo "Starting container: ${CONTAINER_NAME} on port ${APP_PORT}"

if [ -f "${ENV_FILE}" ]; then
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart unless-stopped \
        -p "${APP_PORT}":"${APP_PORT}" \
        --env-file "${ENV_FILE}" \
        -e PORT="${APP_PORT}" \
        "${IMAGE_NAME}":latest
else
    echo "WARNING: ENV_FILE not found at ${ENV_FILE}. Starting without it."
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart unless-stopped \
        -p "${APP_PORT}":"${APP_PORT}" \
        -e PORT="${APP_PORT}" \
        "${IMAGE_NAME}":latest
fi
'''
            }
        }


        stage('Health Check') {
            steps {
                sh '''#!/bin/bash
set -euo pipefail

echo "Waiting for container to be ready..."

for i in $(seq 1 20); do
    echo "Health check attempt ${i}/20..."
    if curl -fsS "http://127.0.0.1:${APP_PORT}/health" -o /tmp/ride-mate-health.json; then
        echo "Health check passed:"
        cat /tmp/ride-mate-health.json

        # Optional: verify model_loaded=true in JSON response
        # Requires jq to be installed on the Jenkins agent
        # if command -v jq &>/dev/null; then
        #     MODEL_STATUS=$(jq -r '.model_loaded' /tmp/ride-mate-health.json)
        #     if [ "$MODEL_STATUS" != "true" ]; then
        #         echo "Model not loaded yet, retrying..."
        #         sleep 3
        #         continue
        #     fi
        # fi

        exit 0
    fi
    sleep 3
done

echo "Health check failed after 20 attempts."
echo "--- Container logs ---"
docker logs "${CONTAINER_NAME}" || true
exit 1
'''
            }
        }


        stage('Cleanup Old Images') {
            steps {
                sh '''#!/bin/bash
set -euo pipefail

echo "Removing dangling Docker images..."
docker image prune -f

# Keep only the last 5 numbered builds of this image; remove the rest
echo "Removing old tagged images (keeping last 5 builds)..."
docker images "${IMAGE_NAME}" --format "{{.Tag}}" \
    | grep -E '^[0-9]+$' \
    | sort -n \
    | head -n -5 \
    | xargs -r -I {} docker rmi "${IMAGE_NAME}:{}" || true
'''
            }
        }
    }

    post {
        success {
            echo "✅ Deployment successful: ${APP_NAME}:${IMAGE_TAG} is running on port ${APP_PORT}"
        }
        failure {
            echo "❌ Deployment failed. Check stage logs above."
            // Optional: dump container logs on failure for easier debugging
            sh "docker logs ${CONTAINER_NAME} || true"
        }
        always {

            cleanWs()
        }
    }
}