#!/usr/bin/env python3
"""拡大図のSVG生成・矢印配置・PNG化・配置と海陸の検査を順に実行する。"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist')
    parser.add_argument('--svg-only', action='store_true',
                        help='PythonによるSVG・GeoJSON生成のみ。矢印配置・PNG・検査は省略')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    node = os.environ.get('NODE', 'node')
    if not args.svg_only:
        if not shutil.which(node):
            parser.error('Node.jsが必要です。SVGのみなら --svg-only を指定してください。')
        if not (ROOT / 'node_modules/playwright/package.json').exists():
            parser.error('リポジトリのルートで npm ci を実行してください。')
    subprocess.run([sys.executable, str(HERE / 'build.py'),
                    '--output-dir', str(output)], check=True)
    if not args.svg_only:
        stem = str(output / 'gulf-hormuz-oman')
        for script in ('render.cjs', 'check-water.cjs'):
            subprocess.run([node, str(HERE / script), stem], check=True)
    print(f'出力先: {output}')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
