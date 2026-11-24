#!/usr/bin/env python3
"""AnonMeta - Automated File Type Detection & Metadata Anonymizer."""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import magic
except ImportError:
    print("[!] python3-magic is missing. Install it: sudo apt install python3-magic -y")
    sys.exit(1)

# الألوان لتوضيح المخرجات في التيرمينال (تتعطل لو الخرج مش terminal)
if sys.stdout.isatty():
    GREEN, YELLOW, RED, CYAN, RESET = (
        "\033[92m", "\033[93m", "\033[91m", "\033[96m", "\033[0m"
    )
else:
    GREEN = YELLOW = RED = CYAN = RESET = ""

# أنواع الـ MIME المدعومة للتنظيف العميق
SUPPORTED_MIMES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/tiff",
    "image/svg+xml",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",      # docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",            # xlsx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",    # pptx
    "application/vnd.oasis.opendocument.text",                                      # odt
    "application/vnd.oasis.opendocument.spreadsheet",                               # ods
    "application/vnd.oasis.opendocument.presentation",                              # odp
    "application/epub+zip",
    "application/zip",
    "audio/mpeg",
    "audio/flac",
    "audio/ogg",
    "video/mp4",
}

# إحصائيات التشغيل
stats = {"cleaned": 0, "skipped": 0, "failed": 0}


def check_dependencies(spoof):
    """التأكد من وجود الأدوات المطلوبة قبل ما نلمس أي ملف"""
    required = ["mat2"]
    if spoof:
        required.append("exiftool")
    missing = [tool for tool in required if shutil.which(tool) is None]
    if missing:
        print(f"{RED}[!] Missing required tools: {', '.join(missing)}{RESET}")
        print("    sudo apt update && sudo apt install mat2 libimage-exiftool-perl -y")
        sys.exit(1)


def detect_file_type(file_path):
    """التعرف على نوع الملف الحقيقي من خلال التوقيع الداخلي (Magic Bytes)"""
    try:
        return magic.Magic(mime=True).from_file(str(file_path))
    except Exception as e:
        return f"unknown ({e})"


def rewrite_pdf(path):
    """
    exiftool بيعدل الـ PDF عن طريق incremental update، يعني النسخة القديمة
    (بالميتاداتا الأصلية) بتفضل جوه الملف ويمكن استرجاعها.
    qpdf بيعيد كتابة الملف ويرمي أي objects قديمة، فبنستخدمه بعد exiftool.
    """
    tmp = path.with_name(path.name + ".anonmeta.tmp")
    try:
        result = subprocess.run(
            ["qpdf", "--linearize", str(path), str(tmp)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        # qpdf بيرجع 3 لو فيه warnings بس الملف الناتج سليم
        if result.returncode in (0, 3) and tmp.exists():
            os.replace(tmp, path)
            return True
        return False
    finally:
        if tmp.exists():
            tmp.unlink()


def spoof_generic_metadata(path, mime_type):
    """
    إضافة بيانات محايدة (Anonymous) بعد المسح العميق لإخفاء أثر التنظيف.
    بترجع (نجح؟، رسالة).
    """
    cmd = ["exiftool", "-overwrite_original"]

    if mime_type == "application/pdf":
        if shutil.which("qpdf") is None:
            return False, "qpdf not installed; PDF spoofing skipped (it would leave the original metadata recoverable)"
        cmd.extend([
            "-Author=anonymous",
            "-Creator=anonymous",
            "-Producer=PDF Generator",
            "-Title=Document",
        ])
    elif mime_type.startswith("image/"):
        cmd.extend([
            "-Comment=Processed",
            "-Software=Image Editor",
        ])
    else:
        return False, "spoofing is only supported for PDF and images; file was wiped only"

    cmd.append(str(path))
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return False, f"exiftool failed: {result.stderr.strip()}"

    if mime_type == "application/pdf" and not rewrite_pdf(path):
        return False, "qpdf rewrite failed; old PDF revision may still contain metadata"

    return True, ""


def is_hidden(path, root):
    """تجاهل الملفات المخفية وأي ملف جوه فولدر مخفي (زي .git)"""
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = (path.name,)
    return any(part.startswith(".") for part in parts)


def anonymize_file(path, spoof=False, dry_run=False):
    # الـ symlinks بنتجاهلها عشان mat2 --inplace ميعدلش ملفات برا الفولدر
    if path.is_symlink() or not path.is_file():
        return

    mime_type = detect_file_type(path)
    print(f"{CYAN}[*] File:{RESET} {path.name} | {YELLOW}Detected Type:{RESET} {mime_type}")

    if mime_type not in SUPPORTED_MIMES:
        print(f"    {YELLOW}[!] Unsupported or plain-text file type, skipped safely.{RESET}")
        stats["skipped"] += 1
        return

    if dry_run:
        print(f"    {YELLOW}[~] Dry run: would clean{' + spoof' if spoof else ''}.{RESET}")
        stats["skipped"] += 1
        return

    try:
        # 1. مسح عميق وإعادة بناء الملف via mat2 (بيعدل الأصل مباشرة بدون نسخة احتياطية)
        result = subprocess.run(
            ["mat2", "--inplace", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            print(f"    {RED}[-] mat2 skipped or failed: {result.stderr.strip()}{RESET}")
            stats["failed"] += 1
            return

        # 2. إضافة بيانات محايدة لو المستخدم طلب وضع التمويه (Spoof)
        if spoof:
            ok, msg = spoof_generic_metadata(path, mime_type)
            if ok:
                print(f"    {GREEN}[+] Metadata stripped & spoofed with anonymous tags.{RESET}")
            else:
                print(f"    {GREEN}[+] Metadata stripped via mat2.{RESET}")
                print(f"    {YELLOW}[!] Spoof not applied: {msg}{RESET}")
        else:
            print(f"    {GREEN}[+] Metadata stripped via mat2.{RESET}")
        stats["cleaned"] += 1

    except Exception as e:
        print(f"    {RED}[!] Error processing {path.name}: {e}{RESET}")
        stats["failed"] += 1


def process_target(target_path, recursive=False, spoof=False, dry_run=False):
    target = Path(target_path)

    if not target.exists():
        print(f"{RED}[!] Error: '{target}' does not exist.{RESET}")
        sys.exit(1)

    if target.is_file():
        if target.name.startswith("."):
            print(f"{YELLOW}[!] Hidden file, skipped.{RESET}")
            return
        anonymize_file(target, spoof=spoof, dry_run=dry_run)
    elif target.is_dir():
        print(f"{CYAN}[*] Scanning directory:{RESET} {target} (Recursive={recursive})\n")
        # sorted عشان الترتيب يبقى ثابت، وبنجمع القايمة الأول عشان التعديل أثناء المسح ميبوظش الـ iteration
        files = sorted(target.rglob("*") if recursive else target.glob("*"))
        for item in files:
            if item.is_file() and not is_hidden(item, target):
                anonymize_file(item, spoof=spoof, dry_run=dry_run)


def main():
    parser = argparse.ArgumentParser(
        description="Automated File Type Detection & Metadata Anonymizer"
    )
    parser.add_argument("target", help="Target file or directory path")
    parser.add_argument("-r", "--recursive", action="store_true", help="Scan subdirectories recursively")
    parser.add_argument("-s", "--spoof", action="store_true", help="Replace wiped metadata with generic anonymous tags")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Show what would be processed without modifying any file")
    args = parser.parse_args()

    if not args.dry_run:
        check_dependencies(args.spoof)

    process_target(args.target, recursive=args.recursive, spoof=args.spoof, dry_run=args.dry_run)

    print(f"\n{CYAN}[*] Done:{RESET} {stats['cleaned']} cleaned, "
          f"{stats['skipped']} skipped, {stats['failed']} failed")
    sys.exit(1 if stats["failed"] else 0)


if __name__ == "__main__":
    main()
