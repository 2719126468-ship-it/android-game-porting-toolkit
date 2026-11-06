# Android Game Porting Toolkit（AGPT）

面向 PC → Android 游戏移植的 AI 辅助、证据驱动工作台。

AGPT 不是万能模拟器，也不承诺所有 PC 游戏都能一键转换。它负责只读盘点游戏目录和源码，识别可执行文件、资源包与构建系统元数据，生成可追溯的移植路线建议，并为原生 Android 和兼容层工作流提供工程模板。

> v0.3.1 新增 C/C++ 源码与构建系统识别、SDL2 依赖探测、Android.mk/Application.mk 的 ABI/API 识别，以及可选 Android ndk-build 适配器。项目已通过真实 GitHub Actions ARM64 NDK 构建，样本为固定 commit 的 DungeonRush Android 参考工程。它仍然不执行导入的游戏、不绕过 DRM/反作弊、不解包受保护内容，也不会把“生成 .so”说成“游戏已可玩”。

## 已验证的 Android 打包参考

固定版本的上游 DungeonRush Android 参考工程已经通过可复现的旧版工具链完成 APK 构建，并通过 Manifest 与 ABI 检查：包名为 `org.libsdl.app`，最低 Android API 16，同时包含 `arm64-v8a` 和 `armeabi-v7a`，共 16 个原生共享库；APK 约 14.47 MiB。

**这只是使用上游已有 Android 移植工程进行的构建/打包验证，不是 AGPT 自动生成的移植 APK。** 尚未进行模拟器或真机安装、启动和实际游戏测试。由于 APK 包含的部分第三方素材授权状态不明确，本项目没有公开发布该 APK。详见[完整验证记录](docs/testing/dungeonrush-android-reference.md)和 [GitHub Actions 构建记录](https://github.com/2719126468-ship-it/android-game-porting-toolkit/actions/runs/42228472437)。

## 当前能力

- 创建独立 Port Project，不复制或修改原游戏目录。
- 安全盘点文件，跳过符号链接，分析阶段不执行导入的 EXE/DLL/SO。
- 从 PE 导入表提取 DLL 依赖，从 ELF PT_DYNAMIC / DT_NEEDED 提取动态库依赖。
- 识别 Unity、Unreal、Godot 的版本与资源包元数据。
- 仅读取 ZIP/APK/JAR 中央目录，不解压、不提取成员文件。
- 有上限地扫描 C/C++ 源码和头文件，识别 CMake、Android.mk、Application.mk、Gradle 与 Makefile。
- 从构建声明和 include 中识别 SDL2、SDL2_image、SDL2_mixer、SDL2_net、SDL2_ttf。
- 对 Native、Compatibility、Hybrid 三条路线提供可追溯的启发式评分。
- 可选调用用户自行安装的 Ghidra Headless，分析单个指定二进制并导出有上限的元数据。
- 可选通过 Android NDK 构建 CMake 或 Android.mk 原生共享库，保存日志、ABI/API、哈希和构建来源。
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

    # Ghidra 元数据分析（需要单独安装 Ghidra）
    agpt ghidra analyze ./game.exe --output ./reports/game.json

    # CMake 原生共享库构建（不是 APK）
    agpt ndk build ./native-source --build-dir ./build/arm64 --abi arm64-v8a --api 26

    # Android.mk 原生共享库构建（不是 APK）
    agpt ndk-build build ./jni --build-dir ./build/ndk-arm64 --abi arm64-v8a --api 21

## 安全边界

Ghidra 和 Android SDK/NDK/CMake 都是用户自行安装的可选工具，AGPT 不会下载或自动更新它们。Ghidra 使用只读导入和一次性工程，只导出元数据，不反编译、不修改原始文件。NDK 适配器会执行 CMake/Android.mk 项目中的构建逻辑，因此只应构建可信的源代码，并尽量使用隔离工作节点。

生成 .so 不等于生成 APK，更不等于游戏已经能运行。APK 打包、安装和真机游戏验证是独立阶段。
