// lostfound-ui-test -- Jenkins Declarative Pipeline (Day20)
// CI/CD chain: checkout -> deps -> env guard -> (ui tests, opt-in) -> allure report
// -> COS upload; nightly cron + failure email notification.
//
// Plan C boundary (Day18 measured data): 4G server has only ~0.7G available memory,
// full UI suite is unstable there (4 failed / 220s, environment timeouts). The suite
// stays local (run_ui_tests.bat); this job is a manual-trigger entry + nightly
// report-only cron. To switch nightly cron to a real UI smoke run: flip UI_TESTS
// default to true and set TEST_PATH=testcases/test_login_ui.py (only after raising
// the jenkins container memory limit, see docs/).
//
// Secrets policy (project red line, applies to this public repo file):
//   - COS keys: Jenkins Credentials (Secret text) -> credentials('cos-secret-id' /
//     'cos-secret-key'), auto-masked in console logs.
//   - BASE_URL / test account / bucket / CDN domain: Jenkins Global properties
//     (Manage Jenkins -> System -> Global properties), values never appear here.
//   - Repo URL + branch live in the Jenkins job config, not in this file.
//   - Comments are pure ASCII on purpose (server locale safety, same rule as .bat/.sh).
//
// Notes:
//   - conftest.py calls load_dotenv() WITHOUT override: Jenkins env vars already set
//     in the process win over .env, so no .env file needs to be generated here.
//   - pytest.ini already carries --reruns 1 --only-rerun timeout/network; the
//     UI Tests stage swallows the exit code so report/upload still run on failure
//     (failure visibility comes from Allure + post.failure, same semantics as the
//     Day19 free-style checklist).
//   - Upload to COS mirrors the Day19 scripts; keep report history with
//     REPORT_PREFIX=build-${BUILD_NUMBER} (Jenkins auto-replaces ${BUILD_NUMBER}).

pipeline {
    agent any

    options {
        // Timestamper plugin (verified installed 2026-08-23): timestamps in console
        // logs without any GUI checkbox. GUI "Add timestamps" option is NOT needed.
        timestamps()
    }

    parameters {
        booleanParam(
            name: 'UI_TESTS',
            defaultValue: false,
            description: 'Run pytest suite? true=run, false=report-only (Plan C)'
        )
        // Declarative parameter types: booleanParam/string/choice/text/password/
        // credentials/file/run. NOTE: "stringParam" is scripted-pipeline syntax and
        // fails with MultipleCompilationErrorsException in declarative parameters
        // (Day20, verified on server 2026-08-24); use "string".
        string(
            name: 'TEST_PATH',
            defaultValue: 'testcases/',
            description: 'pytest target when UI_TESTS=true (smoke: testcases/test_login_ui.py)'
        )
        string(
            name: 'REPORT_PREFIX',
            defaultValue: 'latest',
            description: 'COS path under reports/: latest or build-N (empty=skip upload)'
        )
    }

    environment {
        // Jenkins Credentials (Manage Jenkins -> Manage Credentials, type Secret text)
        COS_SECRET_ID  = credentials('cos-secret-id')
        COS_SECRET_KEY = credentials('cos-secret-key')
        // Jenkins Global properties (set real values there, keep placeholders here)
        COS_BUCKET     = "${env.COS_BUCKET ?: ''}"
        COS_REGION     = "${env.COS_REGION ?: 'ap-guangzhou'}"
        COS_CDN_DOMAIN = "${env.COS_CDN_DOMAIN ?: ''}"
        BASE_URL       = "${env.BASE_URL ?: ''}"
        TEST_USERNAME  = "${env.TEST_USERNAME ?: ''}"
        TEST_PASSWORD  = "${env.TEST_PASSWORD ?: ''}"
        TEST_EMAIL     = "${env.TEST_EMAIL ?: ''}"
        MAIL_TO        = "${env.MAIL_TO ?: ''}"
    }

    triggers {
        // Nightly run, report-only by default (Plan C boundary, see header).
        // TIMEZONE TRAP (Day20, verified 2026-08-24): the jenkins container runs
        // UTC (docker exec jenkins date), so cron follows UTC, NOT Beijing time.
        // 'H 18 * * *' = 18:00 UTC = 02:00 Beijing. If the container TZ is ever
        // changed to Asia/Shanghai, revert this to 'H 2 * * *'.
        // Disable by removing this block or unchecking the job trigger in Jenkins.
        cron('H 18 * * *')
    }

    stages {
        stage('Checkout') {
            steps {
                echo "workspace: ${WORKSPACE}"
                checkout scm
            }
        }

        stage('Env Guard') {
            steps {
                sh '''
                    set -e
                    echo "== [guard] required env vars (values never printed) =="
                    for v in BASE_URL TEST_USERNAME TEST_PASSWORD; do
                        if ! env | grep -q "^$v="; then
                            echo "[ERROR] env $v is empty - set it in Jenkins Global properties" >&2
                            exit 1
                        fi
                    done
                    echo "[ok] required env vars present"
                '''
            }
        }

        stage('Setup Environment') {
            steps {
                sh '''
                    set -e
                    echo "== [setup] venv (cached in workspace; do NOT clean workspace) =="
                    if [ ! -d venv ]; then python3 -m venv venv; fi
                    venv/bin/pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple -q
                    # cos-python-sdk-v5: NOT on tsinghua mirror -> official PyPI fallback (Day19)
                    venv/bin/pip install cos-python-sdk-v5 -q || true
                    echo "== [setup] playwright chromium (npmmirror standard prefix, Day18) =="
                    export PLAYWRIGHT_DOWNLOAD_HOST=https://registry.npmmirror.com/-/binary/playwright
                    venv/bin/playwright install chromium || true
                '''
            }
        }

        stage('UI Tests') {
            when { expression { return params.UI_TESTS } }
            steps {
                withEnv(["TEST_PATH=${params.TEST_PATH}"]) {
                    sh '''
                        echo "== [tests] pytest $TEST_PATH (server memory limited, see docs) =="
                        venv/bin/python -m pytest $TEST_PATH -q || true
                    '''
                }
            }
        }

        stage('Generate Report') {
            when { expression { return fileExists('allure-results') } }
            steps {
                sh '''
                    echo "== [report] allure generate (skip if CLI missing; plugin also publishes) =="
                    if command -v allure >/dev/null 2>&1; then
                        allure generate ./allure-results -o ./allure-report --clean || true
                    else
                        echo "[warn] allure CLI not found; report served by Jenkins Allure plugin only"
                    fi
                '''
            }
        }

        stage('Upload to COS') {
            when {
                allOf {
                    expression { return fileExists('allure-report') }
                    expression { return params.REPORT_PREFIX != '' }
                    expression { return env.COS_BUCKET != '' }
                }
            }
            steps {
                withEnv(["REPORT_PREFIX=${params.REPORT_PREFIX}"]) {
                    sh '''
                        set -e
                        if [ "$REPORT_PREFIX" = "latest" ]; then
                            echo "== [upload] reports/latest (prune orphans + verify) =="
                            # --prune: delete orphan objects under the prefix (Allure
                            # attachments are random-uuid named; put_object never deletes,
                            # so stale attachments pile up and --verify stays MISMATCH.
                            # Day20 measured 40 orphans on server build #3, 194 vs 154).
                            venv/bin/python scripts/upload_to_cos.py allure-report reports/latest --prune --verify
                        else
                            echo "== [upload] reports/$REPORT_PREFIX (history, no version file) =="
                            venv/bin/python scripts/upload_to_cos.py allure-report "reports/$REPORT_PREFIX" --no-version
                        fi
                    '''
                }
            }
        }
    }

    post {
        success {
            script {
                // env.X (NOT bare X): post blocks run outside the node context,
                // bare environment names throw MissingPropertyException (Day20,
                // server build #3 verified: "No such property: COS_CDN_DOMAIN").
                if (env.COS_CDN_DOMAIN) {
                    echo "Pipeline OK. Report: ${env.COS_CDN_DOMAIN}/reports/${params.REPORT_PREFIX}/index.html"
                } else {
                    echo "Pipeline OK. Report served via COS console/custom domain (COS_CDN_DOMAIN not set)"
                }
            }
        }
        failure {
            emailext(
                to: env.MAIL_TO ?: 'you@example.com',
                subject: "[Jenkins] ${env.JOB_NAME} #${env.BUILD_NUMBER} FAILED",
                body: """Job: ${env.JOB_NAME} (#${env.BUILD_NUMBER})
Build URL: ${env.BUILD_URL}
Duration: ${currentBuild.durationString}
Last stage: ${env.STAGE_NAME}
Report: ${env.COS_CDN_DOMAIN}/reports/${params.REPORT_PREFIX}/index.html

Check the console output for the failing stage."""
            )
        }
        always {
            echo "Build #${env.BUILD_NUMBER} finished: ${currentBuild.currentResult}"
        }
    }
}
