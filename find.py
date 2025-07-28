import requests
import base64
import re

# CONFIGURATION
GITHUB_TOKEN = "ghp_your_token_here"
ORG = "your-org-name"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

BITNAMI_PATTERNS = [
    r'bitnami/',
    r'https://charts\.bitnami\.com/bitnami',
    r'oci://registry-1\.docker\.io/bitnamicharts'
]

def get_repos():
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/{ORG}/repos?per_page=100&page={page}"
        res = requests.get(url, headers=HEADERS)
        if res.status_code != 200:
            raise Exception(f"Error: {res.text}")
        data = res.json()
        if not data:
            break
        repos.extend([r['name'] for r in data])
        page += 1
    return repos

def get_yaml_files(repo):
    url = f"https://api.github.com/repos/{ORG}/{repo}/git/trees/HEAD?recursive=1"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return []
    return [item["path"] for item in res.json()["tree"]
            if item["path"].endswith((".yaml", ".yml")) and item["type"] == "blob"]

def get_file_content(repo, path):
    url = f"https://api.github.com/repos/{ORG}/{repo}/contents/{path}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return ""
    return base64.b64decode(res.json()["content"]).decode("utf-8", errors="ignore")

def contains_bitnami(content):
    return any(re.search(p, content) for p in BITNAMI_PATTERNS)

def main():
    results = {}
    print(f"🔍 Scanning GitHub org: {ORG}")
    repos = get_repos()
    for repo in repos:
        print(f"📁 Checking repo: {repo}")
        for file_path in get_yaml_files(repo):
            content = get_file_content(repo, file_path)
            if contains_bitnami(content):
                results.setdefault(repo, []).append(file_path)
    print("\n=== Bitnami Usage Report ===")
    for repo, files in results.items():
        print(f"\n📦 {repo}")
        for f in files:
            print(f"  - {f}")

if __name__ == "__main__":
    main()
