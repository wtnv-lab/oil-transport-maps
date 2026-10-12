#!/usr/bin/env python3
"""地図生成の入口。保存済み背景からSVGを生成し、必要に応じてPNG化する。

ニュースやAISの自動取得は行わない。PNG出力はNode.js側に委ねるため、
--svg-onlyならPython標準ライブラリだけで実行できる。
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MAPS = ("middle-east", "global")


def main():
    """対象地図と出力先を選び、各処理の失敗を終了コードで呼出元へ伝える。"""
    parser = argparse.ArgumentParser(description="中東図・全球図を再作図します（通常はネット接続不要）")
    parser.add_argument("map", choices=("all",) + MAPS, nargs="?", default="all")
    parser.add_argument("--svg-only", action="store_true", help="PythonだけでSVG・GeoJSONを作成")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    selected = MAPS if args.map == "all" else (args.map,)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    node = os.environ.get("NODE", "node")
    # SVGだけを使う人には、Node.jsやブラウザーの準備を要求しない。
    if not args.svg_only:
        if not shutil.which(node):
            parser.error("Node.js 20以上が必要です。SVGのみの場合は --svg-only を指定してください。")
        if not (ROOT / "node_modules/playwright/package.json").exists():
            parser.error("依存ライブラリがありません。リポジトリで npm ci を実行してください。")
    for name in selected:
        print(f"\n{name} を作成します", flush=True)
        # 同じPythonで地図固有の作図処理を実行。作業ディレクトリに依存しない。
        subprocess.run(
            [sys.executable, str(ROOT / "maps" / name / "build.py"),
             "--output-dir", str(output)],
            check=True,
        )
        if not args.svg_only:
            subprocess.run(
                [node, str(ROOT / "scripts/render.cjs"),
                 str(output / f"{name}.svg"), str(output / f"{name}.png")],
                check=True,
            )
    print(f"\n出力先: {output}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
