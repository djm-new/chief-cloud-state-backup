# ffmpeg overlay notes for product mockups

Session-proven workflow for placing a logo/wordmark onto a product photo quickly.

## Case: opaque logo card on a beige background

If the logo asset is a flat image with a nearly uniform light background:

1. Try a light colorkey to remove the background:
   ```bash
   ffmpeg -y -i logo.jpg \
     -vf "colorkey=0xf1eadb:0.45:0.0,format=rgba,scale=220:-1" \
     -frames:v 1 logo_rgba.png
   ```

2. Overlay it onto the base photo:
   ```bash
   ffmpeg -y -i base.jpg -i logo_rgba.png \
     -filter_complex "[0:v][1:v]overlay=(W-w)/2:235:format=auto" \
     -frames:v 1 out.jpg
   ```

## Useful heuristics

- Scale the logo relative to the printable area, not the full frame.
- Center the logo on the visible front face unless the object perspective suggests otherwise.
- If the keyed result leaves a halo or box, try a different key color/threshold or use a cleaner source asset.
- For simple wordmarks, `drawtext` can be enough if no source logo is supplied.

## Verification

After exporting, inspect the mockup visually for:

- readable text
- no leftover matte/rectangle
- believable size and placement
- no obvious clipping at edges
