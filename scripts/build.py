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

from user_layers import load_layer

ROOT = Path(__file__).resolve().parents[1]
MAPS = ("middle-east", "global")


def main():
    """対象地図と出力先を選び、各処理の失敗を終了コードで呼出元へ伝える。"""
    parser = argparse.ArgumentParser(description="中東図・全球図を再作図します（通常はネット接続不要）")
    parser.add_argument("map", choices=("all",) + MAPS, nargs="?", default="all")
    parser.add_argument("--svg-only", action="store_true", help="PythonだけでSVG・GeoJSONを作成")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument(
        "--data-dir", type=Path, default=ROOT / "user-data",
        help="独自データのフォルダー（global.geojson / middle-east.geojson）",
    )
    parser.add_argument(
        "--check-data", action="store_true",
        help="独自データの形式だけを検査。画像・出力ファイルは作成しない",
    )
    args = parser.parse_args()
    selected = MAPS if args.map == "all" else (args.map,)
    data_dir = args.data_dir.resolve()
    # 全対象の入力を先に検査し、途中の地図だけが更新される失敗を避ける。
    for name in selected:
        data_file = data_dir / f"{name}.geojson"
        if not data_file.is_file():
            parser.error(f"独自データがありません: {data_file}")
        try:
            layer = load_layer(data_file, name)
        except (ValueError, OSError) as error:
            parser.error(str(error))
        print(f"{name}: 独自データ {len(layer['features'])} 件を確認", flush=True)
    if args.check_data:
        print("形式チェック完了。情報の真偽や配置は、出典と生成画像で確認してください。")
        return
    output = args.output_dir.resolve()
    for name in selected:
        if (output / f"{name}.geojson").resolve() == (data_dir / f"{name}.geojson").resolve():
            parser.error("入力GeoJSONを上書きしないよう、--output-dir は --data-dir と別の場所にしてください。")
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
             "--output-dir", str(output),
             "--data-file", str(data_dir / f"{name}.geojson")],
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
