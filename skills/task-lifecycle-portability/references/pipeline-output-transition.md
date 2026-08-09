# Pipeline Output Model Transition (2026-06-11)

## What Changed

`<domain-skill>/scripts/pipeline.py` was updated to write all generated files to `output/` instead of the task root.

| Before | After |
|--------|-------|
| RECORDING.md at root | output/RECORDING.md |
| COMPOSITING.md at root | output/COMPOSITING.md |
| IMAGE_SLIDESHOW.md at root | output/IMAGE_SLIDESHOW.md |
| SUBTITLE_SPEC.md at root | output/SUBTITLE_SPEC.md |
| tts-<hash6>/ at root | output/tts-<hash6>/ |
| image-slideshow-* at root | output/image-slideshow-*/ |
| subtitle-gen-* at root | output/subtitle-gen-*/ |
| browser-video-recording-* at root | output/browser-video-recording-*/ |
| compositing-* at root | output/compositing-*/ |
| REQUIREMENTS.md at root | input/REQUIREMENTS.md (fallback to root) |
| `--clean` positive-list | `rm -rf output/` |

## Why

Exclusion-based deletion (`find . -not -name 'REQUIREMENTS.md' -delete` or positive-listing `rm -rf tts-*/ RECORDING.md ...`) destroyed TASK.md because it was a regular file in the task root. The structural fix: put all generated files in a single `output/` directory, then cleaning is simply `rm -rf output/`.

## Migration

Existing pipeline tasks were migrated manually:
1. Created `input/` + `output/` dirs
2. Moved REQUIREMENTS.md + images/ into `input/`
3. Moved all generated specs and phase dirs into `output/`
4. TASK.md, CHANGELOG.md, .hermes-task.json converted to symlinks

## TTS cache location

TTS cache scanning now looks in `output/` directory for existing tts-* dirs:
- Old: `os.listdir(TASK_DIR)` → look for tts-* at root
- New: `os.listdir(os.path.join(TASK_DIR, OUTPUT_DIR))` → look for tts-* under output/

## script path

`<skill-path>/scripts/pipeline.py`
