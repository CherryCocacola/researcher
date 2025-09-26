#!/usr/bin/env python3
"""
수동 WBS 작업 생성 스크립트
계획 단계의 작업을 미리 Notion WBS에 등록할 때 사용합니다.
"""

import os
import sys
from datetime import datetime, timezone
from wbs_notion_sync import WBSNotionSync

def create_manual_task():
    """대화형으로 수동 작업을 생성합니다."""
    print("📋 새 WBS 작업 생성")
    print("=" * 30)

    # 작업 정보 입력
    task_name = input("작업명: ")
    if not task_name.strip():
        print("❌ 작업명은 필수입니다.")
        return False

    print("\n담당자 선택:")
    print("1. 본인")
    print("2. AI Agent")
    print("3. 공동")
    assignee_choice = input("선택 (1-3): ").strip()
    assignee_map = {"1": "본인", "2": "AI Agent", "3": "공동"}
    assignee = assignee_map.get(assignee_choice, "본인")

    print("\n카테고리 선택:")
    categories = ["기획", "개발", "테스트", "문서화", "배포", "버그수정"]
    for i, cat in enumerate(categories, 1):
        print(f"{i}. {cat}")
    category_choice = input("선택 (1-6): ").strip()
    try:
        category = categories[int(category_choice) - 1]
    except (ValueError, IndexError):
        category = "기획"

    print("\n우선순위 선택:")
    print("1. P0 (긴급)")
    print("2. P1 (높음)")
    print("3. P2 (보통)")
    print("4. P3 (낮음)")
    priority_choice = input("선택 (1-4): ").strip()
    priority_map = {"1": "P0", "2": "P1", "3": "P2", "4": "P3"}
    priority = priority_map.get(priority_choice, "P2")

    # 예상 시간
    try:
        estimated_hours = float(input("예상 소요시간 (시간): ") or "1")
    except ValueError:
        estimated_hours = 1.0

    # 설명
    description = input("작업 설명 (선택사항): ").strip()

    # 상위 작업 (선택사항)
    parent_task = input("상위 작업 ID (선택사항): ").strip()

    print(f"\n📝 작업 생성 중...")
    print(f"   작업명: {task_name}")
    print(f"   담당자: {assignee}")
    print(f"   카테고리: {category}")
    print(f"   우선순위: {priority}")
    print(f"   예상시간: {estimated_hours}시간")

    # 확인
    confirm = input("\n생성하시겠습니까? (y/N): ").lower().strip()
    if confirm != 'y':
        print("❌ 작업 생성이 취소되었습니다.")
        return False

    try:
        sync = WBSNotionSync()
        task_id = f"MANUAL-{datetime.now().strftime('%m%d%H%M')}"

        # 작업 속성 구성
        props = {
            "Task Name": {"title": [{"text": {"content": task_name}}]},
            "Task ID": {"rich_text": [{"text": {"content": task_id}}]},
            "Status": {"select": {"name": "계획"}},
            "Assignee": {"select": {"name": assignee}},
            "Category": {"multi_select": [{"name": category}]},
            "Priority": {"select": {"name": priority}},
            "Progress": {"number": 0},
            "Start Date": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
            "Estimated Hours": {"number": estimated_hours},
            "Description": {"rich_text": [{"text": {"content": description or "수동으로 생성된 계획 작업"}}]}
        }

        # 상위 작업 관계 설정 (Notion에서 Relation 필드가 있는 경우)
        if parent_task:
            props["Parent Task"] = {"rich_text": [{"text": {"content": parent_task}}]}

        # Notion 페이지 생성
        import requests
        from wbs_notion_sync import NOTION_HEADERS

        url = "https://api.notion.com/v1/pages"
        payload = {"parent": {"database_id": sync.db_id}, "properties": props}

        response = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30)
        response.raise_for_status()

        print(f"✅ 작업이 성공적으로 생성되었습니다!")
        print(f"   작업 ID: {task_id}")
        print(f"   Notion에서 확인하세요.")
        return True

    except Exception as e:
        print(f"❌ 작업 생성 실패: {e}")
        return False

def bulk_create_tasks():
    """일괄 작업 생성 (파일에서 읽어오기)"""
    file_path = input("작업 목록 파일 경로 (.txt): ").strip()
    if not os.path.exists(file_path):
        print("❌ 파일을 찾을 수 없습니다.")
        return False

    try:
        sync = WBSNotionSync()
        created_count = 0

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # 형식: "작업명|담당자|카테고리|우선순위|예상시간|설명"
                parts = [p.strip() for p in line.split('|')]
                if len(parts) < 1:
                    continue

                task_name = parts[0]
                assignee = parts[1] if len(parts) > 1 else "본인"
                category = parts[2] if len(parts) > 2 else "기획"
                priority = parts[3] if len(parts) > 3 else "P2"

                try:
                    estimated_hours = float(parts[4]) if len(parts) > 4 else 1.0
                except ValueError:
                    estimated_hours = 1.0

                description = parts[5] if len(parts) > 5 else f"라인 {line_num}에서 생성"

                # 작업 생성
                task_id = f"BULK-{datetime.now().strftime('%m%d')}-{line_num:03d}"

                props = {
                    "Task Name": {"title": [{"text": {"content": task_name}}]},
                    "Task ID": {"rich_text": [{"text": {"content": task_id}}]},
                    "Status": {"select": {"name": "계획"}},
                    "Assignee": {"select": {"name": assignee}},
                    "Category": {"multi_select": [{"name": category}]},
                    "Priority": {"select": {"name": priority}},
                    "Progress": {"number": 0},
                    "Start Date": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
                    "Estimated Hours": {"number": estimated_hours},
                    "Description": {"rich_text": [{"text": {"content": description}}]}
                }

                import requests
                from wbs_notion_sync import NOTION_HEADERS

                url = "https://api.notion.com/v1/pages"
                payload = {"parent": {"database_id": sync.db_id}, "properties": props}

                response = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30)
                response.raise_for_status()

                created_count += 1
                print(f"✅ 작업 {created_count}: {task_name}")

        print(f"\n🎉 총 {created_count}개 작업이 생성되었습니다!")
        return True

    except Exception as e:
        print(f"❌ 일괄 생성 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("🚀 WBS 수동 작업 생성 도구")
    print("=" * 40)

    if len(sys.argv) > 1:
        if sys.argv[1] == "--bulk":
            return bulk_create_tasks()
        elif sys.argv[1] == "--help":
            print("""
사용법:
  python manual_wbs_task.py           # 대화형 단일 작업 생성
  python manual_wbs_task.py --bulk    # 파일에서 일괄 생성
  python manual_wbs_task.py --help    # 도움말

일괄 생성 파일 형식 (.txt):
  작업명1|본인|기획|P1|2|상세 설명
  작업명2|AI Agent|개발|P2|4|또 다른 설명
  # 주석은 건너뜀

필요한 환경변수:
  NOTION_TOKEN
  NOTION_WBS_DATABASE_ID
            """)
            return True

    return create_manual_task()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)