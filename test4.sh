# This is a fully working test in test mode; a PR is created and we return
# a PR link (since test_mode is explicitly set to false).
curl -G "http://localhost:8080/api/v1/git_api" \
    --data-urlencode "git_user=DennisPeriquet" \
    --data-urlencode "branch=master" \
    --data-urlencode "jira_number=JIRA-1234" \
    --data-urlencode "image_name=dennis-operator" \
    --data-urlencode "file_content=description: this is a test" \
    --data-urlencode "test_mode=false"

