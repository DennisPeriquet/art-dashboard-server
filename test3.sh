# This uses an IP address to test ALLOW_HOSTS functionality only allows certain IP addresses.
curl -G "http://192.168.1.100:8080/api/v1/git_jira_api" \
    --data-urlencode "git_user=DennisPeriquet" \
    --data-urlencode "branch=master" \
    --data-urlencode "image_name=dennis-operator" \
    --data-urlencode "file_content=description: this is a test"
