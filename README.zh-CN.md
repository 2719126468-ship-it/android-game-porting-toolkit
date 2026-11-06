# Android Game Porting Toolkit（AGPT）

**面向 PC → Android 游戏移植的 AI 辅助、证据驱动工作台。**

AGPT 不是万能模拟器，也不承诺所有 PC 游戏都能一键转换。它负责只读盘点游戏目录、分析可执行文件和资源包的元数据、生成可追溯的移植路线建议，并为原生 Android 和兼容层工作流提供工程模板。

> **v0.2.0 范围：** 项目管理、受限只读扫描、PE/ELF 依赖提取、Unity/Unreal/Godot 元数据识别、ZIP 中央目录检查、路线规划、插件接口、工程模板、测试与 CI。当前不会执行导入的游戏，不会绕过 DRM/反作弊，也不会把 APK 编译成功说成游戏已经可玩。

## 当前能力

- 创建独立 Port Project 清单，不复制或修改原游戏目录。
- 跳过符号链接，不执行导入的 EXE/DLL/SO。
- 从 PE 导入表提取直接 DLL 依赖。
- 从 ELF PT_DYNAMIC / DT_NEEDED 提取动态库依赖。
- 识别 Unity ProjectVersion.txt、UnityFS 资源包和 IL2CPP 元数据线索。
- 识别 Unreal Build.version、PAK 尾部版本标记和 IoStore 文件布局。
- 识别 Godot PCK 引擎版本与包格式版本。
- 仅读取 ZIP/APK/JAR 的中央目录，不解压、不提取成员文件。
- 标记 ZIP 中的绝对路径、父目录穿越路径和异常压缩比。
- 生成包含证据和未知项的 JSON / Markdown 分析报告。
- 检查 Ghidra、Java、CMake、Android SDK/NDK、ADB、Wine、Box64 等可选工具。
- 生成 Android NDK/CMake 起始工程或兼容层配置模板。

## 安装与使用

要求 Python 3.10+，运行时不依赖第三方 Python 包。

    python -m venv .venv
    . .venv/bin/activate
    python -m pip install -e ".[dev]"

    agpt init ./projects/my-game --name "My Game" --source "/path/to/game"
    agpt analyze ./projects/my-game
    agpt doctor

生成模板：

    agpt scaffold native ./work/my-game-android --package-id com.example.mygame
    agpt scaffold compatibility ./work/my-game-compat --executable game.exe

分析结果位于项目的 analysis/analysis.json 和 analysis/report.md。原始游戏文件保持不变。

## 分析边界

- PE/ELF 解析有单文件字节预算、节区/程序头和依赖数量上限。
- ZIP 检查只读取 EOCD 和中央目录，不解压；本版本识别 ZIP64，但暂不解析其中央目录。
- 格式损坏、输入超限或证据不明确时输出警告，不猜测为成功。
- 版本识别依赖游戏是否保留对应元数据，不保证每个游戏都能识别版本。
- 路线分数是启发式适配指标，不是成功概率或兼容性保证。

只分析你有权检查和修改的游戏及资产。AGPT 不绕过 DRM、许可证验证、反作弊或在线认证。不要向 Git 提交商业游戏文件、专有资源或存档。

详见 SECURITY.md、docs/ARCHITECTURE.md、docs/AGENTS.md、docs/PLUGIN_API.md、docs/SAFETY_AND_LIMITS.md 与 ROADMAP.md。
