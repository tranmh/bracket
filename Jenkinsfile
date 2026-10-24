// The safety net of bracket, written by aqaa from what its QA run found: unit tests with coverage and its
// floor, integration tests against the databases they need, end-to-end tests, and lint, SAST and dependency
// checks (report only: a finding marks the stage unstable until it is triaged).
// Needs the plugins Pipeline, Docker Pipeline, JUnit, Coverage, Timestamper and Workspace Cleanup;
// integration stages run on an agent labelled 'docker'.
pipeline {
  agent none
  options {
    timeout(time: 90, unit: 'MINUTES')
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '10'))
    disableConcurrentBuilds(abortPrevious: true)
  }
  environment {
    CI = 'true'
  }
  stages {
    stage('Tests') {
      parallel {
        stage('Unit: nextjs docs') {
          agent { docker { image 'node:22-bookworm' } }
          options { timeout(time: 30, unit: 'MINUTES') }
          steps {
            dir('docs') {
              sh '''
                set -eu
                mkdir -p test-reports
                corepack enable
                yarn install --frozen-lockfile
                npm install --no-save --no-audit --no-fund "@vitest/coverage-v8@$(node -p "require('vitest/package.json').version")"
                npx vitest run --coverage --coverage.reporter=cobertura --coverage.reportsDirectory=test-reports/coverage --reporter=default --reporter=junit --outputFile.junit=test-reports/unit.xml --exclude '**/*.integration.test.*' --exclude 'e2e/**'
              '''
            }
          }
          post {
            always {
              junit allowEmptyResults: true, testResults: 'docs/test-reports/*.xml'
              recordCoverage id: 'coverage-nextjs-docs', name: 'Coverage nextjs docs', tools: [[parser: 'COBERTURA', pattern: 'docs/test-reports/coverage/cobertura-coverage.xml']], sourceDirectories: [[path: 'docs']]
              archiveArtifacts allowEmptyArchive: true, artifacts: 'docs/test-reports/**'
            }
            cleanup {
              cleanWs deleteDirs: true, notFailBuild: true
            }
          }
        }
        stage('Unit: nextjs frontend') {
          agent { docker { image 'node:22-bookworm' } }
          options { timeout(time: 30, unit: 'MINUTES') }
          steps {
            dir('frontend') {
              sh '''
                set -eu
                mkdir -p test-reports
                corepack enable
                yarn install --frozen-lockfile
                npm install --no-save --no-audit --no-fund jest-junit@17.0.0
                JEST_JUNIT_OUTPUT_DIR=test-reports JEST_JUNIT_OUTPUT_NAME=unit.xml npx jest --ci --coverage --coverageReporters=cobertura --coverageDirectory=test-reports/coverage --reporters=default --reporters=jest-junit --testPathIgnorePatterns integration e2e
              '''
            }
          }
          post {
            always {
              junit allowEmptyResults: true, testResults: 'frontend/test-reports/*.xml'
              recordCoverage id: 'coverage-nextjs-frontend', name: 'Coverage nextjs frontend', tools: [[parser: 'COBERTURA', pattern: 'frontend/test-reports/coverage/cobertura-coverage.xml']], sourceDirectories: [[path: 'frontend']]
              archiveArtifacts allowEmptyArchive: true, artifacts: 'frontend/test-reports/**'
            }
            cleanup {
              cleanWs deleteDirs: true, notFailBuild: true
            }
          }
        }
        stage('End-to-end: nextjs frontend') {
          agent { docker { image 'mcr.microsoft.com/playwright:v1.56.1-noble' } }
          options { timeout(time: 45, unit: 'MINUTES') }
          steps {
            dir('frontend') {
              sh '''
                set -eu
                mkdir -p test-reports
                corepack enable
                yarn install --frozen-lockfile
                npm install --no-save --no-audit --no-fund jest-junit@17.0.0
                npx playwright install chromium
                PLAYWRIGHT_JUNIT_OUTPUT_NAME=test-reports/e2e.xml npx playwright test --reporter=junit,list
              '''
            }
          }
          post {
            always {
              junit allowEmptyResults: true, testResults: 'frontend/test-reports/*.xml'
              archiveArtifacts allowEmptyArchive: true, artifacts: 'frontend/test-reports/**'
            }
            cleanup {
              cleanWs deleteDirs: true, notFailBuild: true
            }
          }
        }
        stage('Unit: node standalone/electron') {
          agent { docker { image 'node:22-bookworm' } }
          options { timeout(time: 30, unit: 'MINUTES') }
          steps {
            dir('standalone/electron') {
              sh '''
                set -eu
                mkdir -p test-reports
                npm ci
                npm install --no-save --no-audit --no-fund "@vitest/coverage-v8@$(node -p "require('vitest/package.json').version")"
                npx vitest run --coverage --coverage.reporter=cobertura --coverage.reportsDirectory=test-reports/coverage --reporter=default --reporter=junit --outputFile.junit=test-reports/unit.xml --exclude '**/*.integration.test.*' --exclude 'e2e/**'
              '''
            }
          }
          post {
            always {
              junit allowEmptyResults: true, testResults: 'standalone/electron/test-reports/*.xml'
              recordCoverage id: 'coverage-node-standalone-electron', name: 'Coverage node standalone/electron', tools: [[parser: 'COBERTURA', pattern: 'standalone/electron/test-reports/coverage/cobertura-coverage.xml']], sourceDirectories: [[path: 'standalone/electron']]
              archiveArtifacts allowEmptyArchive: true, artifacts: 'standalone/electron/test-reports/**'
            }
            cleanup {
              cleanWs deleteDirs: true, notFailBuild: true
            }
          }
        }
        stage('Unit: python backend') {
          agent { docker { image 'python:3.13-slim' } }
          options { timeout(time: 30, unit: 'MINUTES') }
          steps {
            dir('backend') {
              sh '''
                set -eu
                . .venv-ci/bin/activate
                mkdir -p test-reports
                python -m venv .venv-ci
                . .venv-ci/bin/activate && python -m pip install --upgrade pip
                . .venv-ci/bin/activate && if [ -f pyproject.toml ]; then pip install -e '.[test,dev]' || pip install -e .; fi
                . .venv-ci/bin/activate && for f in requirements*.txt; do if [ -f "$f" ]; then pip install -r "$f"; fi; done
                . .venv-ci/bin/activate && pip install pytest==9.1.1 pytest-cov==7.1.0 ruff==0.17.2 'bandit[sarif]==1.9.4' pip-audit==2.10.1
                python -m pytest -q -m "not integration and not e2e" --junitxml=test-reports/unit.xml --cov=. --cov-report=xml:test-reports/coverage.xml || { rc=$?; [ "$rc" -eq 5 ] || exit "$rc"; }
              '''
            }
          }
          post {
            always {
              junit allowEmptyResults: true, testResults: 'backend/test-reports/*.xml'
              recordCoverage id: 'coverage-python-backend', name: 'Coverage python backend', tools: [[parser: 'COBERTURA', pattern: 'backend/test-reports/coverage.xml']], sourceDirectories: [[path: 'backend']], qualityGates: [[threshold: 85.0, metric: 'LINE', baseline: 'PROJECT', criticality: 'FAILURE']]
              archiveArtifacts allowEmptyArchive: true, artifacts: 'backend/test-reports/**'
            }
            cleanup {
              cleanWs deleteDirs: true, notFailBuild: true
            }
          }
        }
        stage('Integration: python backend') {
          agent { label 'docker' }
          options { timeout(time: 45, unit: 'MINUTES') }
          steps {
            script {
              docker.image('postgres:16-alpine').withRun('-e POSTGRES_USER=aqaa -e POSTGRES_PASSWORD=aqaa -e POSTGRES_DB=aqaa') { postgres ->
                docker.image('postgres:16-alpine').inside("--link ${postgres.id}:postgres") {
                  sh 'until pg_isready -h postgres -U aqaa -d aqaa; do sleep 1; done'
                }
                docker.image('python:3.13-slim').inside("--link ${postgres.id}:postgres -e AQAA_PG_URL=postgres://aqaa:aqaa@postgres:5432/aqaa?sslmode=disable -e DATABASE_URL=postgres://aqaa:aqaa@postgres:5432/aqaa?sslmode=disable -e 'AQAA_PG_CONNECTION_STRING=Host=postgres;Port=5432;Database=aqaa;Username=aqaa;Password=aqaa' -e AQAA_SQLITE_PATH=/tmp/aqaa.db") {
                  dir('backend') {
                    sh '''
                      set -eu
                      . .venv-ci/bin/activate
                      mkdir -p test-reports
                      python -m venv .venv-ci
                      . .venv-ci/bin/activate && python -m pip install --upgrade pip
                      . .venv-ci/bin/activate && if [ -f pyproject.toml ]; then pip install -e '.[test,dev]' || pip install -e .; fi
                      . .venv-ci/bin/activate && for f in requirements*.txt; do if [ -f "$f" ]; then pip install -r "$f"; fi; done
                      . .venv-ci/bin/activate && pip install pytest==9.1.1 pytest-cov==7.1.0 ruff==0.17.2 'bandit[sarif]==1.9.4' pip-audit==2.10.1
                      python -m pytest -q -m integration --junitxml=test-reports/integration.xml || { rc=$?; [ "$rc" -eq 5 ] || exit "$rc"; }
                    '''
                  }
                }
              }
            }
          }
          post {
            always {
              junit allowEmptyResults: true, testResults: 'backend/test-reports/*.xml'
              archiveArtifacts allowEmptyArchive: true, artifacts: 'backend/test-reports/**'
            }
            cleanup {
              cleanWs deleteDirs: true, notFailBuild: true
            }
          }
        }
        stage('Unit: python standalone') {
          agent { docker { image 'python:3.13-slim' } }
          options { timeout(time: 30, unit: 'MINUTES') }
          steps {
            dir('standalone') {
              sh '''
                set -eu
                . .venv-ci/bin/activate
                mkdir -p test-reports
                python -m venv .venv-ci
                . .venv-ci/bin/activate && python -m pip install --upgrade pip
                . .venv-ci/bin/activate && if [ -f pyproject.toml ]; then pip install -e '.[test,dev]' || pip install -e .; fi
                . .venv-ci/bin/activate && for f in requirements*.txt; do if [ -f "$f" ]; then pip install -r "$f"; fi; done
                . .venv-ci/bin/activate && pip install pytest==9.1.1 pytest-cov==7.1.0 ruff==0.17.2 'bandit[sarif]==1.9.4' pip-audit==2.10.1
                python -m pytest -q -m "not integration and not e2e" --junitxml=test-reports/unit.xml --cov=. --cov-report=xml:test-reports/coverage.xml || { rc=$?; [ "$rc" -eq 5 ] || exit "$rc"; }
              '''
            }
          }
          post {
            always {
              junit allowEmptyResults: true, testResults: 'standalone/test-reports/*.xml'
              recordCoverage id: 'coverage-python-standalone', name: 'Coverage python standalone', tools: [[parser: 'COBERTURA', pattern: 'standalone/test-reports/coverage.xml']], sourceDirectories: [[path: 'standalone']], qualityGates: [[threshold: 93.0, metric: 'LINE', baseline: 'PROJECT', criticality: 'FAILURE']]
              archiveArtifacts allowEmptyArchive: true, artifacts: 'standalone/test-reports/**'
            }
            cleanup {
              cleanWs deleteDirs: true, notFailBuild: true
            }
          }
        }
      }
    }
    stage('Checks') {
      parallel {
        stage('Checks: nextjs docs') {
          agent { docker { image 'node:22-bookworm' } }
          options { timeout(time: 30, unit: 'MINUTES') }
          steps {
            dir('docs') {
              sh '''
                set -eu
                mkdir -p test-reports
                corepack enable
                yarn install --frozen-lockfile
                npm install --no-save --no-audit --no-fund "@vitest/coverage-v8@$(node -p "require('vitest/package.json').version")"
              '''
              catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE', message: 'eslint found issues') {
                sh '''
                  set -eu
                  if ls eslint.config.* .eslintrc* >/dev/null 2>&1; then npx eslint .; else echo 'no ESLint configuration'; fi
                '''
              }
              catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE', message: 'tsc found issues') {
                sh '''
                  set -eu
                  npx tsc --noEmit
                '''
              }
              catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE', message: 'npm audit found issues') {
                sh '''
                  set -eu
                  npm audit --audit-level=high --omit=dev
                '''
              }
            }
          }
          post {
            always { archiveArtifacts allowEmptyArchive: true, artifacts: 'docs/test-reports/**' }
            cleanup { cleanWs deleteDirs: true, notFailBuild: true }
          }
        }
        stage('Checks: nextjs frontend') {
          agent { docker { image 'node:22-bookworm' } }
          options { timeout(time: 30, unit: 'MINUTES') }
          steps {
            dir('frontend') {
              sh '''
                set -eu
                mkdir -p test-reports
                corepack enable
                yarn install --frozen-lockfile
                npm install --no-save --no-audit --no-fund jest-junit@17.0.0
              '''
              catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE', message: 'eslint found issues') {
                sh '''
                  set -eu
                  if ls eslint.config.* .eslintrc* >/dev/null 2>&1; then npx eslint .; else echo 'no ESLint configuration'; fi
                '''
              }
              catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE', message: 'tsc found issues') {
                sh '''
                  set -eu
                  npx tsc --noEmit
                '''
              }
              catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE', message: 'npm audit found issues') {
                sh '''
                  set -eu
                  npm audit --audit-level=high --omit=dev
                '''
              }
            }
          }
          post {
            always { archiveArtifacts allowEmptyArchive: true, artifacts: 'frontend/test-reports/**' }
            cleanup { cleanWs deleteDirs: true, notFailBuild: true }
          }
        }
        stage('Checks: node standalone/electron') {
          agent { docker { image 'node:22-bookworm' } }
          options { timeout(time: 30, unit: 'MINUTES') }
          steps {
            dir('standalone/electron') {
              sh '''
                set -eu
                mkdir -p test-reports
                npm ci
                npm install --no-save --no-audit --no-fund "@vitest/coverage-v8@$(node -p "require('vitest/package.json').version")"
              '''
              catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE', message: 'eslint found issues') {
                sh '''
                  set -eu
                  if ls eslint.config.* .eslintrc* >/dev/null 2>&1; then npx eslint .; else echo 'no ESLint configuration'; fi
                '''
              }
              catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE', message: 'npm audit found issues') {
                sh '''
                  set -eu
                  npm audit --audit-level=high --omit=dev
                '''
              }
            }
          }
          post {
            always { archiveArtifacts allowEmptyArchive: true, artifacts: 'standalone/electron/test-reports/**' }
            cleanup { cleanWs deleteDirs: true, notFailBuild: true }
          }
        }
        stage('Checks: python backend') {
          agent { docker { image 'python:3.13-slim' } }
          options { timeout(time: 30, unit: 'MINUTES') }
          steps {
            dir('backend') {
              sh '''
                set -eu
                . .venv-ci/bin/activate
                mkdir -p test-reports
                python -m venv .venv-ci
                . .venv-ci/bin/activate && python -m pip install --upgrade pip
                . .venv-ci/bin/activate && if [ -f pyproject.toml ]; then pip install -e '.[test,dev]' || pip install -e .; fi
                . .venv-ci/bin/activate && for f in requirements*.txt; do if [ -f "$f" ]; then pip install -r "$f"; fi; done
                . .venv-ci/bin/activate && pip install pytest==9.1.1 pytest-cov==7.1.0 ruff==0.17.2 'bandit[sarif]==1.9.4' pip-audit==2.10.1
              '''
              catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE', message: 'ruff found issues') {
                sh '''
                  set -eu
                  . .venv-ci/bin/activate
                  ruff check .
                '''
              }
              catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE', message: 'bandit found issues') {
                sh '''
                  set -eu
                  . .venv-ci/bin/activate
                  bandit -r . -x ./tests,./.venv-ci,./node_modules -f sarif -o test-reports/bandit.sarif
                '''
              }
              catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE', message: 'pip-audit found issues') {
                sh '''
                  set -eu
                  . .venv-ci/bin/activate
                  pip-audit
                '''
              }
            }
          }
          post {
            always { archiveArtifacts allowEmptyArchive: true, artifacts: 'backend/test-reports/**' }
            cleanup { cleanWs deleteDirs: true, notFailBuild: true }
          }
        }
        stage('Checks: python standalone') {
          agent { docker { image 'python:3.13-slim' } }
          options { timeout(time: 30, unit: 'MINUTES') }
          steps {
            dir('standalone') {
              sh '''
                set -eu
                . .venv-ci/bin/activate
                mkdir -p test-reports
                python -m venv .venv-ci
                . .venv-ci/bin/activate && python -m pip install --upgrade pip
                . .venv-ci/bin/activate && if [ -f pyproject.toml ]; then pip install -e '.[test,dev]' || pip install -e .; fi
                . .venv-ci/bin/activate && for f in requirements*.txt; do if [ -f "$f" ]; then pip install -r "$f"; fi; done
                . .venv-ci/bin/activate && pip install pytest==9.1.1 pytest-cov==7.1.0 ruff==0.17.2 'bandit[sarif]==1.9.4' pip-audit==2.10.1
              '''
              catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE', message: 'ruff found issues') {
                sh '''
                  set -eu
                  . .venv-ci/bin/activate
                  ruff check .
                '''
              }
              catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE', message: 'bandit found issues') {
                sh '''
                  set -eu
                  . .venv-ci/bin/activate
                  bandit -r . -x ./tests,./.venv-ci,./node_modules -f sarif -o test-reports/bandit.sarif
                '''
              }
              catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE', message: 'pip-audit found issues') {
                sh '''
                  set -eu
                  . .venv-ci/bin/activate
                  pip-audit
                '''
              }
            }
          }
          post {
            always { archiveArtifacts allowEmptyArchive: true, artifacts: 'standalone/test-reports/**' }
            cleanup { cleanWs deleteDirs: true, notFailBuild: true }
          }
        }
      }
    }
  }
}
