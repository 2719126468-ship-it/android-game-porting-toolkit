"""Extend the stable AGPT CLI with opt-in external-tool commands."""
from __future__ import annotations

import argparse
import json
import sys

from agpt.cli import main as base_main


def _ghidra(argv):
    from agpt.adapters.ghidra import AdapterError, analyze_binary

    parser = argparse.ArgumentParser(prog="agpt ghidra analyze")
    parser.add_argument("action", choices=["analyze"])
    parser.add_argument("binary")
    parser.add_argument("--output")
    parser.add_argument("--ghidra")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--analysis-timeout", type=int, default=1200)
    parser.add_argument("--max-functions", type=int, default=20000)
    args = parser.parse_args(argv)
    try:
        result = analyze_binary(
            args.binary, output=args.output, executable=args.ghidra,
            timeout=args.timeout,
            analysis_timeout_per_file=args.analysis_timeout,
            max_functions=args.max_functions,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    except (AdapterError, OSError, ValueError) as exc:
        print(f"agpt ghidra: error: {exc}", file=sys.stderr)
        return 2


def _ndk(argv):
    from agpt.adapters.ndk import NdkBuildError, build_native

    parser = argparse.ArgumentParser(prog="agpt ndk build")
    parser.add_argument("action", choices=["build"])
    parser.add_argument("source")
    parser.add_argument("--build-dir", required=True)
    parser.add_argument("--ndk")
    parser.add_argument("--sdk")
    parser.add_argument("--cmake")
    parser.add_argument("--abi", default="arm64-v8a")
    parser.add_argument("--api", type=int, default=26)
    parser.add_argument("--build-type", choices=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"], default="Debug")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--generator")
    args = parser.parse_args(argv)
    try:
        result = build_native(
            args.source, args.build_dir, ndk_dir=args.ndk, sdk_dir=args.sdk,
            cmake=args.cmake, abi=args.abi, android_api=args.api,
            build_type=args.build_type, timeout=args.timeout,
            jobs=args.jobs, generator=args.generator,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    except (NdkBuildError, OSError, ValueError) as exc:
        print(f"agpt ndk: error: {exc}", file=sys.stderr)
        return 2


def _ndk_make(argv):
    from agpt.adapters.ndkbuild import NdkMakeError, build_native

    parser = argparse.ArgumentParser(prog="agpt ndk-build build")
    parser.add_argument("action", choices=["build"])
    parser.add_argument("source")
    parser.add_argument("--build-dir", required=True)
    parser.add_argument("--ndk")
    parser.add_argument("--abi", default="arm64-v8a")
    parser.add_argument("--api", type=int, default=21)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args(argv)
    try:
        result = build_native(
            args.source, args.build_dir, ndk_dir=args.ndk,
            abi=args.abi, android_api=args.api, timeout=args.timeout, jobs=args.jobs,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (NdkMakeError, OSError, ValueError) as exc:
        print(f"agpt ndk-build: error: {exc}", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "ghidra":
        if len(args) < 2:
            print("usage: agpt ghidra analyze BINARY [options]", file=sys.stderr)
            return 2
        return _ghidra(args[1:])
    if args and args[0] == "ndk":
        if len(args) < 2:
            print("usage: agpt ndk build SOURCE --build-dir DIR [options]", file=sys.stderr)
            return 2
        return _ndk(args[1:])
    if args and args[0] == "ndk-build":
        if len(args) < 2:
            print("usage: agpt ndk-build build SOURCE --build-dir DIR [options]", file=sys.stderr)
            return 2
        return _ndk_make(args[1:])
    return base_main(args)
