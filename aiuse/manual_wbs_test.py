#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append('.')

from tools.wbs_notion_sync import WBSNotionSync

# 수동으로 커밋 정보 생성
def manual_test():
    try:
        sync = WBSNotionSync()

        # 가상의 커밋 정보
        commit_info = {
            'hash': 'abc12345',
            'author': 'Test User',
            'email': 'test@example.com',
            'message': 'AI 수정: WBS Notion 동기화 코드 개선',
            'date': '2025-09-26 13:00:00 +0900'
        }

        changed_files = [
            'tools/wbs_notion_sync.py',
            'test_notion.py',
            '.env'
        ]

        print("수동 WBS 작업 생성 테스트...")
        success = sync.create_commit_task(commit_info, changed_files)

        if success:
            print("성공: WBS 작업이 생성되었습니다!")
        else:
            print("실패: WBS 작업 생성에 실패했습니다.")

        return success

    except Exception as e:
        print(f"오류: {e}")
        return False

if __name__ == "__main__":
    manual_test()