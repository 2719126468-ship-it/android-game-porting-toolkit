# Android Game Porting Toolkit（AGPT）

**面向 PC → Android 游戏移植的 AI 辅助、证据驱动工作台。**

AGPT 是自动化编排与分析工具，不是万能模拟器，也不承诺所有 PC 游戏都能一键转换。当前版本能够建立独立移植项目、只读扫描游戏目录、识别常见文件架构与引擎线索、生成可解释的路线建议、检查本机工具链，并生成 Android Native 与兼容层工作模板。

> **v0.1.0 范围：** 项目管理、只读侦察、启发式路线规划、插件接口、工具链诊断、模板、测试与 CI。当前不会运行导入的游戏，不会绕过 DRM/反作弊/付费验证，也不会把“APK 编译成功”说成“游戏已可玩”。

## 当前功能

- 创建 `Port Project` 清单，不复制、不修改原游戏目录。
- 安全盘点文件（不跟随符号链接、不执行二进制文件），从 PE/ELF 头识别架构。
- 检测 Unity、Unreal、Godot、Ren'Py、RPG Maker、SDL、DirectX 等线索。
- 对 Native、Compatibility、Hybrid 三条路线给出可解释的启发式评分。
- 输出包含证据与不确定性的 JSON / Markdown 报告。
- 检查 Ghidra、Java、CMake、Ninja、Android SDK/NDK、ADB、Wine、Box64、Gradle 等可选工具。
- 生成最小 Android NDK/CMake 模板或兼容层运行配置。
- 通过 Python entry points 加载第三方分析插件。

## 环境要求

- Python 3.10 或更高版本。
- 运行时不依赖第三方 Python 包。
- 测试可选用 `pytest`；Android SDK/NDK、JDK、CMake、Wine/Box64、Ghidra 仅在对应工作流中需要。

## 安装与使用

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"

# 创建项目；source 指向你有权分析的游戏目录
agpt init ./projects/my-game --name "My Game" --source "/path/to/game"

# 生成分析报告
agpt analyze ./projects/my-game

# 检查本机工具
agpt doctor

# 生成 Android NDK/CMake 起始工程
agpt scaffold native ./work/my-game-android --package-id com.example.mygame

# 生成兼容层配置模板（不会启动游戏）
agpt scaffold compatibility ./work/my-game-compat --executable game.exe
```

分析报告位于项目的 `analysis/analysis.json` 和 `analysis/report.md`。原始游戏文件保持不变。

## 三条路线

| 路线 | 用途 | v0.1.0 能力 |
|---|---|---|
| Native | 复用或移植引擎/游戏代码至 ARM64/Android | 证据报告 + 最小 NDK/CMake 起始工程 |
| Compatibility | 通过兼容环境运行原版 Windows 程序 | 生成配置，不捆绑或启动 Wine/Box64 |
| Hybrid | 用原生模块替换部分功能，同时保留兼容运行环境 | 生成计划，标记需要人工确认的模块边界 |

路线分数是**启发式适配分数**，不是成功概率、性能基准或兼容性保证。报告会保留加减分依据和未知项。

## 安全与合规

仅分析你有权检查和修改的游戏与资产。默认只读盘点文件、读取头部和签名线索，不执行游戏文件。不绕过 DRM、许可证校验、反作弊、在线认证或其他访问控制；不下载或分发专有游戏数据。开始移植前应核实游戏、引擎、资产许可证及适用条款。不要把商业游戏二进制文件或资源提交到 Git。

详见 [安全政策](SECURITY.md)、[架构说明](docs/ARCHITECTURE.md)、[Agent 模型](docs/AGENTS.md)、[插件 API](docs/PLUGIN_API.md)、[发布说明](PUBLISH.md) 与 [路线图](ROADMAP.md)。
