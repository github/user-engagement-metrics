"""
GitHub User Engagement Metrics Collector

This module fetches and aggregates GitHub user engagement metrics for a list of usernames.
It collects data on repositories, contributions, organizations, and user profiles from the
GitHub API. The script handles rate limiting, retries, and checkpointing to resume
interrupted operations.

Usage:
    1. Add GitHub usernames to 'usernames.txt' (one per line)
    2. Replace 'your_token' with a valid GitHub API token
    3. Run the script to collect metrics
    4. Results are stored in 'user_results.jsonl'
"""

import json
import os
import random
import time
from re import search

import requests

GITHUB_API = "https://api.github.com"
TOKEN = "your_token"  # Replace with your token for higher limits

headers = {"Accept": "application/vnd.github+json", "Authorization": f"token {TOKEN}"}

USERNAMES_FILE = "usernames.txt"  # Each line: a github username
OUTPUT_FILE = "user_results.jsonl"  # One JSON per line
CHECKPOINT_FILE = "completed_usernames.txt"  # To track finished users


def safe_get(url, params=None, extra_headers=None, max_retries=5):
    """
    Make a GET request to the GitHub API with automatic rate limit handling and retries.

    This function handles rate limits by sleeping until the reset time when limits are hit.
    It also implements exponential backoff for server errors.

    Args:
        url (str): The API endpoint URL to request
        params (dict, optional): Query parameters for the request. Defaults to None.
        extra_headers (dict, optional): Additional headers to include in the request.
                                        Defaults to None.
        max_retries (int, optional): Maximum number of retry attempts for failed requests.
                                     Defaults to 5.

    Returns:
        requests.Response: The response object from the successful request
    """
    retries = 0
    while True:
        combined_headers = headers.copy()
        if extra_headers:
            combined_headers.update(extra_headers)
        response = requests.get(
            url, headers=combined_headers, params=params, timeout=10
        )
        if response.status_code == 403:
            remaining = int(response.headers.get("X-RateLimit-Remaining", "1"))
            if remaining == 0:
                reset_time = int(
                    response.headers.get("X-RateLimit-Reset", time.time() + 60)
                )
                sleep_for = max(reset_time - time.time(), 0) + 2
                print(
                    f"Rate limit hit. Sleeping for {sleep_for/60:.2f} minutes (until reset)."
                )
                time.sleep(sleep_for)
                retries = 0
                continue
        if response.status_code in (500, 502, 503, 504) or response.status_code == 403:
            if retries < max_retries:
                wait = (2**retries) + random.uniform(0, 1)
                print(
                    f"Error {response.status_code} on {url}. Retrying in {wait:.2f} seconds..."
                )
                time.sleep(wait)
                retries += 1
                continue
            print(f"Max retries reached for {url}. Skipping.")
            return response
        return response


def get_user_profile(user):
    """
    Fetch a GitHub user's profile information.

    Args:
        user (str): The GitHub username to fetch profile for

    Returns:
        dict: User profile data from the GitHub API
    """
    url = f"{GITHUB_API}/users/{user}"
    return safe_get(url).json()


def get_user_repos(user_name):
    """
    Fetch all public repositories for a GitHub user.

    This function handles pagination to retrieve all repositories even if
    the user has more than 100 repos (the API's default page size).

    Args:
        user_name (str): The GitHub username to fetch repositories for

    Returns:
        list: A list of repository objects from the GitHub API
    """
    repositories = []
    page = 1
    while True:
        url = f"{GITHUB_API}/users/{user_name}/repos"
        params = {"per_page": 100, "page": page}
        res = safe_get(url, params=params).json()
        if not res or "message" in res:
            break
        repositories.extend(res)
        if len(res) < 100:
            break
        page += 1
    return repositories


def get_starred_repos_count(user):
    """
    Get the total count of repositories starred by a GitHub user.

    This function efficiently determines the count by examining the pagination
    links rather than fetching all starred repos.

    Args:
        user (str): The GitHub username to check

    Returns:
        int: The number of repositories starred by the user
    """
    url = f"{GITHUB_API}/users/{user}/starred"
    params = {"per_page": 1}
    res = safe_get(url, params=params)
    link = res.headers.get("Link", "")
    if 'rel="last"' in link:
        match = search(r'page=(\d+)>; rel="last"', link)
        if match:
            return int(match.group(1))
    return len(res.json())


def get_orgs(user):
    """
    Fetch all organizations a GitHub user is a member of.

    Args:
        user (str): The GitHub username to check

    Returns:
        list: A list of organization objects from the GitHub API
    """
    url = f"{GITHUB_API}/users/{user}/orgs"
    return safe_get(url).json()


def search_user_contributions(user, type_):
    """
    Search for a user's public contributions of a specific type.

    Args:
        user (str): The GitHub username to check
        type_ (str): The type of contribution to search for:
                     'pr' (pull requests), 'issue', or 'commit'

    Returns:
        int: The total count of contributions of the specified type
    """
    q_map = {
        "pr": f"type:pr author:{user}",
        "issue": f"type:issue author:{user}",
        "commit": f"author:{user}",
    }
    if type_ == "commit":
        url = f"{GITHUB_API}/search/commits"
        extra_headers = {"Accept": "application/vnd.github.cloak-preview+json"}
        r = safe_get(url, params={"q": q_map[type_]}, extra_headers=extra_headers)
    else:
        url = f"{GITHUB_API}/search/issues"
        r = safe_get(url, params={"q": q_map[type_]})
    return r.json().get("total_count", 0)


def load_completed_usernames():
    """
    Load the set of usernames that have already been processed.

    This function reads the checkpoint file to determine which users
    have been successfully processed in previous runs.

    Returns:
        set: A set of usernames that have already been processed
    """
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as checkpoint_file_load:
            return set(line.strip() for line in checkpoint_file_load if line.strip())
    return set()


def append_completed_username(completed_username):
    """
    Mark a username as completed by adding it to the checkpoint file.

    Args:
        completed_username (str): The GitHub username to mark as completed
    """
    with open(CHECKPOINT_FILE, "a", encoding="utf-8") as checkpoint_file_append:
        checkpoint_file_append.write(completed_username + "\n")


def append_result(user_result):
    """
    Append a user's engagement metrics to the output file.

    Args:
        user_result (dict): The user's engagement metrics to save
    """
    with open(OUTPUT_FILE, "a", encoding="utf-8") as output_file_append:
        output_file_append.write(json.dumps(user_result) + "\n")


if __name__ == "__main__":  # pragma: no cover
    completed = load_completed_usernames()
    with open(USERNAMES_FILE, "r", encoding="utf-8") as file:
        usernames = [line.strip() for line in file if line.strip()]

    print(f"Loaded {len(usernames)} usernames, {len(completed)} already completed.")
    if TOKEN == "your_token":
        print("Warning: You need to generate and use a token.")

    for idx, username in enumerate(usernames):
        if username in completed:
            continue
        print(f"Processing {username} ({idx+1}/{len(usernames)})...")
        try:
            profile = get_user_profile(username)
            if "message" in profile and profile["message"] == "Not Found":
                print(f"User {username} not found.")
                append_completed_username(username)
                continue
            repos = get_user_repos(username)
            starred_count = get_starred_repos_count(username)
            orgs = get_orgs(username)
            pr_count = search_user_contributions(username, "pr")
            issue_count = search_user_contributions(username, "issue")
            commit_count = search_user_contributions(username, "commit")

            result = {
                "username": username,
                "name": profile.get("name"),
                "public_repos": profile.get("public_repos"),
                "followers": profile.get("followers"),
                "following": profile.get("following"),
                "organizations": [org["login"] for org in orgs],
                "starred_repos": starred_count,
                "total_public_prs": pr_count,
                "total_public_issues": issue_count,
                "total_public_commits": commit_count,
            }
            append_result(result)
        except requests.RequestException as e:
            print(f"Network error processing {username}: {e}")
            continue
        except (KeyError, ValueError) as e:
            print(f"Data error processing {username}: {e}")
            continue
        append_completed_username(username)
