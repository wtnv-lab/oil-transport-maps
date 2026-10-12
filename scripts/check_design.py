"""設定の整合と、単色面に載る主要文字のコントラストを検査する。

地図背景の各画素や色覚特性はこの数値だけで評価できない。図の目視確認を
置き換えず、WCAG適合や全ルートの識別性を認証するものではない。
"""
import argparse
import json
from pathlib import Path

from design_system import MAP_IDS, contrast_ratio, load_design


def inspect_design():
    results = {}
    failures = []
    for map_id in MAP_IDS:
        design = load_design(map_id)
        colors = design["colors"]
        pairs = []
        # 縮小後も読む本文は通常文字の4.5:1を設計目標にする。
        for foreground, background in (("primary", "frame"), ("secondary", "panel"), ("muted", "panel"), ("strong", "ink")):
            ratio = contrast_ratio(colors[foreground], colors[background])
            target = design["contrast"]["body_target"]
            passed = ratio >= target
            pairs.append({"foreground": foreground, "background": background, "ratio": round(ratio, 2), "target": target, "pass": passed})
            if not passed:
                failures.append(f"{map_id}: {foreground}/{background} = {ratio:.2f} < {target}")
        results[map_id] = {"version": design["version"], "contrast": pairs}
    return {"maps": results, "failures": failures, "scope": "単色面の文字を対象とする設計検査。地図全体のアクセシビリティ認証ではありません。"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="検査結果JSONの保存先（省略時は標準出力のみ）")
    args = parser.parse_args()
    report = inspect_design()
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output)
    print(output, end="")
    if report["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
