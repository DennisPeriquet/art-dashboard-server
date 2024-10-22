# This is a fully working test in test mode; no PR is created but we still
# run and return a PR link.
curl -G "http://localhost:8080/api/v1/git_api" \
    --data-urlencode "git_user=DennisPeriquet" \
    --data-urlencode "branch=master" \
    --data-urlencode "jira_number=JIRA-1234" \
    --data-urlencode "image_name=dennis-operator" \
    --data-urlencode "file_content=description: this is a test"
