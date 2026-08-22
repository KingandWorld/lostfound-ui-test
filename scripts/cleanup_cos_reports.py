#!/usr/bin/env python3
"""Clean up old COS report history (Day19).

Storage policy (see docs/UI自动化CI集成方案决策文档.md / README Day19 section):
    reports/latest/        latest report, overwritten every run (never cleaned)
    reports/build-<N>/     one copy per Jenkins build, keep newest --keep
    reports/archive/       monthly archive (optional, never cleaned by this script)

This script ONLY touches reports/build-* directories: lists them, keeps the
newest --keep ones, deletes the rest (all objects under each stale prefix).

Usage:
    python scripts/cleanup_cos_reports.py            # real delete, keep 10
    python scripts/cleanup_cos_reports.py --keep 5   # keep 5 builds
    python scripts/cleanup_cos_reports.py --dry-run  # only print what would be deleted

Config: same COS_* env vars as upload_to_cos.py (see .env.example).
Security: bucket name is masked in all output.
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

COS_SECRET_ID = os.getenv("COS_SECRET_ID", "")
COS_SECRET_KEY = os.getenv("COS_SECRET_KEY", "")
COS_REGION = os.getenv("COS_REGION", "ap-guangzhou")
COS_BUCKET = os.getenv("COS_BUCKET", "")

REPORTS_PREFIX = "reports/"
PAGE_SIZE = 1000


def mask_bucket(bucket: str) -> str:
    """桶名脱敏：只留前缀 3 字符，其余打码（桶名含账号 APPID，绝不原样输出）。"""
    return f"{bucket[:3]}***" if bucket else "<unset>"


def list_build_dirs(client) -> list:
    """列出 reports/ 下的 build-* 目录前缀（CommonPrefixes，分页拉全）。"""
    marker, dirs = "", []
    while True:
        resp = client.list_objects(Bucket=COS_BUCKET, Prefix=REPORTS_PREFIX,
                                   Delimiter="/", Marker=marker, MaxKeys=PAGE_SIZE)
        dirs.extend(prefix["Prefix"] for prefix in resp.get("CommonPrefixes", []))
        # Day19 实测坑: IsTruncated 是字符串 "true"/"false"("false" 为真值);
        # marker 取到 None 会让签名串与请求不一致 -> SignatureDoesNotMatch(403)
        if resp.get("IsTruncated") == "true":
            marker = resp.get("NextMarker") or resp.get("Marker") or ""
        else:
            break
    return sorted(d for d in dirs if d.rstrip("/").rsplit("/", 1)[-1].startswith("build-"))


def list_object_keys(client, prefix: str) -> list:
    """列出某前缀下全部对象 key（分页拉全）。"""
    marker, keys = "", []
    while True:
        resp = client.list_objects(Bucket=COS_BUCKET, Prefix=prefix,
                                   Marker=marker, MaxKeys=PAGE_SIZE)
        keys.extend(item["Key"] for item in resp.get("Contents", []))
        if resp.get("IsTruncated") == "true":
            marker = resp.get("NextMarker") or resp.get("Marker") or ""
        else:
            break
    return keys


def delete_prefix(client, prefix: str) -> int:
    """删除某前缀下全部对象（每次 1000 个批量删除，返回删除数）。"""
    keys = list_object_keys(client, prefix)
    for i in range(0, len(keys), PAGE_SIZE):
        batch = [{"Key": k} for k in keys[i:i + PAGE_SIZE]]
        client.delete_objects(Bucket=COS_BUCKET, Delete={"Object": batch})
    return len(keys)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean old reports/build-* dirs in COS")
    parser.add_argument("--keep", type=int, default=10, help="newest build dirs to keep, default 10")
    parser.add_argument("--dry-run", action="store_true", help="print only, delete nothing")
    args = parser.parse_args()

    missing = [k for k, v in (("COS_SECRET_ID", COS_SECRET_ID),
                              ("COS_SECRET_KEY", COS_SECRET_KEY),
                              ("COS_BUCKET", COS_BUCKET)) if not v]
    if missing:
        print(f"[FAIL] missing env: {', '.join(missing)} (see .env.example COS_* section)")
        return 1

    from qcloud_cos import CosConfig, CosS3Client  # 延迟导入：配置缺失时也能给出友好提示

    client = CosS3Client(CosConfig(Region=COS_REGION, SecretId=COS_SECRET_ID,
                                   SecretKey=COS_SECRET_KEY))

    build_dirs = list_build_dirs(client)
    print(f"[scan] cos://{mask_bucket(COS_BUCKET)}/reports/ build-* dirs: {len(build_dirs)}")
    if not build_dirs:
        print("[skip] nothing to clean")
        return 0

    stale = build_dirs[:-args.keep] if args.keep > 0 else build_dirs
    mode = "DRY-RUN" if args.dry_run else "DELETE"
    if not stale:
        print(f"[skip] {len(build_dirs)} dirs <= keep {args.keep}: nothing to clean")
        return 0

    print(f"[{mode}] keeping {len(build_dirs) - len(stale)} newest, cleaning {len(stale)} oldest:")
    for d in stale:
        keys = list_object_keys(client, d)  # dry-run 同样列出对象，只打印不删除
        print(f"    {d} ({len(keys)} objects)")
        if not args.dry_run and keys:
            deleted = delete_prefix(client, d)
            print(f"    -> deleted {deleted} objects")
    return 0


if __name__ == "__main__":
    sys.exit(main())
