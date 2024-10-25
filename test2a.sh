# This uses a hostname to test ALLOW_HOSTS functionality only allows certain hosts.
curl -G "http://chopin2:8080/api/v1/git_jira_api" \
    --data-urlencode "git_user=DennisPeriquet" \
    --data-urlencode "branch=master" \
    --data-urlencode "image_name=dennis-operator" \
    --data-urlencode "file_content=description: this is a test" \
    --data-urlencode "git_test_mode=false" \
    --data-urlencode "jira_test_mode=false" \
    --data-urlencode "jira_summary=Test Summary" \
    --data-urlencode "jira_description=Test Description" \
    --data-urlencode "jira_project_id=ART" \
    --data-urlencode "jira_story_type_id=Story" \
    --data-urlencode "jira_component=Release work" \
    --data-urlencode "jira_priority=Normal"

