# FK Builder for Maya

Autodesk Maya 2026で、選択したJoint階層から汎用FK Controller Rigを構築するRigger / Technical Artist向けツールです。Controller生成、Zero Group、階層化、Constraint、Channel Lock、Color、Shape、Visibilityを一貫した手順で設定します。

## Overview

JointごとのController作成と命名、位置合わせ、階層化、Constraint設定を自動化し、手作業による設定漏れを減らします。Build前の検証、Build後のJoint行列検証、失敗時のUndo rollbackにより、既存のbind poseを保護します。

## Demo

デモ画像・動画は[`docs/media/`](docs/media/)へ追加できます。ポートフォリオ素材をMaya packageから分離して更新できる構成です。

## Features

- Root Joint以下を親から子の順で検出
- 対応するJoint suffixから`*_anim` Controllerと`*_zero` Groupを生成
- 標準Cubeまたは同梱MOX NURBS curve shapeを選択
- Controller SizeとCVへのPosition / Rotation Offset適用
- 全体、名前ルール、分岐単位でのColor・Offset・Channel Lock設定
- End JointのInclude / Exclude
- ControllerとZero Groupの重複名検証
- Joint階層に対応する再帰的FK Controller階層
- Parent ConstraintとScale Constraintの作成
- 任意のSettings ControllerへのVisibility attribute追加
- Build前後のJoint world matrix比較
- 例外発生時の単一Undo chunk rollback

## Installation

1. リポジトリをMayaからアクセス可能な場所へcloneまたはdownloadします。
2. Maya Script EditorのPythonタブからlauncherを実行します。

Mayaユーザースクリプトフォルダへ配置する例:

```text
<Maya user scripts>/FK-Builder/
```

## Usage

```python
from pathlib import Path
import runpy
from maya import cmds

tool_root = Path(cmds.internalVar(userScriptDir=True)) / "FK-Builder"
runpy.run_path(str(tool_root / "launch_fk_builder.py"))
```

1. 対象階層のRoot Jointを選択して`SET`を押します。
2. Controller SizeとEnd Joint設定を確認します。
3. Shape、Color、Offset、Channel Lockの適用方法を選択します。
4. 必要ならSettings ControllerとVisibility attributeを設定します。
5. `BUILD FK`を実行し、Logで結果を確認します。

## Technical Highlights

- UI、Build orchestration、curve生成、階層処理、Maya helperをmodule単位で分離
- `maya.cmds`を遅延importし、Builderへcommand moduleを注入可能
- `BuildResult` frozen dataclassで生成nodeを明示的に返却
- Maya DAG long pathを使った親子探索とrecursive branch grouping
- duplicate controller / zero nameをBuild前に検出・回避
- Curve CVへEuler rotationとtranslationを焼き込み、transformをfreeze
- 複数componentのNURBS shapeを1つのController transformへ統合
- Constraint作成後にJoint world matrixを比較し、bind pose変化時はrollback
- Maya非依存ロジックを標準`unittest`で検証

## Project Structure

```text
fk_builder/                    公開Python package
  builder.py                   検証とFK build orchestration
  controller.py                NURBS controller factory
  hierarchy.py                 FK hierarchy構築
  shape_library.py             同梱shape JSON読込
  shape_picker.py              PySide6 visual shape picker
  ui.py                        PySide6 UI
  main.py                      Maya main window integration
  utils.py                     命名・選択・Maya helper
  data/mox_shapes.json         Controller shape data
tests/                         Maya非依存unit tests
docs/media/                    Demo素材
launch_fk_builder.py           Maya launcher
```

既存のMaya launcherと`fk_builder` importを維持するため、無理な`src/` layoutへの変更は行っていません。

## Requirements

- Autodesk Maya 2026
- Python 3.11（Maya 2026同梱）
- PySide6 / shiboken6（Maya 2026同梱）
- 外部Python package不要

## Testing

### Automated Tests

Maya非依存テストは標準ライブラリだけで実行できます。

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

自動テストは命名、選択検証、Joint階層順、Color解決、MOX JSON検証、CV offset計算、Visibility attribute正規化、Shape validation、branch groupingを対象とします。GitHub Actionsでは全Pythonファイルのcompile checkとMaya非依存import checkも実行します。

### Maya Manual Tests

- launcherとPySide6 windowの起動・再読み込み
- Root Joint検出とEnd Joint除外
- Cube / MOX shapeのcurve生成とvisual picker
- Color、Offset、Channel Lockの全適用mode
- Controller / Zero hierarchyと親階層
- Parent / Scale Constraintとbind pose維持
- Visibility attributeとroot zero visibility接続
- duplicate node検出とエラー表示
- Build途中の失敗時にUndoで完全に戻ること
- Maya Undo履歴と既存animationへの影響

## Development Workflow

変更は`feature/*`、`fix/*`、`chore/*`ブランチで行い、`main`向けPull Requestを作成します。CI成功とMaya手動確認の後にのみmergeし、`main`を公開可能な安定版として維持します。

## Third-Party Assets

`fk_builder/data/mox_shapes.json`のmetadataは`MoxRigController 2015-07-23`をsourceとして示しています。公開・再配布前に、リポジトリ所有者が元データの利用条件と必要なattributionを確認してください。

## License

ライセンスは現在指定されていません。コードおよび同梱shape dataの利用・再配布条件は、権利確認後に明示してください。
