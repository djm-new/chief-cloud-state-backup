---
name: visual-compositing
description: "Use when compositing assets onto still images or short clips: product mockups, logo placement, overlays, face swaps, coordinate grids, and Telegram-ready exports. Preserve realism and verify visually."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [creative, image-editing, video-editing, compositing, mockup, overlay]
    related_skills: [comfyui, sketch, claude-design]
---

# Visual Compositing

## Overview

Use this skill when the user wants one visual asset placed, blended, or swapped into another visual asset while preserving realism. That includes product mockups, logo placement, labels, stickers, short GIF edits, reaction clip overlays, face swaps, and other small-scene compositing tasks.

The core idea is the same across stills and motion: identify the real target surface or region, place the source asset cleanly, and verify that the result still looks natural in the final frame(s).

## When to Use

- Putting a logo, wordmark, label, or badge onto a product photo
- Overlaying an asset onto a still image without obvious matte boxes
- Editing a short GIF or MP4 clip with a replacement face or graphic
- Matching scale, perspective, opacity, or fade timing on a composite
- Creating a coordinate grid or frame sheet to help the user refine placement
- Exporting a clean final image or Telegram-ready MP4/GIF

Do **not** use this for:
- Full brand redesigns or multi-slide layouts
- Pure generative image creation with no source asset
- Long-form video editing or timeline-heavy post-production

## Two common modes

### 1) Still-image mockups

Use this mode for product photos, packaging shots, signage, shirts, mugs, boxes, and similar surfaces.

Guidelines:
- Inspect the source logo/graphic before placing it.
- Scale against the printable or visible surface, not the entire canvas.
- Match the object’s perspective and keep the composite believable.
- Prefer subtle blending over a hard rectangle or sticker panel.
- If the logo asset has a uniform background, remove it cleanly before overlaying.

Support note:
- `references/ffmpeg-overlay-notes.md` — a proven ffmpeg workflow for extracting a keyed logo and overlaying it onto a product photo.

### 2) Short-clips and GIF overlays

Use this mode for short reaction clips, meme edits, face swaps, and other frame-based motion composites.

Guidelines:
- Inspect the clip duration, FPS, and frame dimensions first.
- Create a contact sheet or coordinate grid early so placement can be refined visually.
- Separate source crop/mask from target placement.
- Match opacity and fade timing to the underlying clip.
- Check the final frames carefully so the overlay does not linger when it should disappear.
- Export MP4 by default; provide GIF only when requested or clearly useful.

## Recommended workflow

1. **Inspect inputs first.**
   - Check image/video dimensions.
   - Determine whether the source asset has transparency.
   - Identify the true target area on the background.

2. **Choose the cleanest composite path.**
   - Transparent source: overlay directly.
   - Opaque source on a flat background: key or remove the background first.
   - Complex source: prefer a cleaner asset over forcing a bad cleanup.

3. **Fit the source to the target.**
   - Scale to the visible surface.
   - Preserve perspective and placement.
   - Keep the result readable without looking pasted on.

4. **Verify visually.**
   - Check readability.
   - Check alignment and proportion.
   - Check for leftover matte, halo, or clipping.
   - For motion, check the first and last visible frames.

## Common pitfalls

1. **Sizing against the whole canvas instead of the actual target surface.**
   The composite should be driven by the printable area or visible face.

2. **Leaving a visible box or halo around the asset.**
   If cleanup is messy, change the keying threshold or use a cleaner source.

3. **Forgetting the motion tail.**
   In short clips, a face or overlay can look fine mid-clip but linger in the last frames.

4. **Using a source crop that is too small inside a larger transparent canvas.**
   Make the visible asset itself fill the target region.

5. **Skipping the visual check.**
   A technically successful overlay can still look awkward if proportion or placement is off.

## Verification checklist

- [ ] Source asset inspected before compositing
- [ ] Target surface/region identified
- [ ] Scale and placement recorded explicitly
- [ ] Final output is readable and believable
- [ ] No unwanted matte, halo, or clipping remains
- [ ] Motion composites were checked in the final frames
- [ ] Final export matches the requested format