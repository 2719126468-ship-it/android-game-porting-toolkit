# Android Game Porting Toolkit（AGPT）

面向 PC → Android 游戏移植的 AI 辅助、证据驱动工作台。

AGPT 不是万能模拟器，也不承诺所有 PC 游戏都能一键转换。它负责只读盘点游戏目录和源码，识别可执行文件、资源包与构建系统元数据，生成可追溯的移植路线建议，并为原生 Android 和兼容层工作流提供工程模板。

> v0.3.1 新增 C/C++ 源码与构建系统识别、SDL2 依赖探测、Android.mk/Application.mk 的 ABI/API 识别，以及可选 Android ndk-build 适配器。项目已通过真实 GitHub Actions ARM64 NDK 构建，样本为固定 commit 的 DungeonRush Android 参考工程。它仍然不执行导入的游戏、不绕过 DRM/反作弊、不解包受保护内容，也不会把“生成 .so”说成“游戏已可玩”。

## 可下载的 Android 示例 APK

CI 会构建一个原创、无外部游戏素材的 SDL2 示例游戏，最低支持 Android 8.1（API 27），同时打包 `armeabi-v7a` 32 位 ARM 和 `arm64-v8a` 64 位 ARM。每次成功 CI 都会上传可安装的 Debug APK 与验证报告（保留 90 天）；推送 `orbit-snake-v0.1.0` 这种标签时，会把通过检查的 APK 和许可证说明发布到 GitHub Releases。

该示例用于验证 SDL2 Android 集成和 APK 发布链路，并不代表 AGPT 已经能自动移植任意商业 PC 游戏。游戏逻辑为 AGPT 原创代码，SDL2 使用其 zlib 许可。

[查看 APK CI 工作流](https://github.com/2719126468-ship-it/android-game-porting-toolkit/actions/workflows/orbit-snake-apk.yml)。

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
- 通过 `agpt plan` 生成仅供审阅的移植任务图，包含依赖顺序、验收条件、建议能力和人工审批关卡。\n- 通过 `agpt patch propose` 生成带源文件哈希和统一 diff 的人工审核补丁提案，严格只读，不修改原游戏源码。
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
    agpt plan ./projects/my-game
    # 需要覆盖旧计划时显式加 --force
    agpt doctor --json

    # Ghidra 元数据分析（需要单独安装 Ghidra）
    agpt ghidra analyze ./game.exe --output ./reports/game.json

    # CMake 原生共享库构建（不是 APK）
    agpt ndk build ./native-source --build-dir ./build/arm64 --abi arm64-v8a --api 26

    # Android.mk 原生共享库构建（不是 APK）
    agpt ndk-build build ./jni --build-dir ./build/ndk-arm64 --abi arm64-v8a --api 21

`agpt plan` 会将任务图写入项目目录的 `plans/port-task-graph.json`；默认拒绝覆盖已有计划，只有显式添加 `--force` 才会替换，并且禁止把输出写进原游戏目录。它只生成计划，不执行任务、不修改游戏源码、不安装工具，也不会启动游戏；低置信度路线会要求人工选择。

## 安全边界

Ghidra 和 Android SDK/NDK/CMake 都是用户自行安装的可选工具，AGPT 不会下载或自动更新它们。Ghidra 使用只读导入和一次性工程，只导出元数据，不反编译、不修改原始文件。NDK 适配器会执行 CMake/Android.mk 项目中的构建逻辑，因此只应构建可信的源代码，并尽量使用隔离工作节点。

生成 .so 不等于生成 APK，更不等于游戏已经能运行。APK 打包、安装和真机游戏验证是独立阶段。
