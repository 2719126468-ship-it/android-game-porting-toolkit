# Publishing this prepared repository to GitHub

The source tree is ready for its first push. The connected GitHub action set in this session supports reading and writing files/commits to an existing repository, but does not expose the GitHub `Create repository` API. The repository therefore has not been created or pushed by AGPT automation.

Create an **empty** repository named `android-game-porting-toolkit` under `2719126468-ship-it` on GitHub (do not initialize it with a README, license, or `.gitignore`), then run from this directory:

```bash
git remote add origin git@github.com:2719126468-ship-it/android-game-porting-toolkit.git
git push -u origin main
```

HTTPS alternative:

```bash
git remote add origin https://github.com/2719126468-ship-it/android-game-porting-toolkit.git
git push -u origin main
```

Do not add commercial game files or assets to the repository. See `.gitignore` and `SECURITY.md`.
