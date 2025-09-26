#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, requests
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
WBS_DB_ID = os.environ.get("NOTION_WBS_DATABASE_ID")

print(f"NOTION_TOKEN: {NOTION_TOKEN[:20] if NOTION_TOKEN else None}...")
print(f"WBS_DB_ID: {WBS_DB_ID}")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# 테스트 작업 생성
def test_create_task():
    try:
        # 테스트 태그
        tags = [
            {"name": "완료"},
            {"name": "AI-Agent"},
            {"name": "개발"},
            {"name": "P2-보통"}
        ]

        # Notion 페이지 속성
        from datetime import datetime, timezone

        props = {
            "Title": {"title": [{"text": {"content": "테스트 작업: Notion WBS 연동 확인 (날짜 포함)"}}]},
            "Tags": {"multi_select": tags},
            "ExcuteDate": {"date": {"start": datetime.now(timezone.utc).isoformat()}}
        }

        # 페이지 생성
        url = "https://api.notion.com/v1/pages"
        payload = {"parent": {"database_id": WBS_DB_ID}, "properties": props}

        r = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30)

        print(f"Response Status: {r.status_code}")
        print(f"Response Body: {r.text}")

        if r.status_code == 200:
            print("성공: 테스트 작업이 Notion WBS에 생성되었습니다!")
            return True
        else:
            print(f"실패: HTTP {r.status_code}")
            return False

    except Exception as e:
        print(f"오류: {e}")
        return False

if __name__ == "__main__":
    if not NOTION_TOKEN or not WBS_DB_ID:
        print("환경변수가 설정되지 않았습니다.")
    else:
        test_create_task()