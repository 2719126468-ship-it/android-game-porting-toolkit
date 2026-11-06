# Android Game Porting Toolkit（AGPT）

面向 PC → Android 游戏移植的 AI 辅助、证据驱动工作台。

AGPT 不是万能模拟器，也不承诺所有 PC 游戏都能一键转换。它负责只读盘点游戏目录、分析可执行文件与资源包元数据、生成可追溯的移植路线建议，并为原生 Android 和兼容层工作流提供工程模板。

> v0.3.0 范围：受限只读侦察、PE/ELF 依赖提取、Unity/Unreal/Godot 元数据识别、ZIP 中央目录检查、路线规划、插件接口、可选 Ghidra Headless 适配器，以及可选 Android NDK/CMake 原生共享库构建适配器。AGPT 不执行导入的游戏、不绕过 DRM/反作弊、不解包受保护内容，也不会把“编译成功”说成“游戏已可玩”。

## 当前能力

- 创建独立 Port Project，不复制或修改原游戏目录。
- 安全盘点文件，跳过符号链接，分析阶段不执行导入的 EXE/DLL/SO。
- 从 PE 导入表提取 DLL 依赖，从 ELF PT_DYNAMIC / DT_NEEDED 提取动态库依赖。
- 识别 Unity、Unreal、Godot 的版本与资源包元数据。
- 仅读取 ZIP/APK/JAR 中央目录，不解压、不提取成员文件。
- 标记危险归档路径和可疑压缩比。
- 对 Native、Compatibility、Hybrid 三条路线提供可追溯的启发式评分。
- 可选调用用户自行安装的 Ghidra Headless，分析单个指定二进制并导出有上限的元数据。
- 可选使用用户自行安装的 Android NDK/CMake 构建原生共享库，保存日志、哈希和构建来源。
- 检查 Ghidra、Java、CMake、Android SDK/NDK、ADB、Wine、Box64 等工具。

## 安装

需要 Python 3.10+，运行时不依赖第三方 Python 包。

    python -m venv .venv
    . .venv/bin/activate
    python -m pip install -e ".[dev]"
    agpt --help

## 快速开始

    agpt init ./projects/my-game --name "My Game" --source "/path/to/game"
    agpt analyze ./projects/my-game
    agpt doctor --json
    agpt ghidra analyze ./game.exe --output ./reports/game.json
    agpt ndk build ./native-source --build-dir ./build/arm64 --abi arm64-v8a --api 26 --build-type Release

## 安全边界

Ghidra 和 Android SDK/NDK/CMake 都是用户自行安装的可选工具，AGPT 不会下载或自动更新它们。Ghidra 使用只读导入和一次性工程，只导出元数据，不反编译、不修改原始文件。NDK 适配器会执行 CMake 项目中的构建逻辑，因此只应构建可信的源代码，并尽量使用隔离工作节点。

生成 .so 不等于生成 APK，更不等于游戏已经能运行。APK 打包、安装和真机游戏验证是独立阶段。
