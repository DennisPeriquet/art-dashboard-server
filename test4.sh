# This is a fully working test in test mode; a PR is created and we return
# a PR link (since git_test_mode is explicitly set to false).
curl -G "http://localhost:8080/api/v1/git_jira_api" \
    --data-urlencode "git_user=DennisPeriquet" \
    --data-urlencode "branch=master" \
    --data-urlencode "image_name=dennis-operator" \
    --data-urlencode "file_content=description: this is a test" \
    --data-urlencode "git_test_mode=false"

