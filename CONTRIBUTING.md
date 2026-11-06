# Contributing

1. Open an issue describing the use case or bug before large architectural changes.
2. Keep the core runtime dependency-free where practical; integrations belong behind adapters.
3. Add deterministic tests for parsers, planners, and serializers.
4. Never execute imported game binaries in unit tests or analyzers.
5. Bound file reads, traversal counts, decompression, subprocess time, and worker permissions.
6. Do not commit copyrighted game files, proprietary assets, credentials, or generated APKs.
7. Run before submitting:

   ```bash
   python -m unittest discover -s tests -v
   python -m compileall -q src tests
   ```

8. Document evidence, limitations, and platform assumptions. Do not convert heuristic scores into unsupported compatibility claims.

By contributing, you agree that your contributions are submitted under the repository's MIT license unless stated otherwise.
