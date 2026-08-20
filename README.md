# FK Builder

Autodesk Maya向けの、**Joint階層からFK Controller Rigを自動構築するためのリギングツール**です。

Controllerの作成、位置合わせ、階層化、Constraint、Shape、Color、Channel Lockなど、FKリグ構築時に繰り返し発生する作業をひとつのUIからまとめて設定・実行できます。

手作業による設定漏れや命名ミスを減らしながら、**素早く、一貫した構造のFKリグを構築すること**を目的として開発しました。

---

## Features

* **Automatic FK Rig Build**
  選択したRoot Joint以下の階層を解析し、Joint構造に対応したFK Controller Rigを自動構築します。

* **Controller Customization**
  ControllerのPosition / Rotation / Channel Lock / Color / ShapeをBuild前に設定できます。

* **Flexible Output Structure**
  末端JointのController生成やZERO Groupの有無を選択でき、用途に合わせて出力するHierarchyを変更できます。

* **Visibility Control**
  任意のControllerへ表示切替Attributeを追加し、生成したFK Controller群のVisibilityをまとめて管理できます。

* **Shape Library**
  複数のController Shapeから用途に合った形状を選択できます。

* **Validation & Rollback**
  Build前に必要なNodeや設定を検証し、途中で問題が発生した場合もSceneへの影響を抑えます。

* **Reusable Workflow**
  特定のキャラクター専用ではなく、異なるJoint Chainへ繰り返し利用できるFK Builderとして設計しています。

---

## Overview

FK Controller Rigを手作業で構築する場合、

**Controller作成 → Jointへの位置合わせ → Shape調整 → ZERO Group作成 → 階層化 → Constraint → Color設定 → Channel Lock**

といった定型作業をJointごとに繰り返す必要があります。

Joint数が増えるほど作業量が増えるだけでなく、命名、階層、Constraint、Channel設定などの小さな設定漏れも発生しやすくなります。

FK BuilderではRoot Jointを指定するとJoint階層を解析し、必要なControllerを親から子へ自動構築します。

```text
Joint Hierarchy
      ↓
Hierarchy Analysis
      ↓
Build Settings
      ↓
Controller Generation
      ↓
FK Hierarchy
      ↓
Constraint
      ↓
Validation
```

単純にControllerを大量生成するのではなく、**構築前に見た目・操作方法・出力構造をまとめて指定し、一貫したFK Rigとして出力できること**を重視しています。

---

## Main Functions

### Automatic FK Build

Root Jointを指定すると、そのJoint以下の階層を解析し、対応するControllerを自動生成します。

Joint階層に合わせてController側にもFK階層を構築するため、Build後すぐに通常のFK Controllerとして操作できます。

繰り返し発生するController作成や階層設定をまとめて処理することで、手作業による設定差を減らします。

---

### Controller Position / Rotation

Controllerの位置・回転をBuild前に調整できます。

JointへControllerを配置したあとに一つずつShapeを修正するのではなく、生成前の設定として調整できるため、Build後の手直しを減らせます。

Controllerの見た目を調整するための処理と、実際にアニメーションで使用するTransformをできるだけ分離し、扱いやすいControllerを生成することを意識しています。

---

### Channel Lock

Controllerごとに不要なTransform ChannelをLockできます。

例えば回転のみを使用するFK Controllerでは、不要なTranslate / Scale Channelを制限することで誤操作を防止できます。

単にControllerを生成するだけではなく、**アニメーターがどのChannelを操作すればよいか分かりやすい状態まで構築すること**を目的としています。

---

### Controller Color

Controller ColorをBuild前に設定できます。

左右や部位ごとにControllerの色を分けることで、Viewport上での視認性を高められます。

Controller生成後に一つずつ色を設定する必要がなく、Build時点で見た目のルールを統一できます。

---

### Controller Shape

用途に合わせてController Shapeを選択できます。

Controllerの役割に応じてShapeを変更できるため、単一の形状だけでFK Rigを構築するのではなく、操作性や視認性を考慮したController構成にできます。

Shape DataとBuild処理を分離することで、Shape Libraryを追加・変更しやすい構造を意識しています。

---

### End Joint Option

Joint Chainの末端JointにControllerを生成するかどうかを選択できます。

```text
Create

Joint
└─ Joint
   └─ End Joint
      └─ Controller


Exclude

Joint
└─ Joint
   └─ End Joint
```

末端Jointまで直接操作したい場合は作成し、末端Jointを構造上の終端としてのみ使用する場合は除外できます。

Rigの用途によって必要なController構成が異なるため、固定仕様にせず選択可能にしています。

---

### ZERO Group Option

Controller生成時に、各ControllerへZERO Groupを作成するかどうかを選択できます。

```text
Create

Controller_ZERO
└─ Controller


Exclude

Controller
```

ZERO Groupを使用する場合は、Controllerの初期Transformを保持したままOffset階層として利用できます。

一方で、既存Rigへ追加する場合や、必要以上にHierarchyを増やしたくない場合にはZERO Groupを除外できます。

特定のRig構造をツール側から強制するのではなく、**用途や既存Hierarchyに合わせて出力構造を選択できること**を重視しています。

---

### Visibility Control

任意のControllerを表示切替Controllerとして指定できます。

指定したControllerへVisibility Attributeを追加し、生成したFK Controller群の表示をまとめて管理します。

Attribute名もUIから設定できるため、

```text
Settings_CTRL
└─ FK-finger
```

のようにRigの用途に合わせた表示管理ができます。

Visibility管理をFK Controllerごとに設定する必要がなく、Rig全体の操作を一か所へ集約できます。

---

## Workflow

基本的なFK Rigの構築は、以下の流れで行います。

1. FK化したい階層の**Root Joint**を選択
2. `設定`からRoot Jointを登録
3. 必要に応じて表示切替Controllerを設定
4. Controller Sizeを調整
5. Position / Rotationを設定
6. Channel Lockを設定
7. Controller Colorを設定
8. Controller Shapeを選択
9. 末端Jointを**作成 / 除外**から選択
10. ZERO Groupを**作成 / 除外**から選択
11. `FKを作成`を実行
12. LogからBuild結果を確認

```text
Select Root Joint
       ↓
Configure Controller
       ↓
Configure Hierarchy
       ↓
Build FK
       ↓
Validate
       ↓
Ready to Animate
```

JointごとにControllerを作成して設定するのではなく、**Build前に必要な情報をまとめて指定し、一度のBuildでFK Rigを完成させる**ワークフローにしています。

---

## Design

### Fast Rig Construction

FKリグの構築では、高度な処理だけでなく「同じ操作を何度も繰り返すこと」も大きな作業負担になります。

Controller作成、位置合わせ、階層化、Constraint、Color、Channel Lockなどの定型作業をまとめて自動化することで、リガーがControllerの操作性やRig全体の設計など、より重要な調整へ時間を使えることを目指しています。

---

### Animator Friendly

自動生成されたControllerをそのままアニメーション作業へ使用しやすい状態にすることを意識しています。

* 不要ChannelのLock
* Controller Colorによる視認性向上
* 用途に応じたController Shape
* Visibilityの一括管理
* 予測しやすいFK Hierarchy

など、Rigを「構築できること」だけでなく、**構築後に扱いやすいこと**も設計対象としています。

---

### Flexible Output Structure

Rigの構造は制作環境や用途によって異なるため、生成するHierarchyをひとつの形式へ固定していません。

末端JointのController生成やZERO Groupの有無を選択可能にすることで、

* 新規Rigの構築
* 既存Rigへの追加
* シンプルなFK Chain
* Offset階層を必要とするRig

など、それぞれのワークフローに合わせた出力ができます。

**自動化によって制作側へ構造を強制するのではなく、必要な部分だけを自動化できる柔軟性**を意識しています。

---

### Predictable Structure

自動化によってRig内部をブラックボックス化しないことも重視しています。

Joint階層を基準としてController階層を構築し、生成されるController / ZERO Group / Constraintの関係を追いやすい構造にしています。

Build後に手作業で調整したい場合でも、どのNodeが何のために存在しているのか把握しやすい状態を目指しています。

---

### Reusability

特定のキャラクター専用の処理としてではなく、Root Jointを起点として異なるJoint Chainへ使用できる構造にしています。

キャラクターごとに同じFK構築スクリプトを書き直すのではなく、設定を変更することで同じBuilderを再利用できることを重視しています。

---

## Architecture

処理をUIへ集中させず、責務ごとにモジュールを分離しています。

```text
                  FK Builder
                      │
              ┌───────┴───────┐
              │               │
              UI          Build Settings
              │               │
              └───────┬───────┘
                      ▼
                   Builder
                      │
          ┌───────────┼───────────┐
          │           │           │
      Hierarchy   Controller   Shape Data
          │           │           │
          └───────────┼───────────┘
                      ▼
                  Maya Scene
```

### UI

ユーザーから、

* Root Joint
* Visibility
* Controller Size
* Position / Rotation
* Channel Lock
* Color
* Shape
* End Joint
* ZERO Group

などのBuild設定を受け取ります。

### Builder

ValidationからController生成、Hierarchy構築、Constraint、最終確認まで、FK Build全体を管理します。

### Hierarchy

Root Joint以下のJoint構造を解析し、親子関係に対応したFK Controller Hierarchyを構築します。

### Controller

NURBS Curve Controllerの生成やShape処理、Transform関連の処理を担当します。

### Shape Data

Controller Shapeの定義をBuild Logicから分離し、Shapeの追加・変更を行いやすくしています。

---

## Validation / Safety

FK Builderでは既存のJoint階層へ処理を行うため、Sceneを不用意に変更しないことを重視しています。

Build前に必要な情報を確認し、問題がある場合は処理を開始しません。

主な確認対象は、

* Root Joint
* Joint Hierarchy
* Controller Name
* Existing Node
* Shape Data
* Visibility Controller
* Visibility Attribute
* Build Settings

などです。

また、Build処理をひとつのUndo単位として扱い、途中でエラーが発生した場合にSceneへ不完全なRigが残ることをできるだけ防ぎます。

自動化による速度だけでなく、**既存Sceneに対して安心して実行できること**を重要な要件としています。

---

## Testing

Mayaに依存しない処理については、可能な範囲でMaya Scene Operationから分離してTestできる構造にしています。

主なTest対象は、

* Naming
* Selection Validation
* Joint Hierarchy
* Controller Settings
* Shape Data
* Color Resolution
* Visibility Attribute
* Branch Processing

などです。

GitHub Actionsでは、Push / Pull Request時に自動Testを実行します。

```text
Push / Pull Request
        ↓
Compile Check
        ↓
Unit Tests
        ↓
Import Check
        ↓
Result
```

コード変更によって既存機能へRegressionが発生していないか確認し、継続的に修正・機能追加を行いやすい状態を維持します。

---

## Technical Details

* Autodesk Maya 2026
* Python 3
* maya.cmds
* PySide6
* shiboken6
* JSON
* unittest
* GitHub Actions

### Technical Focus

* Joint Hierarchyの自動解析
* Joint構造に対応したFK Hierarchy生成
* Controller Shape Dataの分離
* Controller Position / Rotation調整
* End Jointの選択的生成
* ZERO Groupの選択的生成
* Visibility Attributeの自動構築
* Channel Lockの自動設定
* Build前Validation
* Undo / Rollbackを考慮したScene操作

---

## Requirements

* Autodesk Maya 2026
* Python 3
* PySide6 / shiboken6

PySide6 / shiboken6はMaya 2026に同梱されているものを使用します。

外部Python Packageは必要ありません。

---

## Installation

リポジトリをMayaからアクセス可能な場所へCloneまたはDownloadします。

例：

```text
Documents/
└─ maya/
   └─ scripts/
      └─ FK-Builder/
```

Maya Script EditorのPythonタブからLauncherを実行します。

```python
from pathlib import Path
import runpy
from maya import cmds

tool_root = Path(cmds.internalVar(userScriptDir=True)) / "FK-Builder"
runpy.run_path(str(tool_root / "launch_fk_builder.py"))
```

---

## Project Structure

```text
FK-Builder/
│
├─ fk_builder/
│  ├─ main.py
│  ├─ ui.py
│  ├─ builder.py
│  ├─ controller.py
│  ├─ hierarchy.py
│  ├─ shape_library.py
│  ├─ shape_picker.py
│  ├─ utils.py
│  │
│  └─ data/
│     └─ bundled_shapes.json
│
├─ tests/
│
├─ docs/
│  └─ media/
│
├─ .github/
│  └─ workflows/
│
├─ launch_fk_builder.py
└─ README.md
```

各モジュールの責務を分離することで、UI変更、Controller生成処理、Hierarchy解析、Shape追加などの変更が互いに影響しにくい構造を意識しています。

---

## Current Scope / Limitations

現在のFK Builderは、**Joint階層からFK Controller Rigを構築すること**に機能を絞っています。

### Supported

* Root Joint以下のFK Rig生成
* Joint Hierarchyの自動解析
* Branchを含むJoint階層
* Controller Position / Rotation設定
* Channel Lock
* Controller Color
* Controller Shape
* End Joint Create / Exclude
* ZERO Group Create / Exclude
* Visibility Attribute
* FK Controller Hierarchy生成

### Current Scope

* IK Rigの自動構築は対象外
* FK / IK Switchの生成は対象外
* Skinning / Weight処理は対象外
* Maya 2026を基準に開発・検証

FK Builder単体ですべてのRigを自動生成するのではなく、**FK Controller Rigを素早く、一貫性のある構造で構築すること**を現在の役割としています。

---

## Background

FK Rigを制作する中で、Controller作成そのものより、

* Jointへの位置合わせ
* Controller Shapeの調整
* ZERO Group作成
* Naming
* Controller階層化
* Constraint
* Color設定
* Channel Lock
* Visibility設定

といった定型作業を何度も繰り返すことに制作時間を取られることが課題でした。

```text
Production Problem
       ↓
Repeated FK Setup
       ↓
Prototype Automation
       ↓
Controller Customization
       ↓
Hierarchy Options
       ↓
Validation
       ↓
Reusable FK Builder
```

そこで、単純なController自動生成スクリプトではなく、**見た目・操作性・Hierarchy・安全性まで含めてFK Rig構築をひとつのワークフローとして扱えるツール**として開発しました。

また、自動化する範囲を固定するのではなく、末端JointやZERO Groupの生成を選択できるようにすることで、異なるRig構造や制作方針にも対応できる設計にしています。

手作業をすべて置き換えることではなく、**繰り返し作業を自動化しながら、リガーが必要な構造を選択できること**を目指しています。

---

## License

MIT License

Copyright (c) 2026 Yuzuki Midoshima
