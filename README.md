# FK Builder

## Overview

Autodesk Maya 2026で、選択した指のJoint階層からFK Controller Rigを構築するツールです。Cube型NURBS Controller、Zero Group、親子階層、Orient Constraintをまとめて生成します。

Technical Artist／Rigger職への応募を目的に制作・公開しているポートフォリオ作品です。

## Problem

指のJointごとにController作成、位置合わせ、階層化、Constraint、Channel Lockを繰り返す作業は、設定漏れや命名の不統一が起きやすくなります。本ツールは選択したRoot Joint以下を検証し、一貫した命名と階層でFK Rigを構築します。

## Features

- Root Joint以下のJoint階層を親から子の順に取得
- Joint名から`*_anim` Controllerと`*_zero` Group名を生成
- CVへSizeを反映したCube型NURBS Controllerを生成
- 元Jointへ位置・回転を合わせてFK親子階層を構築
- ControllerからJointへOrient Constraintを作成
- End Joint ControllerのInclude／Exclude
- Translate、Rotate、Scale、VisibilityのChannel Lock設定
- Thumb、Index、Middle、Ring、PinkyごとのMaya Color Index設定
- Cool／Warm Color Preset
- 任意のSettings Controllerへ`FK_visibility` Attributeを追加
- 出力名の重複と既存Nodeとの衝突をBuild前に検証
- 失敗時にMaya UndoでBuild処理をロールバック

## Architecture

UI、Build Orchestration、Controller生成、階層処理、Mayaアクセス補助を分離しています。

```text
PySide6 UI (ui.py)
       ↓
Build Orchestration (builder.py)
       ├── Controller Factory (controller.py)
       ├── FK Hierarchy (hierarchy.py)
       └── Validation / Maya Helpers (utils.py)
```

- `ui.py`：入力、オプション、ログ表示
- `builder.py`：検証からController、Constraint生成までのBuild手順
- `controller.py`：Cube Curveの生成とColor設定
- `hierarchy.py`：Joint親子関係に対応したFK階層の構築
- `utils.py`：選択、Joint取得、命名、Maya遅延import
- `main.py`：Maya Main Windowとの統合とWindow管理

Build処理はMaya Undo Chunkで囲み、途中で例外が発生した場合はChunkを閉じてUndoします。

## Requirements

- Autodesk Maya 2026
- Python 3.11
- PySide6（Maya同梱版）

## Installation

`FK-Builder`フォルダをMayaのユーザースクリプトフォルダ直下へ配置します。

```text
<Maya userAppDir>/
└── scripts/
    └── FK-Builder/
```

Maya上のユーザースクリプトフォルダは次のコードで確認できます。

```python
from maya import cmds

print(cmds.internalVar(userScriptDir=True))
```

## Usage

### 起動

Maya Script EditorのPythonタブで次を実行します。Shelfへ登録する場合も同じコードを使用できます。

```python
from pathlib import Path
import runpy
from maya import cmds

tool_root = (
    Path(cmds.internalVar(userScriptDir=True))
    / "FK-Builder"
)
runpy.run_path(str(tool_root / "launch_fk_builder.py"))
```

### 基本操作

1. 指階層のRoot Jointを選択して`SET`を押します。
2. Controller Sizeを設定します。
3. 必要に応じてChannel Lock、Controller Color、End Jointを設定します。
4. Visibilityをまとめて制御する場合は、Settings Controllerを選択してVisibility Controlの`SET`を押します。
5. `BUILD FK`を押します。
6. Logで検出Joint数と作成結果を確認します。

## Project Structure

```text
FK-Builder/
├── fk_builder/
│   ├── __init__.py
│   ├── builder.py
│   ├── controller.py
│   ├── hierarchy.py
│   ├── main.py
│   ├── ui.py
│   └── utils.py
├── tests/
│   └── test_core.py
├── launch_fk_builder.py
├── README.md
└── .gitignore
```

## Testing

命名、選択検証、Joint階層順、部位別Color解決はMayaなしでテストできます。

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Controller生成、Constraint、UI、UndoはMaya APIとSceneを必要とするため、Maya 2026上で手動確認します。

## Known Limitations

- 対象Joint名は`_jnt`で終わる必要があります。
- 出力予定のControllerまたはZero Groupがすでに存在する場合はBuildを中止します。
- 部位別Colorは、Joint名を記号で分割したTokenに`thumb`、`index`、`middle`、`ring`、`pinky`が含まれる場合に適用されます。
- Visibility ControlにはTransform Nodeを1つ指定します。
- Visibility Controlに`FK_visibility` Attributeがすでに存在する場合はBuildを中止します。
- Maya依存部分の自動統合テストは現在ありません。

## License

このリポジトリにはライセンスファイルを設定していません。公開後のコード利用条件は、ライセンスを明示するまで著作権者に留保されます。
