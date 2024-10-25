# This uses a hostname to test ALLOW_HOSTS functionality only allows certain hosts.
curl -G "http://chopin2:8080/api/v1/git_jira_api" \
    --data-urlencode "git_user=DennisPeriquet" \
    --data-urlencode "branch=master" \
    --data-urlencode "image_name=dennis-operator" \
    --data-urlencode "file_content=description: this is a test"
