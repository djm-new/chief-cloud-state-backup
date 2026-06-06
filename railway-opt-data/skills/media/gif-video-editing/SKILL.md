---
name: gif-video-editing
description: "Edit short GIF/MP4 reaction clips: overlays, face swaps, coordinate grids, timing/fade matching, and Telegram-ready exports."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [gif, video, editing, face-overlay, media, telegram]
---

# GIF / Short Video Editing

Use this when the user wants a GIF/MP4 modified rather than merely searched/downloaded: swapping a person, adding an overlay, matching a meme/reaction clip, creating coordinate grids, or exporting Telegram-ready MP4/GIF outputs.

## Core workflow

1. **Identify the real reference asset.** Telegram often delivers GIFs as `.mp4` videos. Inspect cached media paths, dimensions, frame count, duration, and FPS before editing.
2. **Preserve the original clip unless told otherwise.** For “modeled on this” or “change the person,” default to preserving the original background/body/motion/timing and altering only the requested region. Do not replace the entire scene with a floating sticker unless the user asks for sticker/composite style.
3. **Create contact sheets early.** Export a small frame grid so the user can point at frames/positions without guessing.
4. **Use coordinate grids for iterative alignment.** Generate readable full-frame and zoomed coordinate grids with current boxes marked. Let the user reply with `x=...→..., y=...→...` or natural nudges (“10px right”, “include more hair”).
5. **Separate source crop from target placement.** Explain and tune these independently:
   - Source crop/mask: which part of the replacement image is used.
   - Target overlay box: where that result is placed in the reference GIF/video.
6. **Match opacity/timing.** If the original subject fades/moves/disappears, apply the same envelope to the overlay. Verify final frames do not retain or reintroduce the overlay.
7. **Export both formats.** MP4 is usually best for Telegram; provide actual `.gif` only when requested or useful.

## Implementation pattern

Python with Pillow + imageio is enough for deterministic first-pass edits:

```python
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import imageio.v3 as iio
import numpy as np

frames = list(iio.imiter('/path/ref.mp4'))
source = Image.open('/path/person.jpg').convert('RGBA')
# crop/mask source, resize to target box, alpha-composite over each frame
# iio.imwrite('/path/out.mp4', np_frames, fps=10, codec='libx264', quality=8)
# iio.imwrite('/path/out.gif', np_frames, duration=100, loop=0)
```

Use `ffmpeg` for quick contact sheets:

```bash
ffmpeg -y -i ref.mp4 -vf "fps=2,scale=160:-1,tile=4x2" contact_sheet.jpg
```

## Face/overlay specifics

- Prefer a soft oval/face-shaped alpha mask over hard rectangular crops.
- If the visible face looks too small, check whether the *transparent canvas* is filling the target box while the visible oval is smaller inside it. Resize the visible masked face itself to fill the target box.
- If the overlay should disappear, force overlay alpha to zero for the final/fade frames and compare the final target region against the original frame.
- Provide debug assets: source-grid-with-crop, target-grid-with-boxes, mask preview, preview sheet, final frame check.

## User interaction pattern

Keep iterations concrete and visual:

- “Here is the source image grid with the current crop box.”
- “Here is the original GIF target grid with current/larger boxes.”
- “Reply with A/B/C or exact coordinates.”
- When the user says “move 10px right,” immediately regenerate using the shifted box and deliver preview + MP4 + GIF.

Avoid over-explaining after each iteration; show the files and the exact changed coordinates.

## Pitfalls

- Don’t mistake a requested face swap for a generic image collage.
- Don’t center the replacement face by default; detect/estimate the original face/body region or ask the user via coordinate grid.
- Don’t let a face overlay persist after the original subject fades out.
- Don’t use a large transparent crop canvas that makes the visible face smaller than the intended target box.
- Don’t assume `.gif` input; Telegram commonly caches GIFs as short MP4s.

## Verification checklist

- Input duration/frame count/dimensions inspected.
- Contact sheet or target coordinate grid created.
- Source crop/mask and target placement recorded as explicit coordinates.
- Output MP4 and GIF exist and are non-empty.
- Last/fade frames checked when timing/fade matters.
- Response includes `MEDIA:/absolute/path` links for preview and final files.