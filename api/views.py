from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets, status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from api.fetchers import rpms_images_fetcher
from api.image_pipeline import pipeline_image_names
from api.util import get_ga_version
from build.models import Build
from . import request_dispatcher
from .serializer import BuildSerializer
import django_filters
from github import Github, GithubException
import json
import re
import os
import jwt
import time
import uuid
from datetime import datetime, timedelta
from build_interface.settings import SECRET_KEY, SESSION_COOKIE_DOMAIN, JWTAuthentication


class BuildDataFilter(django_filters.FilterSet):
    stream_only = django_filters.BooleanFilter(method='filter_stream_only')

    def filter_stream_only(self, queryset, name, value):
        if value:
            return queryset.filter(build_0_nvr__endswith='.assembly.stream')
        return queryset

    class Meta:
        model = Build
        fields = {
            "build_0_id": ["icontains", "exact"],
            "build_0_nvr": ["icontains", "exact"],
            "dg_name": ["icontains", "exact"],
            "brew_task_state": ["exact"],
            "brew_task_id": ["icontains", "exact"],
            "group": ["icontains", "exact"],
            "dg_commit": ["icontains", "exact"],
            "label_io_openshift_build_commit_id": ["icontains", "exact"],
            "time_iso": ["exact"],
            "jenkins_build_url": ["icontains", "exact"],
        }


class BuildViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A read-only view set (https://www.django-rest-framework.org/api-guide/viewsets/#readonlymodelviewset) to get
    build data from ART mariadb database.
    Results are paginated: https://github.com/ashwindasr/art-dashboard-server/tree/master/api#get-apiv1builds
    """
    queryset = Build.objects.all()
    serializer_class = BuildSerializer
    filter_backends = [DjangoFilterBackend,
                       filters.OrderingFilter]  # add feature to filter by URL request eg: /v1/builds/?page=2
    # Explicitly specify which fields the API may be ordered against
    # ordering_fields = ()
    filterset_class = BuildDataFilter

    # This will be used as the default ordering
    ordering = ("-build_time_iso")


@api_view(["GET"])
def pipeline_from_github_api_endpoint(request):
    """
    Endpoint to get the image pipeline starting from GitHub, distgit, brew, cdn or delivery
    :param request: The GET request from the client
    :returns: JSON response containing all data. Eg:
                                {
                                    "status": str,
                                    "payload": {
                                        "openshift_version": str,
                                        "github_repo": str,
                                        "upstream_github_url": str,
                                        "private_github_url": str,
                                        "distgit": [
                                            {
                                                "distgit_repo_name": str,
                                                "distgit_url": "str,
                                                "brew": {
                                                    "brew_id": int,
                                                    "brew_build_url": str,
                                                    "brew_package_name": str,
                                                    "bundle_component": str,
                                                    "bundle_distgit": str,
                                                    "payload_tag": str,
                                                    "cdn": [
                                                        {
                                                            "cdn_repo_id": int,
                                                            "cdn_repo_name": str,
                                                            "cdn_repo_url": str,
                                                            "variant_name": str,
                                                            "variant_id": int,
                                                            "delivery": {
                                                                "delivery_repo_id": str,
                                                                "delivery_repo_name": str,
                                                                "delivery_repo_url": str}}]}}]}}

    """
    starting_from = request.query_params.get("starting_from", None)
    name = request.query_params.get("name", None)
    version = request.query_params.get("version", None)

    # validate input
    if re.match(r"^[A-Za-z]+$", starting_from) and re.match(r"^[A-Za-z0-9/\-]+$", name) and re.match(r"^\d+.\d+$", version):
        try:
            if not version:
                version = get_ga_version()  # Default version set to GA version, if unspecified

            if starting_from.lower().strip() == "github":
                result, status_code = pipeline_image_names.pipeline_from_github(name, version)
            elif starting_from.lower().strip() == "distgit":
                result, status_code = pipeline_image_names.pipeline_from_distgit(name, version)
            elif starting_from.lower().strip() == "package":
                result, status_code = pipeline_image_names.pipeline_from_package(name, version)
            elif starting_from.lower().strip() == "cdn":
                result, status_code = pipeline_image_names.pipeline_from_cdn(name, version)
            elif starting_from.lower().strip() == "image":
                result, status_code = pipeline_image_names.pipeline_from_image(name, version)
            else:
                result, status_code = {
                    "status": "error",
                    "payload": "Invalid value in field 'starting_from'"
                }, 400
        except Exception:
            result, status_code = {
                "status": "error",
                "payload": "Error while retrieving the image pipeline"
            }, 500
    else:
        result, status_code = {
            "status": "error",
            "payload": "Invalid input values"
        }, 400

    json_string = json.loads(json.dumps(result, default=lambda o: o.__dict__))

    return Response(json_string, status=status_code)


@api_view(["GET"])
def ga_version(request):
    try:
        result, status_code = {
            "status": "success",
            "payload": get_ga_version()
        }, 200
    except Exception:
        result, status_code = {
            "status": "error",
            "payload": "Error while retrieving GA version"
        }, 500

    json_string = json.loads(json.dumps(result, default=lambda o: o.__dict__))

    return Response(json_string, status=status_code)


@api_view(["GET"])
def branch_data(request):
    request_type = request.query_params.get("type", None)

    if request_type is None:
        return Response(data={"status": "error", "message": "Missing \"type\" params in the url."})
    elif request_type in ["advisory", "all", "openshift_branch_advisory_ids"]:
        data = request_dispatcher.handle_get_request_for_branch_data_view(request)
        response = Response(data=data)
        return response


@api_view(["GET"])
def test(request):
    return Response({
        "status": "success",
        "payload": "Setup successful!"
    }, status=200)


@api_view(["GET"])
def git_api(request):
    try:
        git_user = request.query_params.get('git_user', None)
        branch = request.query_params.get('branch', None)
        jira_number = request.query_params.get('jira_number', None)
        file_content = request.query_params.get('file_content', None)
        image_name = request.query_params.get('image_name', None)
        test_mode = request.query_params.get('test_mode', None)

        # extract the host from the request.
        host = request.get_host()

        if not all([git_user, branch, jira_number, file_content, image_name]):
            # These are all required. If any are missing, return an error and
            # list what the user passed in.
            return Response({
                "error": "Missing required parameters",
                "parameters": {
                    "git_user": git_user,
                    "branch": branch,
                    "jira_number": jira_number,
                    "file_content": file_content,
                    "image_name": image_name
                }
            }, status=400)

        print(f"Git User: {git_user}")
        print(f"Jira Number: {jira_number}")

        # Do this for now to speed things up for the connectivity test.
        # Test mode is the default (when not specified).
        if not test_mode or 'true' in test_mode.lower():
            return Response({
                "status": "success",
                "payload": f"{host}: Fake PR created successfully",
                "pr_url": "https://github.com/DennisPeriquet/ocp-build-data/pull/10"
            }, status=200)

        # Load the git token from an environment variable, later we can update the deployment
        # to get the token from a Kubernetes environment variable sourced from a secret.
        github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not github_token:
            return Response({"error": "git token not in GITHUB_PERSONAL_ACCESS_TOKEN environment variable"}, status=500)

        git_object = Github(github_token)

        def make_github_request(func, *args, **kwargs):
            """
            This function applies retry logic (with exponential backoff) to git api calls.
            """

            max_retries = 3
            retry_delay = 5
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except GithubException as e:
                    if e.status == 403 and "rate limit" in e.data.get("message", "").lower():
                        print(f"Rate limit exceeded, retrying in {retry_delay} seconds...")
                    elif e.status >= 500 or e.status < 600:
                        print(f"Server error {e.status}, retrying in {retry_delay} seconds...")
                    else:
                        raise
                except Exception as e:
                    print(f"Unexpected error: {str(e)}")
                    raise
                time.sleep(retry_delay)
                retry_delay *= 2
            raise Exception("Max retries exceeded on call to {func.__name__}")

        # Get the repository
        repo = make_github_request(git_object.get_repo, f"{git_user}/ocp-build-data")

        # Get the base branch
        base_branch = make_github_request(repo.get_branch, branch)

        # Generate a unique branch name from the base branch
        unique_id = uuid.uuid4().hex[:10]
        new_branch_name = f"art-dashboard-new-image-{unique_id}"

        # Create a new branch off the base branch
        make_github_request(repo.create_git_ref, ref=f"refs/heads/{new_branch_name}", sha=base_branch.commit.sha)

        # Create the file (images/pf-status-relay.yml) on the new branch
        file_path = f"images/{image_name}.yml"
        make_github_request(
            repo.create_file,
            path=file_path,
            message=f"{image_name} image add",
            content=file_content,
            branch=new_branch_name
        )

        # Create a pull request from the new branch to the base branch
        pr = make_github_request(
            repo.create_pull,
            title=f"[{jira_number}] {image_name} image add",
            body=f"Ticket: {jira_number}\n\nThis PR adds the {image_name} image file",
            head=new_branch_name,
            base=branch
        )

        print(f"Pull request created: {pr.html_url} on branch {new_branch_name}")
        return Response({
            "status": "success",
            "payload": "PR created successfully",
            "pr_url": pr.html_url
        }, status=200)

    except GithubException as e:
        print(f"git api error: {str(e)}")
        return Response({"error": f"git api error: {e.data.get('message', 'Unknown error')}"}, status=e.status)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return Response({"error": f"Unexpected error: {str(e)}"}, status=500)


@api_view(["GET"])
def rpms_images_fetcher_view(request):
    release = request.query_params.get("release", None)

    if release is None:
        return Response(data={"status": "error", "message": "Missing \"release\" params in the url."})

    # Always fetch data
    try:
        result = rpms_images_fetcher.fetch_data(release)
    except Exception as e:
        return Response({
            "status": "error",
            "payload": f"An error occurred while fetching data from GitHub: {e}"
        }, status=500)

    return Response({
        "status": "success",
        "payload": result
    }, status=200)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if username == os.environ.get('ART_DASH_PRIVATE_USER') and password == os.environ.get('ART_DASH_PRIVATE_PASSWORD'):
        # Create a JWT token
        expiration = datetime.utcnow() + timedelta(hours=1)  # Set token to expire in 1 hour
        token = jwt.encode({
            'username': username,
            'exp': expiration
        }, SECRET_KEY, algorithm="HS256")

        # Create a response
        return Response({'detail': 'Login successful', 'token': token}, status=status.HTTP_200_OK)

    return Response({'detail': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def check_auth(request):
    return Response({'detail': 'Authenticated'}, status=status.HTTP_200_OK)
