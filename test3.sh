# This uses an IP address to test ALLOW_HOSTS functionality only allows certain IP addresses.
curl -G "http://192.168.1.100:8080/api/v1/git_api" \
    --data-urlencode "git_user=DennisPeriquet" \
    --data-urlencode "branch=master" \
    --data-urlencode "jira_number=JIRA-1234" \
    --data-urlencode "image_name=dennis-operator" \
    --data-urlencode "file_content=description: this is a test"
