pipeline {
    agent {
        label "centos7-generic"
    }

    stages {
        stage('test') {
            steps {
                sh """
                python3.6 -m venv env
                . env/bin/activate
                pip install --upgrade pip setuptools
                pip install -e .[test]
                pytest
                """
            }
        }
        stage('package') {
            steps {
                sh """
                rm -rf dist

                python3.6 -m venv env
                . env/bin/activate
                pip install --upgrade pip setuptools wheel
                python setup.py sdist bdist_wheel
                """
            }
        }
        stage('approve-deploy') {
            agent none
            steps {
                timeout(time: 14, unit: 'DAYS') {
                    input message: 'Deploy to prod?'
                }
            }
        }
        stage('deploy') {
            environment {
                TWINE = credentials('pypi-cmbrad')
            }
            steps {
                sh """
                export TWINE_USERNAME=${TWINE_USR}
                export TWINE_PASSWORD=${TWINE_PSW}

                python3.6 -m venv env
                . env/bin/activate
                pip install --upgrade pip setuptools
                pip install twine

                twine upload dist/*
                """
            }
        }
    }

    post {
        always {
            cleanWs()
        }
    }
}
