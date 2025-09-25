import os, re, requests
from github import Github

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DB_ID = os.environ["NOTION_DATABASE_ID"]
REPO_FULL = os.environ["REPO"]

g = Github(os.environ["GITHUB_TOKEN"])
repo = g.get_repo(REPO_FULL)

NOTION_HEADERS = {
  "Authorization": f"Bearer {NOTION_TOKEN}",
  "Notion-Version": "2022-06-28",
  "Content-Type": "application/json",
}

def status_of(issue):
  if issue.state == "closed":
    return "Done"
  labels = {l.name.lower() for l in issue.labels}
  if "in-progress" in labels or "doing" in labels or issue.assignees:
    return "In Progress"
  if "review" in labels:
    return "Review"
  return "Backlog"

def parse_eta(issue):
  for l in issue.labels:
    m = re.match(r"eta:(\d{4}-\d{2}-\d{2})", l.name.lower())
    if m:
      return m.group(1)
  if issue.milestone and issue.milestone.due_on:
    return issue.milestone.due_on.strftime("%Y-%m-%d")
  return None

def parse_priority(issue):
  for l in issue.labels:
    n = l.name.lower()
    if n in ("p0", "p1", "p2"):
      return n.upper()
    m = re.match(r"priority:(p0|p1|p2)", n)
    if m:
      return m.group(1).upper()
  return None

def parse_progress(issue):
  for l in issue.labels:
    m = re.match(r"progress:(\d{1,3})", l.name.lower())
    if m:
      v = int(m.group(1))
      return max(0, min(100, v))
  return None

def find_page(issue_number):
  url = f"https://api.notion.com/v1/databases/{DB_ID}/query"
  payload = {
    "filter": {"property": "Issue", "number": {"equals": issue_number}},
    "page_size": 1,
  }
  r = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30)
  r.raise_for_status()
  results = r.json().get("results", [])
  return results[0]["id"] if results else None

def build_props(issue):
  assignees = [{"name": a.login} for a in issue.assignees] or []
  props = {
    "Name": {"title": [{"text": {"content": f"#{issue.number} {issue.title}"}}]},
    "Issue": {"number": issue.number},
    "Status": {"select": {"name": status_of(issue)}},
    "Assignees": {"multi_select": assignees},
    "URL": {"url": issue.html_url},
  }
  eta = parse_eta(issue)
  if eta:
    props["ETA"] = {"date": {"start": eta}}
  prio = parse_priority(issue)
  if prio:
    props["Priority"] = {"select": {"name": prio}}
  prog = parse_progress(issue)
  if prog is not None:
    props["Progress"] = {"number": prog}
  return props

def create_page(issue):
  url = "https://api.notion.com/v1/pages"
  payload = {"parent": {"database_id": DB_ID}, "properties": build_props(issue)}
  r = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30)
  r.raise_for_status()

def update_page(page_id, issue):
  url = f"https://api.notion.com/v1/pages/{page_id}"
  payload = {"properties": build_props(issue)}
  r = requests.patch(url, headers=NOTION_HEADERS, json=payload, timeout=30)
  r.raise_for_status()

def sync_issue(issue):
  pid = find_page(issue.number)
  if pid:
    update_page(pid, issue)
  else:
    create_page(issue)

def main():
  issues = repo.get_issues(state="all", sort="updated", direction="desc")
  for i, issue in enumerate(issues):
    if issue.pull_request:
      continue
    if i > 200:
      break
    sync_issue(issue)

if __name__ == "__main__":
  main()
