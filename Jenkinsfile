pipeline {
    agent any

    environment {
        PYTHON = 'C:\\Users\\TiwariG\\AppData\\Local\\Programs\\Python\\Python310\\python.exe'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Python Version') {
            steps {
                bat '"%PYTHON%" --version'
            }
        }

        stage('Install Dependencies') {
            steps {
                bat '"%PYTHON%" -m pip install --upgrade pip'
                bat '"%PYTHON%" -m pip install -r requirements.txt'
            }
        }

        stage('Syntax Check') {
            steps {
                bat '"%PYTHON%" -m py_compile app.py'
            }
        }

        stage('Docker Build') {
            steps {
                bat 'docker build -t attendance-app .'
            }
        }

        stage('Deploy Container') {
            steps {
                bat 'docker rm -f attendance-container || exit 0'
                bat 'docker run -d -p 5000:5000 --name attendance-container attendance-app'
            }
        }

        stage('Build') {
            steps {
                bat 'echo Attendance App Build Successful'
            }
        }
    }

    post {

        success {
            echo 'Pipeline executed successfully'
        }

        failure {
            echo 'Pipeline failed'
        }

        always {
            echo 'Pipeline execution completed'
        }
    }
}