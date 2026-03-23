#!/usr/bin/env python3
"""
指定したMarkdownファイルから特定の文字列を削除するスクリプト。

使い方:
    python scripts/delete_string.py <ファイルパス> <削除する文字列>

例:
    python scripts/delete_string.py src/content/chapters/part1-01.md "削除したい文章"
"""

import sys


def delete_string(file_path: str, target: str) -> None:
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    count = content.count(target)
    if count == 0:
        print(f"文字列が見つかりませんでした: {target!r}")
        sys.exit(1)

    new_content = content.replace(target, "")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"{count} 箇所削除しました: {file_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("使い方: python scripts/delete_string.py <ファイルパス> <削除する文字列>")
        sys.exit(1)

    delete_string(sys.argv[1], sys.argv[2])
