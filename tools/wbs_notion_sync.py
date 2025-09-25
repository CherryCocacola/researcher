import os, re, requests, json
from github import Github
from datetime import datetime, timedelta
from typing import Dict, List, Optional

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

class WBSNotionSync:
    def __init__(self):
        self.db_id = DB_ID
        self.repo = repo
        
    def status_of(self, issue):
        """이슈 상태를 WBS 상태로 매핑"""
        if issue.state == "closed":
            return "완료"
        
        labels = {l.name.lower() for l in issue.labels}
        
        # WBS 상태 매핑
        if "in-progress" in labels or "doing" in labels or issue.assignees:
            return "진행중"
        if "review" in labels or "testing" in labels:
            return "검토중"
        if "blocked" in labels or "waiting" in labels:
            return "대기중"
        if "planning" in labels or "design" in labels:
            return "계획중"
            
        return "대기열"
    
    def parse_eta(self, issue):
        """ETA 파싱"""
        for l in issue.labels:
            m = re.match(r"eta:(\d{4}-\d{2}-\d{2})", l.name.lower())
            if m:
                return m.group(1)
        if issue.milestone and issue.milestone.due_on:
            return issue.milestone.due_on.strftime("%Y-%m-%d")
        return None
    
    def parse_priority(self, issue):
        """우선순위 파싱"""
        for l in issue.labels:
            n = l.name.lower()
            if n in ("p0", "p1", "p2", "p3"):
                return n.upper()
            m = re.match(r"priority:(p0|p1|p2|p3)", n)
            if m:
                return m.group(1).upper()
        return "P2"  # 기본값
    
    def parse_progress(self, issue):
        """진행률 파싱"""
        for l in issue.labels:
            m = re.match(r"progress:(\d{1,3})", l.name.lower())
            if m:
                v = int(m.group(1))
                return max(0, min(100, v))
        return None
    
    def parse_wbs_level(self, issue):
        """WBS 레벨 파싱 (1.0, 1.1, 1.1.1 등)"""
        for l in issue.labels:
            m = re.match(r"wbs:(\d+(?:\.\d+)*)", l.name.lower())
            if m:
                return m.group(1)
        return None
    
    def parse_category(self, issue):
        """카테고리 파싱"""
        categories = {
            "backend": "백엔드",
            "frontend": "프론트엔드", 
            "database": "데이터베이스",
            "ai": "AI/ML",
            "devops": "DevOps",
            "testing": "테스팅",
            "documentation": "문서화",
            "security": "보안",
            "performance": "성능",
            "ui/ux": "UI/UX"
        }
        
        for l in issue.labels:
            cat = l.name.lower()
            if cat in categories:
                return categories[cat]
        return "기타"
    
    def parse_effort(self, issue):
        """작업량 추정 (Story Points)"""
        for l in issue.labels:
            m = re.match(r"effort:(\d+)", l.name.lower())
            if m:
                return int(m.group(1))
        return None
    
    def find_page(self, issue_number):
        """Notion에서 기존 페이지 찾기"""
        url = f"https://api.notion.com/v1/databases/{self.db_id}/query"
        payload = {
            "filter": {"property": "Issue", "number": {"equals": issue_number}},
            "page_size": 1,
        }
        r = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30)
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0]["id"] if results else None
    
    def build_props(self, issue):
        """WBS 속성 구성"""
        assignees = [{"name": a.login} for a in issue.assignees] or []
        
        props = {
            "Name": {"title": [{"text": {"content": f"#{issue.number} {issue.title}"}}]},
            "Issue": {"number": issue.number},
            "Status": {"select": {"name": self.status_of(issue)}},
            "Assignees": {"multi_select": assignees},
            "URL": {"url": issue.html_url},
            "Category": {"select": {"name": self.parse_category(issue)}},
            "Priority": {"select": {"name": self.parse_priority(issue)}},
        }
        
        # 선택적 속성들
        eta = self.parse_eta(issue)
        if eta:
            props["ETA"] = {"date": {"start": eta}}
            
        progress = self.parse_progress(issue)
        if progress is not None:
            props["Progress"] = {"number": progress}
            
        wbs_level = self.parse_wbs_level(issue)
        if wbs_level:
            props["WBS Level"] = {"rich_text": [{"text": {"content": wbs_level}}]}
            
        effort = self.parse_effort(issue)
        if effort:
            props["Effort"] = {"number": effort}
            
        # 마일스톤 정보
        if issue.milestone:
            props["Milestone"] = {"rich_text": [{"text": {"content": issue.milestone.title}}]}
            
        return props
    
    def create_page(self, issue):
        """Notion 페이지 생성"""
        url = "https://api.notion.com/v1/pages"
        payload = {"parent": {"database_id": self.db_id}, "properties": self.build_props(issue)}
        r = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30)
        r.raise_for_status()
        print(f"Created page for issue #{issue.number}")
    
    def update_page(self, page_id, issue):
        """Notion 페이지 업데이트"""
        url = f"https://api.notion.com/v1/pages/{page_id}"
        payload = {"properties": self.build_props(issue)}
        r = requests.patch(url, headers=NOTION_HEADERS, json=payload, timeout=30)
        r.raise_for_status()
        print(f"Updated page for issue #{issue.number}")
    
    def sync_issue(self, issue):
        """이슈 동기화"""
        page_id = self.find_page(issue.number)
        if page_id:
            self.update_page(page_id, issue)
        else:
            self.create_page(issue)
    
    def create_wbs_summary(self):
        """WBS 요약 페이지 생성"""
        url = f"https://api.notion.com/v1/databases/{self.db_id}/query"
        payload = {"page_size": 100}
        r = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30)
        r.raise_for_status()
        
        pages = r.json().get("results", [])
        
        # 상태별 통계
        status_stats = {}
        category_stats = {}
        priority_stats = {}
        
        for page in pages:
            props = page.get("properties", {})
            
            status = props.get("Status", {}).get("select", {}).get("name", "Unknown")
            category = props.get("Category", {}).get("select", {}).get("name", "Unknown")
            priority = props.get("Priority", {}).get("select", {}).get("name", "Unknown")
            
            status_stats[status] = status_stats.get(status, 0) + 1
            category_stats[category] = category_stats.get(category, 0) + 1
            priority_stats[priority] = priority_stats.get(priority, 0) + 1
        
        # 요약 데이터 반환
        return {
            "total_issues": len(pages),
            "status_breakdown": status_stats,
            "category_breakdown": category_stats,
            "priority_breakdown": priority_stats,
            "last_updated": datetime.now().isoformat()
        }
    
    def sync_all_issues(self):
        """모든 이슈 동기화"""
        print("Starting WBS sync...")
        issues = self.repo.get_issues(state="all", sort="updated", direction="desc")
        
        synced_count = 0
        for i, issue in enumerate(issues):
            if issue.pull_request:
                continue
            if i > 200:  # 최대 200개 이슈
                break
                
            self.sync_issue(issue)
            synced_count += 1
        
        print(f"Synced {synced_count} issues")
        
        # 요약 생성
        summary = self.create_wbs_summary()
        print(f"WBS Summary: {summary}")
        
        return summary

def main():
    """메인 실행 함수"""
    sync = WBSNotionSync()
    sync.sync_all_issues()

if __name__ == "__main__":
    main()