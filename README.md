# YDL — YouTube ダウンローダー

YouTubeの動画を **MP3（音声）** または **MP4（動画）** で保存できる、Windows向けのデスクトップアプリです。

<table>
  <tr>
    <td>
      <img src="https://github.com/user-attachments/assets/dcfa2ecb-87f5-4397-86de-5d02813a8f28" width="280" alt="画像1">
    </td>
    <td>
      <img src="https://github.com/user-attachments/assets/8e8e8e2f-db62-4ae6-85a1-bd30da578673" width="280" alt="画像2">
    </td>
  </tr>
</table>

![Views](https://komarev.com/ghpvc/?username=Sumomodayo&repo=Youtube-Downloader&label=Repository%20Views&color=7c3aed&style=flat)
![GitHub Downloads](https://img.shields.io/github/downloads/Sumomodayo/Youtube-Downloader/total?label=Downloads&color=7c3aed)

## 機能

* MP3 / MP4 の切り替え
* 音質（128k / 192k / 256k / 320k）の選択
* 画質（360p〜4K）の選択
* ファイル名の指定（空欄の場合は元動画のタイトルを使用）
* 保存先の変更

## インストール方法

1. `YDL-Setup.exe` を起動します。
2. インストーラーの画面に従ってインストールします。
3. インストール完了後、デスクトップのショートカット、またはインストール先からYDLを起動します。

## 使い方

1. YDLを起動します。
2. 上部の切り替えボタンで **MP3** または **MP4** を選択します。
3. YouTubeのURLを入力します。「貼り付け」ボタンも使用できます。
4. 音質または画質を選択します。
5. 必要に応じてファイル名と保存先を設定します。
6. 「ダウンロード」ボタンを押します。
7. 完了後、「フォルダを開く」ボタンから保存先を開けます。

### 保存先

初期設定では、デスクトップの `YDL` フォルダに保存されます。

MP3とMP4は同じフォルダに保存されます。

## トラブルシューティング

| 症状                                      | 対処方法                                               |
| --------------------------------------- | -------------------------------------------------- |
| ダウンロードに失敗する                             | インターネット接続を確認してください。YouTube側の仕様変更により動作しなくなる場合もあります。 |
| Windows Defender / SmartScreenの警告が表示される | 発行元や入手元を確認してください。不明なファイルや信頼できないファイルは実行しないでください。    |
| アプリが起動しない/インストールできない                               | [Python](https://www.python.org/downloads/)のダウンロードが必要です。それでも解決しない場合はお問い合わせください。                   |

## 使用上の注意

* 本ソフトウェアは個人制作のツールです。利用は自己責任で行ってください。
* ダウンロードは、著作権法およびYouTubeの利用規約を守って行ってください。
* 自分で投稿した動画や、ダウンロードが許可されている動画など、利用する権利があるコンテンツを対象としています。
* 第三者が権利を持つコンテンツを利用する場合は、必要な許可を確認してください。
* URLにプレイリストが含まれていても、ダウンロードされるのは指定した動画1本だけです。
* YouTubeの仕様変更などにより、機能の一部または全部が使用できなくなる場合があります。

## 使用ライブラリ

* [yt-dlp](https://github.com/yt-dlp/yt-dlp) — 動画・音声の取得
* [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) — FFmpegの同梱
* tkinter — GUI
* [PyInstaller](https://pyinstaller.org/) — 実行ファイルの作成
* [Inno Setup](https://jrsoftware.org/isinfo.php) — インストーラーの作成
