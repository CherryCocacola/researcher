#!/usr/bin/env python3
"""
자동 커밋 및 푸시 스크립트
Claude Code가 파일을 수정할 때 자동으로 Git 커밋/푸시를 수행합니다.
"""

import subprocess
import sys
import os
from datetime import datetime
from typing import Optional


def run_command(cmd: list, cwd: str = None) -> tuple[bool, str]:
    """명령어를 실행하고 결과를 반환합니다."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr.strip() or e.stdout.strip()}"


def check_git_status(repo_path: str) -> tuple[bool, list]:
    """Git 상태를 확인하고 변경된 파일 목록을 반환합니다."""
    success, output = run_command(['git', 'status', '--porcelain'], repo_path)
    if not success:
        return False, []

    changed_files = []
    for line in output.split('\n'):
        if line.strip():
            status = line[:2]
            filepath = line[3:]
            changed_files.append((status, filepath))

    return True, changed_files


def auto_commit_push(repo_path: str, message: Optional[str] = None, files: list = None) -> bool:
    """자동으로 커밋 및 푸시를 수행합니다."""

    if not os.path.exists(os.path.join(repo_path, '.git')):
        print("❌ Git 저장소가 아닙니다.")
        return False

    # Git 상태 확인
    success, changed_files = check_git_status(repo_path)
    if not success:
        print("❌ Git 상태를 확인할 수 없습니다.")
        return False

    if not changed_files:
        print("✅ 변경된 파일이 없습니다.")
        return True

    # 파일 추가
    if files:
        for file in files:
            success, output = run_command(['git', 'add', file], repo_path)
            if not success:
                print(f"❌ 파일 추가 실패 ({file}): {output}")
                return False
    else:
        success, output = run_command(['git', 'add', '.'], repo_path)
        if not success:
            print(f"❌ 파일 추가 실패: {output}")
            return False

    # 커밋 메시지 생성
    if not message:
        file_summary = []
        for status, filepath in changed_files[:5]:  # 최대 5개 파일만 표시
            if status.strip() == 'M':
                file_summary.append(f"수정: {filepath}")
            elif status.strip() == 'A':
                file_summary.append(f"추가: {filepath}")
            elif status.strip() == 'D':
                file_summary.append(f"삭제: {filepath}")
            elif status.strip() == '??':
                file_summary.append(f"신규: {filepath}")

        if len(changed_files) > 5:
            file_summary.append(f"... 외 {len(changed_files) - 5}개 파일")

        message = f"AI 수정: {', '.join(file_summary)}"

    # 커밋 메시지에 Claude Code 서명 추가
    full_message = f"""{message}

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"""

    # 커밋
    success, output = run_command(['git', 'commit', '-m', full_message], repo_path)
    if not success:
        if "nothing to commit" in output:
            print("✅ 커밋할 변경사항이 없습니다.")
            return True
        print(f"❌ 커밋 실패: {output}")
        return False

    print(f"✅ 커밋 완료: {message}")

    # 푸시
    success, output = run_command(['git', 'push'], repo_path)
    if not success:
        print(f"❌ 푸시 실패: {output}")
        print("💡 'git push'를 수동으로 실행해주세요.")
        return False

    print("✅ 푸시 완료")
    return True


def main():
    """메인 함수"""
    repo_path = os.getcwd()
    message = None
    files = []

    # 명령행 인자 파싱
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("""
사용법: python auto_commit.py [옵션] [커밋메시지]

옵션:
  -h, --help    도움말 표시
  -f, --files   특정 파일만 커밋 (공백으로 구분)

예시:
  python auto_commit.py "기능 추가"
  python auto_commit.py -f app.py core/database.py "데이터베이스 수정"
            """)
            return

        if sys.argv[1] in ["-f", "--files"]:
            files = sys.argv[2:-1] if len(sys.argv) > 3 else []
            message = sys.argv[-1] if len(sys.argv) > 2 else None
        else:
            message = sys.argv[1]

    # 자동 커밋/푸시 실행
    success = auto_commit_push(repo_path, message, files)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()