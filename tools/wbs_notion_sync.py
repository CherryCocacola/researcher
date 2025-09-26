import os, re, requests, json, subprocess
from github import Github
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경변수 설정 - WBS 전용 데이터베이스 ID 사용
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
WBS_DB_ID = os.environ.get("NOTION_WBS_DATABASE_ID") or os.environ.get("NOTION_DATABASE_ID")
REPO_FULL = os.environ.get("REPO", "CherryCocacola/researcher")

# GitHub 설정 (선택사항)
github_token = os.environ.get("GITHUB_TOKEN")
g = Github(github_token) if github_token else None
repo = g.get_repo(REPO_FULL) if g else None

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

class WBSNotionSync:
    def __init__(self):
        if not NOTION_TOKEN or not WBS_DB_ID:
            raise ValueError("NOTION_TOKEN과 NOTION_WBS_DATABASE_ID 환경변수가 필요합니다.")

        self.db_id = WBS_DB_ID
        self.repo = repo
        print(f"WBS Notion 동기화 초기화 완료 (DB: {WBS_DB_ID[:8]}...)")

    def get_latest_commit_info(self) -> Optional[Dict]:
        """최신 커밋 정보를 가져옵니다."""
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%H|%an|%ae|%s|%ai'],
                capture_output=True,
                text=True,
                check=True
            )
            commit_info = result.stdout.strip().split('|')
            if len(commit_info) >= 5:
                return {
                    'hash': commit_info[0][:8],
                    'author': commit_info[1],
                    'email': commit_info[2],
                    'message': commit_info[3],
                    'date': commit_info[4]
                }
        except subprocess.CalledProcessError:
            print("Git 커밋 정보를 가져올 수 없습니다.")
        return None

    def get_changed_files(self) -> List[str]:
        """최신 커밋에서 변경된 파일 목록을 가져옵니다."""
        try:
            result = subprocess.run(
                ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD'],
                capture_output=True,
                text=True,
                check=True
            )
            return [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
        except subprocess.CalledProcessError:
            return []
        
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
    
    def find_page(self, task_name):
        """Notion에서 기존 페이지 찾기"""
        url = f"https://api.notion.com/v1/databases/{self.db_id}/query"
        payload = {
            "filter": {"property": "Title", "title": {"contains": task_name[:50]}},
            "page_size": 1,
        }
        r = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30)
        r.raise_for_status()
        results = r.json().get("results", [])
        return results[0]["id"] if results else None
    
    def build_props(self, issue):
        """간단한 3-속성 구성 (이름, 태그, 파일)"""
        # 태그 생성
        tags = []

        # 상태 태그
        tags.append({"name": self.status_of(issue)})

        # 담당자 태그
        if issue.assignees:
            tags.append({"name": "본인"})
        else:
            tags.append({"name": "AI-Agent"})

        # 카테고리 태그
        category = self.parse_category(issue)
        if category == "백엔드":
            tags.append({"name": "개발"})
        elif category == "문서화":
            tags.append({"name": "문서화"})
        else:
            tags.append({"name": "개발"})

        # 우선순위 태그
        priority = self.parse_priority(issue)
        tags.append({"name": f"{priority}-보통" if priority == "P2" else f"{priority}-높음"})

        props = {
            "Title": {"title": [{"text": {"content": f"#{issue.number} {issue.title}"}}]},
            "Tags": {"multi_select": tags},
            "ExcuteDate": {"date": {"start": datetime.now(timezone.utc).isoformat()}}
            # plandate는 사용자가 수동으로 입력
        }

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
    
    def create_commit_task(self, commit_info: Dict, changed_files: List[str]) -> bool:
        """커밋 정보로부터 간단한 WBS 작업을 생성합니다."""
        try:
            task_name = commit_info['message']
            if len(task_name) > 100:
                task_name = task_name[:97] + "..."

            # 태그 생성
            tags = []

            # 상태 태그 (커밋은 이미 완료된 작업)
            tags.append({"name": "완료"})

            # 담당자 태그 - AI 여부 판단
            if any(keyword in commit_info['message'].lower()
                   for keyword in ['ai', 'claude', 'auto', '🤖']):
                tags.append({"name": "AI-Agent"})
            else:
                tags.append({"name": "본인"})

            # 카테고리 태그 판단
            if any(keyword in commit_info['message'].lower()
                   for keyword in ['feat', 'feature', 'add']):
                tags.append({"name": "개발"})
            elif any(keyword in commit_info['message'].lower()
                     for keyword in ['fix', 'bug', 'error']):
                tags.append({"name": "버그수정"})
            elif any(keyword in commit_info['message'].lower()
                     for keyword in ['doc', 'readme']):
                tags.append({"name": "문서화"})
            elif any(keyword in commit_info['message'].lower()
                     for keyword in ['test']):
                tags.append({"name": "테스트"})
            else:
                tags.append({"name": "개발"})

            # 우선순위 태그
            tags.append({"name": "P2-보통"})

            # Notion 페이지 속성 (Title, Tags, Files, plandate, ExcuteDate)
            props = {
                "Title": {"title": [{"text": {"content": task_name}}]},
                "Tags": {"multi_select": tags},
                "ExcuteDate": {"date": {"start": datetime.now(timezone.utc).isoformat()}}
                # Files 속성은 API로 파일 업로드가 복잡하므로 생략
                # plandate는 사용자가 수동으로 입력
            }

            # 페이지 생성
            url = "https://api.notion.com/v1/pages"
            payload = {"parent": {"database_id": self.db_id}, "properties": props}

            r = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30)
            r.raise_for_status()

            print(f"WBS 작업 생성: {task_name}")
            return True

        except Exception as e:
            print(f"WBS 작업 생성 실패: {e}")
            return False

    def find_commit_task(self, commit_hash: str) -> Optional[str]:
        """커밋 해시로 기존 작업 찾기 (이름에 해시가 포함된 작업 찾기)"""
        try:
            url = f"https://api.notion.com/v1/databases/{self.db_id}/query"
            payload = {
                "filter": {
                    "property": "Title",
                    "title": {"contains": commit_hash[:8]}
                },
                "page_size": 1
            }
            r = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30)
            r.raise_for_status()

            results = r.json().get("results", [])
            return results[0]["id"] if results else None

        except Exception as e:
            print(f"기존 작업 검색 실패: {e}")
            return None

    def sync_latest_commit(self) -> bool:
        """최신 커밋을 WBS에 동기화"""
        print("최신 커밋 WBS 동기화 시작...")

        # 커밋 정보 가져오기
        commit_info = self.get_latest_commit_info()
        if not commit_info:
            return False

        print(f"처리할 커밋: {commit_info['hash']} - {commit_info['message'][:50]}...")

        # 기존 작업 확인
        existing_task = self.find_commit_task(commit_info['hash'])
        if existing_task:
            print("이미 동기화된 커밋입니다.")
            return True

        # 변경된 파일 목록
        changed_files = self.get_changed_files()
        print(f"변경된 파일 수: {len(changed_files)}")

        # WBS 작업 생성
        return self.create_commit_task(commit_info, changed_files)

    def sync_all_issues(self):
        """모든 이슈 동기화 (기존 기능 유지)"""
        if not self.repo:
            print("GitHub API 토큰이 없어 이슈 동기화를 건너뜁니다.")
            return self.sync_latest_commit()

        print("GitHub 이슈 WBS 동기화 시작...")
        issues = self.repo.get_issues(state="all", sort="updated", direction="desc")

        synced_count = 0
        for i, issue in enumerate(issues):
            if issue.pull_request:
                continue
            if i > 200:  # 최대 200개 이슈
                break

            self.sync_issue(issue)
            synced_count += 1

        print(f"{synced_count}개 이슈 동기화 완료")

        # 최신 커밋도 동기화
        print("최신 커밋 동기화...")
        self.sync_latest_commit()

        # 요약 생성
        summary = self.create_wbs_summary()
        print(f"WBS 요약: {json.dumps(summary, indent=2, ensure_ascii=False)}")

        return summary

def main():
    """메인 실행 함수"""
    try:
        sync = WBSNotionSync()

        # 커맨드라인 인자 처리
        import sys
        if len(sys.argv) > 1:
            if sys.argv[1] == "--commit-only":
                # 최신 커밋만 동기화
                return sync.sync_latest_commit()
            elif sys.argv[1] == "--issues-only":
                # GitHub 이슈만 동기화
                if sync.repo:
                    sync.sync_all_issues()
                else:
                    print("❌ GitHub API 토큰이 필요합니다.")
                    return False
            elif sys.argv[1] == "--help":
                print("""
WBS Notion 동기화 스크립트

사용법:
  python wbs_notion_sync.py                # 전체 동기화 (이슈 + 커밋)
  python wbs_notion_sync.py --commit-only  # 최신 커밋만 동기화
  python wbs_notion_sync.py --issues-only  # GitHub 이슈만 동기화
  python wbs_notion_sync.py --help         # 도움말

필요한 환경변수:
  NOTION_TOKEN              # Notion 통합 토큰
  NOTION_WBS_DATABASE_ID    # WBS 데이터베이스 ID
  GITHUB_TOKEN (선택)       # GitHub API 토큰
  REPO (선택)               # 저장소 이름 (기본: CherryCocacola/researcher)
                """)
                return True

        # 기본 동작: 전체 동기화
        return sync.sync_all_issues()

    except ValueError as e:
        print(f"설정 오류: {e}")
        print(".env 파일에 NOTION_TOKEN과 NOTION_WBS_DATABASE_ID를 설정해주세요.")
        return False
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)