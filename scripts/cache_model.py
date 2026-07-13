from __future__ import annotations

import argparse
import os


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pre-download a Hugging Face compatible model into a local cache."
    )
    parser.add_argument(
        "--model",
        default="protectai/deberta-v3-base-prompt-injection-v2",
        help="Model id or mirror-hosted model id.",
    )
    parser.add_argument(
        "--cache-dir",
        required=True,
        help="Target cache directory. Copy this directory into the intranet image or host.",
    )
    parser.add_argument(
        "--revision",
        default=None,
        help="Optional revision, branch, tag, or commit hash.",
    )
    parser.add_argument(
        "--endpoint",
        default=None,
        help="Optional Hugging Face mirror endpoint, for example https://hf-mirror.com.",
    )
    parser.add_argument(
        "--local-dir",
        default=None,
        help="Optional flat local model directory produced by snapshot_download.",
    )
    parser.add_argument(
        "--trust-remote-code",
        action="store_true",
        help="Allow custom model code. Keep disabled unless the model requires it.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.endpoint:
        os.environ["HF_ENDPOINT"] = args.endpoint

    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=args.model,
        revision=args.revision,
        cache_dir=args.cache_dir,
        local_dir=args.local_dir,
        local_dir_use_symlinks=False if args.local_dir else "auto",
    )

    # Validate that Transformers can load the cached files before packaging.
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    load_target = args.local_dir or args.model
    load_kwargs = {
        "cache_dir": args.cache_dir,
        "local_files_only": True,
        "trust_remote_code": args.trust_remote_code,
    }
    if args.revision:
        load_kwargs["revision"] = args.revision

    AutoTokenizer.from_pretrained(load_target, **load_kwargs)
    AutoModelForSequenceClassification.from_pretrained(load_target, **load_kwargs)

    print(f"Cached and verified model: {args.model}")
    print(f"cache_dir={args.cache_dir}")
    if args.local_dir:
        print(f"local_dir={args.local_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
