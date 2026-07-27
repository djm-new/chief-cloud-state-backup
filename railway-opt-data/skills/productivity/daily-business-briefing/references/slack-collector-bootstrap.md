# Slack collector bootstrap fallback

Use when the Smart Business Briefing collection cron fails before it can gather Slack candidates because the base Python environment is missing `slack_sdk`.

## Pattern

The collector script can self-bootstrap by re-execing under `uv` with the required runtime packages:

```python
if shutil.which('uv'):
    os.execvp(
        'uv',
        [
            'uv', 'run', '--with', 'slack-sdk', '--with', 'aiohttp',
            'python', __file__, *sys.argv[1:],
        ],
    )
```

## Verification

- Run the collector directly and confirm it emits candidate items rather than a `ModuleNotFoundError`.
- Check the cron output file for the job ID before changing the briefing prompt or synthesis logic.
- If the collector succeeds but the final brief is wrong, debug the downstream context builder next.

## Pitfalls

- Don’t assume the final briefing job is broken just because the overall workflow failed.
- First identify the failing stage: collector, context builder, or synthesis.
- Keep the bootstrap wrapper narrowly scoped to dependency recovery; do not change briefing filtering rules as part of this fix.