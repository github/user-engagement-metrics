import requests
import time
import random
import json
import os

GITHUB_API = "https://api.github.com"
TOKEN = "your_token"  # Replace with your token for higher limits

headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"token {TOKEN}"
}

USERNAMES_FILE = "usernames.txt"     # Each line: a github username
OUTPUT_FILE = "user_results.jsonl"   # One JSON per line
CHECKPOINT_FILE = "completed_usernames.txt"  # To track finished users

def safe_get(url, params=None, extra_headers=None, max_retries=5):
    retries = 0
    while True:
        combined_headers = headers.copy()
        if extra_headers:
            combined_headers.update(extra_headers)
        response = requests.get(url, headers=combined_headers, params=params)
        if response.status_code == 403:
            remaining = int(response.headers.get('X-RateLimit-Remaining', '1'))
            if remaining == 0:
                reset_time = int(response.headers.get('X-RateLimit-Reset', time.time() + 60))
                sleep_for = max(reset_time - time.time(), 0) + 2
                print(f"Rate limit hit. Sleeping for {sleep_for/60:.2f} minutes (until reset).")
                time.sleep(sleep_for)
                retries = 0
                continue
        if response.status_code in (500, 502, 503, 504) or response.status_code == 403:
            if retries < max_retries:
                wait = (2 ** retries) + random.uniform(0, 1)
                print(f"Error {response.status_code} on {url}. Retrying in {wait:.2f} seconds...")
                time.sleep(wait)
                retries += 1
                continue
            else:
                print(f"Max retries reached for {url}. Skipping.")
                return response
        return response

def get_user_profile(username):
    url = f"{GITHUB_API}/users/{username}"
    return safe_get(url).json()

def get_user_repos(username):
    repos = []
    page = 1
    while True:
        url = f"{GITHUB_API}/users/{username}/repos"
        params = {"per_page": 100, "page": page}
        res = safe_get(url, params=params).json()
        if not res or "message" in res:
            break
        repos.extend(res)
        if len(res) < 100:
            break
        page += 1
    return repos

def get_starred_repos_count(username):
    url = f"{GITHUB_API}/users/{username}/starred"
    params = {"per_page": 1}
    res = safe_get(url, params=params)
    link = res.headers.get("Link", "")
    if 'rel="last"' in link:
        import re
        match = re.search(r'page=(\d+)>; rel="last"', link)
        if match:
            return int(match.group(1))
    return len(res.json())

def get_orgs(username):
    url = f"{GITHUB_API}/users/{username}/orgs"
    return safe_get(url).json()

def search_user_contributions(username, type_):
    q_map = {
        "pr": f"type:pr author:{username}",
        "issue": f"type:issue author:{username}",
        "commit": f"author:{username}"
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
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def append_completed_username(username):
    with open(CHECKPOINT_FILE, "a") as f:
        f.write(username + "\n")

def append_result(result):
    with open(OUTPUT_FILE, "a") as f:
        f.write(json.dumps(result) + "\n")

if __name__ == "__main__":
    completed = load_completed_usernames()
    with open(USERNAMES_FILE, "r") as f:
        usernames = [line.strip() for line in f if line.strip()]

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
                "organizations": [org['login'] for org in orgs],
                "starred_repos": starred_count,
                "total_public_prs": pr_count,
                "total_public_issues": issue_count,
                "total_public_commits": commit_count
            }
            append_result(result)
        except Exception as e:
            print(f"Error processing {username}: {e}")
            continue
        append_completed_username(username)