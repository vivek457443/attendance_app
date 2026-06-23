pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                echo 'Code fetched successfully'
            }
        }

        stage('Build') {
            steps {
                bat 'echo Building Attendance App'
            }
        }

        stage('Test') {
            steps {
                bat 'echo Running Tests'
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
    }
}