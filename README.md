# Finger FK Builder

Autodesk Maya 2026向けのFinger FKコントローラー生成ツールです。選択した指のジョイント階層から、キューブ型コントローラーとZeroグループをまとめて作成します。

## Features

- 選択したルート以下のFinger Jointを自動取得
- ジョイント名からController／Zero Group名を生成
- NURBS Cube Controllerを作成
- 指の親子関係を維持したFK階層を構築
- Controller Size、Color、End Jointの生成を設定可能
- Maya Undoに対応
- Maya API処理とUI処理を分離

## Requirements

- Autodesk Maya 2026
- Python 3.11
- PySide6（Maya同梱版）

## Installation

1. このリポジトリをダウンロードします。
2. `Finger-FK-Builder`フォルダをMayaの`scripts`フォルダへ配置します。
3. Mayaを再起動します。

一般的な配置先は次のとおりです。

```text
<Maya userAppDir>/scripts/Finger-FK-Builder/
```

## Usage

Maya Script EditorのPythonタブで実行します。

```python
from pathlib import Path
import runpy
from maya import cmds

scripts_dir = Path(cmds.internalVar(userScriptDir=True))
runpy.run_path(
    str(scripts_dir / "Finger-FK-Builder" / "launch_finger_fk_builder.py")
)
```

UIを開いたら、ルートとなるFinger Jointを選択してBuildを実行します。

## Project Structure

```text
Finger-FK-Builder/
├── FingerFKBuilder/
│   ├── builder.py
│   ├── controller.py
│   ├── hierarchy.py
│   ├── main.py
│   ├── ui.py
│   └── utils.py
├── launch_finger_fk_builder.py
└── README.md
```

## Architecture

- `builder.py`: ビルド処理のオーケストレーション
- `controller.py`: NURBSコントローラー生成
- `hierarchy.py`: FK親子階層の構築
- `utils.py`: Mayaアクセス、選択、命名処理
- `ui.py`: PySide6 UI
- `main.py`: Mayaウィンドウとの統合とエントリーポイント

## Version

`1.0.0`
