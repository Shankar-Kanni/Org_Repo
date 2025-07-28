import requests
import base64
import yaml
import re
import time

# === CONFIG ===
GITHUB_TOKEN = "ghp_your_token_here"  # 🔁 Replace with your token
ORG = "your-org-name"                 # 🔁 Replace with your GitHub organization

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

BITNAMI_PATTERNS = {
    "bitnami": r'\bbitnami/([\w\-.]+)\b',
    "docker": r'\bdocker\.io/bitnami/([\w\-.]+)\b',
    "charts": r'https://charts\.bitnami\.com/bitnami',
    "oci": r'oci://registry-1\.docker\.io/bitnamicharts(?:/([\w\-.]+))?'
}

def get_all_repos():
    repos = []
    page = 1
    print("📦 Fetching all repositories...")
    while True:
        url = f"https://api.github.com/orgs/{ORG}/repos?per_page=100&page={page}"
        res = requests.get(url, headers=HEADERS)
        if res.status_code != 200:
            print(f"❌ Failed to fetch repos: {res.text}")
            break
        data = res.json()
        if not data:
            break
        repos.extend([r['name'] for r in data])
        page += 1
        time.sleep(0.1)  # avoid rate limit
    return repos

def get_yaml_files(repo):
    url = f"https://api.github.com/repos/{ORG}/{repo}/git/trees/HEAD?recursive=1"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return []
    return [item["path"] for item in res.json()["tree"]
            if item["type"] == "blob" and item["path"].endswith((".yaml", ".yml"))]

def fetch_file_content(repo, path):
    url = f"https://api.github.com/repos/{ORG}/{repo}/contents/{path}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return None
    try:
        content = res.json()["content"]
        return base64.b64decode(content).decode("utf-8", errors="ignore")
    except Exception:
        return None

def search_bitnami_in_yaml(data):
    matches = []

    def recursive_search(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                recursive_search(k)
                recursive_search(v)
        elif isinstance(obj, list):
            for item in obj:
                recursive_search(item)
        elif isinstance(obj, str):
            for key, pattern in BITNAMI_PATTERNS.items():
                m = re.search(pattern, obj)
                if m:
                    full = m.group(0)
                    extracted = m.group(1) if len(m.groups()) >= 1 else ""
                    matches.append((key, full, extracted))

    recursive_search(data)
    return matches

def main():
    print(f"🔍 Scanning GitHub org: {ORG}")
    repos = get_all_repos()
    results = {}

    for repo in repos:
        print(f"📁 Checking repo: {repo}")
        try:
            yaml_files = get_yaml_files(repo)
        except Exception as e:
            print(f"  ⚠️ Failed to fetch files for {repo}: {e}")
            continue

        for path in yaml_files:
            content = fetch_file_content(repo, path)
            if not content:
                continue
            try:
                parsed_yaml = yaml.safe_load(content)
            except yaml.YAMLError:
                continue
            if not parsed_yaml:
                continue
            matches = search_bitnami_in_yaml(parsed_yaml)
            if matches:
                results.setdefault(repo, []).append((path, matches))

    print("\n=== 🧾 Bitnami Usage Report ===")
    if not results:
        print("✅ No Bitnami usage found in any repo.")
    else:
        for repo, entries in results.items():
            print(f"\n📦 {repo}")
            for path, matches in entries:
                print(f"  📄 {path}")
                for kind, full, extracted in matches:
                    if extracted:
                        print(f"    ➤ {full} → {extracted}")
                    else:
                        print(f"    ➤ {full}")

if __name__ == "__main__":
    main()
