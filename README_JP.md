# Phoo - キーボード駆動のファイル分類ツール

[中文](README.md) | [English](README_EN.md)

> キーを押すだけでファイルが分類される！

Phoo は Python 製のファイル分類ツールです。ショートカットキーを押すだけで画像・動画・Flash ファイルを瞬時に対応フォルダへ振り分けます。

## 主な機能

- **キーボード分類**：カスタマイズ可能なホットキーで即座にファイル分類
- **マルチフォーマット対応**：画像（JPG/PNG/GIF/BMP/TIFF/ICO）、動画（MP4/AVI/MOV/WMV/FLV/MKV）、Flash（SWF）
- **コピーモード / 移動モード**：安全なコピーモード（デフォルト）または移動モード
- **動画サムネイルプレビュー**：最初のフレームをサムネイル表示（opencv-python 必須）
- **ファイル情報表示**：ファイルタイプと撮影日を表示（EXIF > ファイル名解析 > ファイルタイムスタンプ）
- **スマート日付認識**：主要スマホ/APP命名形式に対応（IMG_, VID_, Screenshot, mmexport, タイムスタンプ等）
- **元に戻す**：Ctrl+Z で取り消し、複数回対応（セッション内のみ）
- **削除**：Delete キーで現在のファイルを削除（確認ダイアログ付き）
- **スキップ**：W キーでスキップして次のファイルへ
- **ソート**：名前・日付・サイズ、昇順/降順
- **サブフォルダスキャン**：再帰スキャンのオン/オフ
- **設定の永続化**：セッション間で設定を自動保存
- **重複保護**：同名ファイルの自動リネーム

## クイックスタート

### 動作環境

- Python 3.7+
- Windows / macOS / Linux

### 依存ライブラリのインストール

```bash
pip install pillow pywin32
```

> オプション：動画サムネイルプレビューには `opencv-python` をインストール
> ```bash
> pip install opencv-python
> ```

### 実行

```bash
python phoo.py
```

## ショートカットキー

| ショートカット | アクション |
|----------------|-----------|
| `1` `2` `3` ... | 対応フォルダにファイルを分類 |
| `W` | 次のファイルへスキップ |
| `Delete` | 現在のファイルを削除（確認付き） |
| `Ctrl+Z` | 直前の操作を取り消し |
| `Tab` | コピー/移動モード切替 |

> ショートカットキーは設定パネルでカスタマイズ可能です。

## スタンドアロン EXE 化

```bash
pip install pyinstaller
pyinstaller --onefile --windowed phoo.py
```

EXE ファイルは `dist/` ディレクトリに生成されます。

## 技術スタック

- Python 3
- Tkinter（GUI）
- Pillow（画像処理 + EXIF 読み取り）
- OpenCV（オプション、動画サムネイル）

## ライセンス

[MIT License](LICENSE)

## クレジット

オリジナルプロジェクト：[RxinnotRstar](https://github.com/RxinnotRstar)。メンテナンス・拡張：[YZH0916](https://github.com/YZH0916)。
