# Global model / quality tuning notes

Use when DJ asks to make Hermes globally smarter, unpin context, expand memory, or make compression/session_search use the main model.

## Active config target

In the Railway Chief environment, verify before changing:

```bash
/opt/hermes/.venv/bin/hermes config path
```

Observed active path: `/opt/data/config.yaml`.

`hermes config set` currently has no `--global` flag. Setting values in the active config path is the global change for new sessions / next gateway model load.

## Known-good command bundle

```bash
/opt/hermes/.venv/bin/hermes config set model.contextlength ""
/opt/hermes/.venv/bin/hermes config set model.default gpt-5.5
/opt/hermes/.venv/bin/hermes config set memory.memory_char_limit 22000
/opt/hermes/.venv/bin/hermes config set memory.user_char_limit 8000
/opt/hermes/.venv/bin/hermes config set auxiliary.compression.model ""
/opt/hermes/.venv/bin/hermes config set auxiliary.session_search.model ""
/opt/hermes/.venv/bin/hermes config set auxiliary.compression.provider auto
/opt/hermes/.venv/bin/hermes config set auxiliary.session_search.provider auto
```

Why the provider lines matter: blanking `auxiliary.compression.model` and `auxiliary.session_search.model` is not enough if their providers are still pinned to `openrouter`; blank model + `provider: openrouter` can still route through OpenRouter defaults. `provider: auto` + blank model is the inheritance shape for main-model auxiliary behavior.

## Verification snippet

```bash
/opt/hermes/.venv/bin/python - <<'PY'
from pathlib import Path
import yaml, json
p=Path('/opt/data/config.yaml')
c=yaml.safe_load(p.read_text())
print(json.dumps({
  'config_path': str(p),
  'model.provider': c.get('model',{}).get('provider'),
  'model.default': c.get('model',{}).get('default'),
  'model.contextlength': c.get('model',{}).get('contextlength'),
  'memory.memory_char_limit': c.get('memory',{}).get('memory_char_limit'),
  'memory.user_char_limit': c.get('memory',{}).get('user_char_limit'),
  'auxiliary.compression.provider': c.get('auxiliary',{}).get('compression',{}).get('provider'),
  'auxiliary.compression.model': c.get('auxiliary',{}).get('compression',{}).get('model'),
  'auxiliary.session_search.provider': c.get('auxiliary',{}).get('session_search',{}).get('provider'),
  'auxiliary.session_search.model': c.get('auxiliary',{}).get('session_search',{}).get('model'),
}, indent=2))
PY
```

## `config show` section pitfall

`hermes config show compression` is not accepted by the current CLI. Use `hermes config show` for full config or read the requested section from YAML directly.
