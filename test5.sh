# We are missing the git_user ; this should fail
curl -G "http://localhost:8080/api/v1/git_api" \
    --data-urlencode "branch=master" \
    --data-urlencode "jira_number=JIRA-1234" \
    --data-urlencode "image_name=dennis-operator" \
    --data-urlencode "file_content=description: this is a test"
