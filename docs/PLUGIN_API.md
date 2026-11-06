# Plugin API (v0.1)

AGPT discovers Python entry points in the `agpt.analyzers` group. A distribution can register an analyzer in `pyproject.toml`:

```toml
[project.entry-points."agpt.analyzers"]
my_engine = "my_agpt_plugin:MyEngineAnalyzer"
```

The target must be a no-argument class or factory. Its instance must provide:

```python
class MyEngineAnalyzer:
    name = "my-engine"

    def analyze(self, inventory):
        # Read inventory.records and inventory.evidence only.
        return {
            "engine": "my-engine",
            "confidence": 0.75,
            "evidence": ["marker-file: MY_ENGINE.DAT"],
        }
```

The inventory is a read-only-by-convention data object. Plugin loading is opt-in through `agpt analyze --plugins`; v0.1.0 does not install plugins or sandbox arbitrary Python plugin code. Only install plugins you trust. Plugin results are treated as untrusted hints, validated as JSON-serializable values, and isolated from built-in scan results.

Future versions will version the plugin API and may add worker isolation and capability declarations.
