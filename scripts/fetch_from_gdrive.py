"""
Google Drive から小説の各話を取得し、Astro用Markdownファイルに変換するスクリプト

使い方:
  python scripts/fetch_from_gdrive.py

設定:
  PART_FOLDERS に各部のGoogle DriveフォルダIDを入力してください。
"""

import os
import re
from datetime import date
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# =====================================================================
# 設定 (ここを編集してください)
# =====================================================================

# 各部のGoogle DriveフォルダID
# フォルダURLの末尾の文字列: https://drive.google.com/drive/folders/XXXXXXXXXX
PART_FOLDERS = {
    1: "ここに第一部のフォルダIDを入力",
    2: "ここに第二部のフォルダIDを入力",
    3: "ここに第三部のフォルダIDを入力",
}

# 出力先ディレクトリ (プロジェクトルートからの相対パス)
OUTPUT_DIR = Path(__file__).parent.parent / "src" / "content" / "chapters"

# ファイル内のエピソードの並び順 ("name" or "createdTime")
SORT_BY = "name"

# =====================================================================

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]

CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"


def get_credentials():
    """OAuth2認証を行い、credentialsを返す"""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print(f"エラー: {CREDENTIALS_FILE} が見つかりません。")
                print("Google Cloud Console から OAuth 2.0 クライアントIDをダウンロードし、")
                print(f"scripts/credentials.json として保存してください。")
                exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def list_docs_in_folder(drive_service, folder_id: str, sort_by: str = "name") -> list:
    """フォルダ内のGoogle Docsファイル一覧を取得する"""
    results = (
        drive_service.files()
        .list(
            q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false",
            fields="files(id, name, createdTime, modifiedTime)",
            orderBy=sort_by,
        )
        .execute()
    )
    return results.get("files", [])


def extract_text_from_doc(docs_service, doc_id: str) -> list[str]:
    """Google DocsのドキュメントIDからテキスト段落リストを取得する"""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    paragraphs = []

    for element in doc.get("body", {}).get("content", []):
        if "paragraph" in element:
            para = element["paragraph"]
            text = ""
            for pe in para.get("elements", []):
                if "textRun" in pe:
                    text += pe["textRun"].get("content", "")
            # 末尾の改行を除去
            text = text.rstrip("\n")
            if text:
                paragraphs.append(text)

    return paragraphs


def paragraphs_to_markdown(paragraphs: list[str]) -> str:
    """段落リストをMarkdown本文に変換する"""
    lines = []
    for para in paragraphs:
        # 段落の先頭に全角スペースがなければ追加
        if not para.startswith("\u3000"):
            para = "\u3000" + para
        lines.append(para)
    return "\n\n".join(lines)


def build_frontmatter(title: str, part: int, episode: int, description: str = "") -> str:
    """Astro用フロントマターを生成する"""
    today = date.today().isoformat()
    lines = [
        "---",
        f"title: {title}",
        f"part: {part}",
        f"episode: {episode}",
        f"publishedAt: {today}",
    ]
    if description:
        lines.append(f"description: {description}")
    lines.append("---")
    return "\n".join(lines)


def build_filename(part: int, episode: int) -> str:
    """ファイル名を生成する (例: part1-01.md)"""
    return f"part{part}-{episode:02d}.md"


def fetch_all(dry_run: bool = False):
    """全部・全話を取得してMarkdownファイルに保存する"""
    print("Google Drive API に接続中...")
    creds = get_credentials()
    drive_service = build("drive", "v3", credentials=creds)
    docs_service = build("docs", "v1", credentials=creds)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for part_num, folder_id in PART_FOLDERS.items():
        if folder_id.startswith("ここに"):
            print(f"\n[第{part_num}部] スキップ (フォルダIDが未設定)")
            continue

        print(f"\n[第{part_num}部] フォルダ {folder_id} を取得中...")
        docs = list_docs_in_folder(drive_service, folder_id, SORT_BY)

        if not docs:
            print(f"  ドキュメントが見つかりませんでした")
            continue

        print(f"  {len(docs)} 件のドキュメントを発見")

        for episode_num, doc_info in enumerate(docs, start=1):
            title = doc_info["name"]
            doc_id = doc_info["id"]
            filename = build_filename(part_num, episode_num)
            output_path = OUTPUT_DIR / filename

            print(f"  [{episode_num:02d}] {title} → {filename}")

            if dry_run:
                continue

            # ドキュメント本文を取得
            paragraphs = extract_text_from_doc(docs_service, doc_id)
            body = paragraphs_to_markdown(paragraphs)

            # フロントマターを生成
            frontmatter = build_frontmatter(title, part_num, episode_num)

            # ファイルに書き込み
            content = frontmatter + "\n\n" + body + "\n"
            output_path.write_text(content, encoding="utf-8")

        print(f"  第{part_num}部 完了")

    print("\n完了！")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Google DriveからAstro用Markdownを生成")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ファイルを作成せずにドキュメント一覧だけ表示する",
    )
    args = parser.parse_args()

    fetch_all(dry_run=args.dry_run)
