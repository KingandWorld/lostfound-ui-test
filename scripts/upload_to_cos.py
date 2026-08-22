#!/usr/bin/env python3
"""Allure report upload to Tencent Cloud COS (Day19).

Upload a local Allure report directory to COS (default prefix reports/latest),
write version.json to record the upload, optionally upload an index page to
the bucket root, and print a masked access hint.

Usage:
    python scripts/upload_to_cos.py <report_dir> [COS目标路径]
    python scripts/upload_to_cos.py allure-report reports/latest
    python scripts/upload_to_cos.py allure-report reports/build-123
    python scripts/upload_to_cos.py --index docs/report_index.html   # 索引页传桶根

Options:
    --verify       上传后列出 COS 前缀下的对象并核对数量（对账）
    --index FILE   把索引页模板作为桶根 index.html 上传（模板内域名占位符
                   需先替换为真实域名，见 docs/report_index.html 头部说明）
    --no-version   不生成 version.json（历史目录 build-* 可省）

Config (.env or environment variables):
    COS_SECRET_ID    腾讯云 SecretId（Day14 已配置于接口项目 .env，可复用）
    COS_SECRET_KEY   腾讯云 SecretKey（与密码同等对待，绝不入库/回显）
    COS_BUCKET       桶名（含账号 APPID 后缀；日志一律脱敏输出）
    COS_REGION       桶所属地域，默认 ap-guangzhou
    COS_CDN_DOMAIN   [可选] 报告外链域名，如 https://reports.example.com；
                     配置后 version.json 才写 report_url，否则只写 cos:// 路径

Security rules (project red line):
    - 凭据只从 .env / 环境变量读取，不硬编码、不入库、不打印；
    - 桶名含账号 APPID 后缀，所有日志经 mask_bucket() 脱敏后再输出；
    - 本文件不含任何真实桶名/域名/密钥（全部走环境变量）。
"""

import argparse
import datetime
import json
import mimetypes
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
COS_CDN_DOMAIN = os.getenv("COS_CDN_DOMAIN", "").rstrip("/")

REQUIRED = ("COS_SECRET_ID", "COS_SECRET_KEY", "COS_BUCKET")
PAGE_SIZE = 1000


def mask_bucket(bucket: str) -> str:
    """桶名脱敏：只留前缀 3 字符，其余打码（桶名含账号 APPID，绝不原样输出）。"""
    return f"{bucket[:3]}***" if bucket else "<unset>"


def require_config() -> bool:
    missing = [k for k in REQUIRED if not os.getenv(k)]
    if missing:
        print(f"[FAIL] missing env: {', '.join(missing)} (see .env.example COS_* section)")
        return False
    return True


def upload_directory(client, local_dir: Path, cos_prefix: str) -> tuple:
    """递归上传目录到 COS 指定前缀，返回 (uploaded_keys, failed_local_paths)。"""
    uploaded, failed = [], []
    files = sorted(p for p in local_dir.rglob("*") if p.is_file())
    for idx, file_path in enumerate(files, 1):
        rel = file_path.relative_to(local_dir).as_posix()
        cos_key = f"{cos_prefix}/{rel}"
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        try:
            with file_path.open("rb") as body:
                client.put_object(
                    Bucket=COS_BUCKET,
                    Key=cos_key,
                    Body=body,
                    ContentType=content_type,
                    CacheControl="no-cache",
                )
            uploaded.append(cos_key)
        except Exception as exc:
            print(f"[FAIL] {rel}: {exc}", file=sys.stderr)
            failed.append(str(file_path))
    return uploaded, failed


def write_version_json(client, cos_prefix: str, uploaded: list, failed: list) -> None:
    """生成并上传 version.json（记录上传时间/数量；配置了 CDN 域名才写 report_url）。"""
    version = {
        "upload_time": datetime.datetime.now().isoformat(timespec="seconds"),
        "cos_path": cos_prefix,
        "total_files": len(uploaded) + len(failed),
        "uploaded": len(uploaded),
        "failed": len(failed),
    }
    if COS_CDN_DOMAIN:
        version["report_url"] = f"{COS_CDN_DOMAIN}/{cos_prefix}/index.html"
    client.put_object(
        Bucket=COS_BUCKET,
        Key=f"{cos_prefix}/version.json",
        Body=json.dumps(version, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )


def verify_prefix(client, cos_prefix: str, expected: int) -> int:
    """列出 COS 前缀下全部对象并计数（分页拉全），返回对象数。"""
    marker, count = "", 0
    while True:
        resp = client.list_objects(
            Bucket=COS_BUCKET, Prefix=f"{cos_prefix}/", Marker=marker, MaxKeys=PAGE_SIZE
        )
        count += len(resp.get("Contents", []))
        # Day19 实测坑: SDK 的 IsTruncated 是字符串 "true"/"false"(xml 原样解析,不转 bool),
        # "false" 为真值会让本循环多翻一页; 且翻页 marker 取到 None 时, 签名串含
        # marker=None 而 requests 丢弃 None 参数 -> SignatureDoesNotMatch(403)。
        # 修复: 显式比较 "true" + marker 兜底 ""。
        if resp.get("IsTruncated") == "true":
            marker = resp.get("NextMarker") or resp.get("Marker") or ""
        else:
            break
    status = "OK" if count == expected else "MISMATCH"
    print(f"[verify] COS objects under {cos_prefix}/ = {count}, expected {expected} -> {status}")
    return count


def upload_index_page(client, index_file: Path) -> None:
    """把索引页模板上传为桶根 index.html（模板内真实域名需先替换占位符）。"""
    if not index_file.is_file():
        print(f"[FAIL] index file not found: {index_file}", file=sys.stderr)
        sys.exit(1)
    with index_file.open("rb") as body:
        client.put_object(
            Bucket=COS_BUCKET, Key="index.html", Body=body,
            ContentType="text/html; charset=utf-8", CacheControl="no-cache",
        )
    print(f"[index] uploaded to cos://{mask_bucket(COS_BUCKET)}/index.html")


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload Allure report to Tencent Cloud COS")
    parser.add_argument("report_dir", nargs="?", help="local allure-report directory")
    parser.add_argument("cos_path", nargs="?", default="reports/latest",
                        help="COS target prefix, default reports/latest")
    parser.add_argument("--index", metavar="FILE", help="upload index page to bucket root")
    parser.add_argument("--verify", action="store_true", help="verify object count after upload")
    parser.add_argument("--no-version", action="store_true", help="skip version.json")
    args = parser.parse_args()

    if not require_config():
        return 1
    if not args.index and not args.report_dir:
        parser.error("report_dir is required unless --index is used")

    from qcloud_cos import CosConfig, CosS3Client  # 延迟导入：配置缺失时也能给出友好提示

    client = CosS3Client(CosConfig(Region=COS_REGION, SecretId=COS_SECRET_ID,
                                   SecretKey=COS_SECRET_KEY))

    if args.index:
        upload_index_page(client, Path(args.index))

    if not args.report_dir:
        return 0

    local_dir = Path(args.report_dir)
    if not local_dir.is_dir():
        print(f"[FAIL] report dir not found: {local_dir}", file=sys.stderr)
        return 1

    start = datetime.datetime.now()
    print(f"[upload] {local_dir} -> cos://{mask_bucket(COS_BUCKET)}/{args.cos_path}/ "
          f"(region {COS_REGION})")
    uploaded, failed = upload_directory(client, local_dir, args.cos_path)

    if uploaded and not args.no_version:
        write_version_json(client, args.cos_path, uploaded, failed)

    if args.verify and uploaded:
        # version.json 也落桶，预期数 = 上传文件数 + (写版本文件 ? 1 : 0)
        expected = len(uploaded) + (0 if args.no_version else 1)
        verify_prefix(client, args.cos_path, expected)

    elapsed = (datetime.datetime.now() - start).total_seconds()
    print(f"[done] {len(uploaded)} files uploaded, {len(failed)} failed in {elapsed:.1f}s")
    if COS_CDN_DOMAIN:
        print(f"[url] {COS_CDN_DOMAIN}/{args.cos_path}/index.html")
    else:
        print("[url] COS_CDN_DOMAIN not set: use COS console/custom domain for external access")
    if failed:
        print(f"[FAIL] failed files: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
