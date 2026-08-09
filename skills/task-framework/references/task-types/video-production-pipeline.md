# video-pipeline 任务生命周期

## 创建

1. 通过 `task_create --skill <video-skill>` 创建
2. 创建 `tasks/<ts>.<name>-<hash6>/` 目录，含 `input/` `output/` `scripts/`
3. 用户填写的 `REQUIREMENTS.md` 和 `images/`（封面图片）放在 `input/`
4. `<video-skill>` 的 `scripts/create_task.py` 生成初始 `TASK.md`
5. 写入 `.hermes-task.json`

## 执行

完整的 5 阶段流水线，使用 `pipeline.py` 驱动：

| Phase | 生成到 | 说明 |
|-------|--------|------|
| 0 | 自身 | 解析 REQUIREMENTS.md → 翻译（如需要） |
| 1a | `output/tts-<hash6>/` | TTS 音频 |
| 1b | `output/image-slideshow-<hash6>/` | 封面视频 |
| 1c | `output/subtitle-gen-<hash6>/` | 字幕 |
| 2 | `output/` | 计算时间线 → RECORDING.md + COMPOSITING.md |
| 3 | `output/browser-video-recording-<hash6>/` | 浏览器录屏 |
| 4 | `output/compositing-<hash6>/` | 合成最终视频 |

示例目录结构（执行后）：

```
tasks/<ts>.<name>-<hash6>/
├── input/
│   ├── REQUIREMENTS.md
│   └── images/
│       └── cover.png
├── output/
│   ├── tts-a3f8c2/
│   │   ├── audio_000001.mp3
│   │   └── audio_manifest.json
│   ├── image-slideshow-a3f8c2/
│   │   └── slideshow.mp4
│   ├── subtitle-gen-a3f8c2/
│   │   └── subtitle_0001.mp4
│   ├── browser-video-recording-a3f8c2/
│   │   └── video.mp4
│   ├── compositing-a3f8c2/
│   │   └── output.mp4
│   ├── RECORDING.md
│   └── COMPOSITING.md
├── TASK.md
├── README.md
├── CHANGELOG.md
└── .hermes-task.json
```

> **迁移说明：** 现有 pipeline 任务（如 `<task-name>-<hash6>`）可能还把 REQUIREMENTS.md 和 images/ 放在根目录。后续对此任务操作时，应迁移到 `input/` + `output/` 模型。

## 修改

- **禁止修改 REQUIREMENTS.md** — 需要改时告知用户，让用户自己改
- 修改后需要重新执行 pipeline

## 清理

```bash
# 方式 A（推荐）：通过 pipeline.py
cd tasks/<ts>.<name>-<hash6>/
python3 <skill-path>/scripts/pipeline.py --clean

# 方式 B：通用清理（input/ 安全）
rm -rf output/
```

`input/` 中的 REQUIREMENTS.md 和 images/ 不受影响。

## 完成

1. 确认 `output/compositing-<hash6>/output.mp4` 存在且可播放（ffprobe 验证）
2. 更新 TASK.md 状态为 `completed`
3. 运行 `python3 scripts/update-index.py  # from the skill directory` 更新索引
