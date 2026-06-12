from github import Github
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to GitHub
g = Github(os.getenv("GITHUB_TOKEN"))

# Get your repo
user = g.get_user()
repo = user.get_repo(os.getenv("GITHUB_REPO"))

print("=" * 40)
print(f"Repo     : {repo.full_name}")
print(f"URL      : {repo.html_url}")
print(f"Branch   : {repo.default_branch}")
print("=" * 40)
print("✅ GitHub connected successfully!")