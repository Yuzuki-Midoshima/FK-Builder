# FK Builder for Maya

Autodesk Maya 2026で、選択したJoint階層から汎用FK Controller Rigを構築するRigger / Technical Artist向けツールです。Controller生成、Zero Group、階層化、Constraint、Channel Lock、Color、Shape、Visibilityを一つのUIで設定できます。

## Demo

デモ画像・動画は[`docs/media/`](docs/media/)へ追加できます。

## Overview

JointごとのController作成と命名、位置合わせ、階層化、Constraint設定を自動化します。Build前後のJoint world matrix比較、重複名検証、失敗時のUndo rollbackにより、既存のbind poseを保護します。

## Features

- Root Joint以下を親から子の順で検出
- Joint suffixから`*_anim` Controllerと`*_zero` Groupを生成
- 標準Cube、同梱の自作基本shape、外部JSON Shape Libraryを選択
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

リポジトリをMayaからアクセス可能な場所へcloneまたはdownloadします。

```text
<Maya user scripts>/FK-Builder/
```

## Usage

Maya Script EditorのPythonタブから実行します。

```python
from pathlib import Path
import runpy
from maya import cmds

tool_root = Path(cmds.internalVar(userScriptDir=True)) / "FK-Builder"
runpy.run_path(str(tool_root / "launch_fk_builder.py"))
```

1. 対象階層のRoot Jointを選択して`SET`を押します。
2. Controller SizeとEnd Joint設定を確認します。
3. Shape、Color、Offset、Channel Lockを設定します。
4. 必要ならSettings ControllerとVisibility attributeを設定します。
5. `BUILD FK`を実行し、Logで結果を確認します。

## Shape Libraries

公開リポジトリには、FK Builder用に新規作成した基本shapeだけを同梱しています。ユーザーが用意する外部shape libraryはRepository外のUserDataから任意で読み込みます。

外部libraryは次のUserDataディレクトリへJSONファイルとして配置します。

```text
<Maya user scripts>/FK-Builder-UserData/shape_libraries/*.json
```

場所を明示する場合は、`FK_BUILDER_USER_DATA_DIR`環境変数へ`shape_libraries`の親ディレクトリを指定できます。`MAYA_APP_DIR`が設定されている環境にも対応します。外部データの入手・利用・保管は、それぞれの利用条件に従ってください。

外部libraryが存在しない場合も同梱shapeだけで起動します。不正なJSONや重複したShape IDは黙って無視・上書きせず、UIのLogへ警告を表示して同梱shapeへフォールバックします。

## Technical Highlights

- UI、build orchestration、curve生成、階層処理、Maya helperをmodule単位で分離
- `maya.cmds`を遅延importし、builderへcommand moduleを注入可能
- `BuildResult` frozen dataclassで生成nodeを明示的に返却
- Maya DAG long pathを使った親子探索とrecursive branch grouping
- Curve CVへEuler rotationとtranslationを焼き込み、Transformをfreeze
- 複数componentのNURBS shapeを一つのController transformへ統合
- 同梱データとリポジトリ外UserDataを分離した汎用JSON Shape Library Loader
- Shape ID重複、schema、degree、CV pointのvalidation
- Maya非依存ロジックを標準`unittest`で検証

## Project Structure

```text
fk_builder/
  builder.py                   Validation and FK build orchestration
  controller.py                NURBS controller factory
  hierarchy.py                 FK hierarchy construction
  shape_library.py             Bundled / external JSON library loader
  shape_picker.py              PySide6 visual shape picker
  ui.py                        PySide6 UI
  main.py                      Maya main-window integration
  utils.py                     Naming, selection, and Maya helpers
  data/bundled_shapes.json     Original FK Builder basic shapes
tests/                         Maya-independent unit tests
docs/media/                    Demo assets
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

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

自動テストは命名、選択検証、Joint階層順、Color解決、同梱shape、外部library探索・読込、重複ID拒否、CV offset計算、Visibility attribute正規化、Shape validation、branch groupingを対象とします。GitHub ActionsではPython 3.11を使い、全Pythonファイルのcompile check、Maya非依存unit test、主要packageのimport checkを実行します。

### Maya Manual Tests

- launcherとPySide6 windowの起動・再読み込み
- 同梱4形状だけでのShape Picker表示とcurve生成
- UserDataに配置した外部libraryのShape Picker表示とcurve生成
- Root Joint検出とEnd Joint除外
- Color、Offset、Channel Lockの全適用mode
- Controller / Zero hierarchyと親階層
- Parent / Scale Constraintとbind pose維持
- Visibility attributeとroot zero visibility接続
- duplicate node検出、エラー表示、Undo rollback

## Development Workflow

変更は`feature/*`、`fix/*`、`chore/*`ブランチで行い、`main`向けPull Requestを作成します。CI成功とMaya手動確認後にのみmergeし、`main`を公開可能な安定版として維持します。

## License

This project is licensed under the [MIT License](LICENSE).
