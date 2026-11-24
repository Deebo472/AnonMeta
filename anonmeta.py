#!/usr/bin/env python3
import os
import sys
import magic
import subprocess
import argparse
from pathlib import Path

# الألوان لتوضيح المخرجات في التيرمينال
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"

# أنواع الـ MIME المدعومة للتنظيف العميق
SUPPORTED_MIMES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/tiff",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",      # docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",            # xlsx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",    # pptx
    "application/zip",
    "audio/mpeg",
    "video/mp4",
}

def detect_file_type(file_path):
    """التعرف على نوع الملف الحقيقي من خلال التوقيع الداخلي (Magic Bytes)"""
    try:
        mime = magic.Magic(mime=True)
        return mime.from_file(str(file_path))
    except Exception as e:
        return f"unknown ({e})"

def spoof_generic_metadata(file_path, mime_type):
    """إضافة بيانات محايدة (Anonymous) بعد المسح العميق لإخفاء أثر التنظيف"""
    cmd = ["exiftool", "-overwrite_original"]
    
    if mime_type == "application/pdf":
        cmd.extend([
            "-Author=anonymous",
            "-Creator=anonymous",
            "-Producer=PDF Generator",
            "-Title=Document"
        ])
    elif mime_type.startswith("image/"):
        cmd.extend([
            "-Comment=Processed",
            "-Software=Image Editor"
        ])
    else:
        return

    cmd.append(str(file_path))
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def anonymize_file(file_path, spoof=False):
    path = Path(file_path)
    if not path.is_file():
        return

    # تجاهل الملفات المخفية أو ملفات النظام
    if path.name.startswith("."):
        return

    mime_type = detect_file_type(path)
    print(f"{CYAN}[*] File:{RESET} {path.name} | {YELLOW}Detected Type:{RESET} {mime_type}")

    if mime_type in SUPPORTED_MIMES:
        try:
            # 1. مسح عميق وإعادة بناء الملف via mat2
            result = subprocess.run(
                ["mat2", "--inplace", str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode == 0:
                # 2. إضافة بيانات محايدة لو المستخدم طلب وضع التمويه (Spoof)
                if spoof:
                    spoof_generic_metadata(path, mime_type)
                    print(f"    {GREEN}[+] Deep wiped & spoofed with anonymous metadata!{RESET}")
                else:
                    print(f"    {GREEN}[+] Deep wiped successfully (100% clean)!{RESET}")
            else:
                print(f"    {RED}[-] mat2 skipped or failed: {result.stderr.strip()}{RESET}")
                
        except Exception as e:
            print(f"    {RED}[!] Error processing {path.name}: {e}{RESET}")
    else:
        print(f"    {YELLOW}[!] Unsupported or plain-text file type, skipped safely.{RESET}")

def process_target(target_path, recursive=False, spoof=False):
    target = Path(target_path)
    
    if not target.exists():
        print(f"{RED}[!] Error: '{target}' does not exist.{RESET}")
        sys.exit(1)

    if target.is_file():
        anonymize_file(target, spoof=spoof)
    elif target.is_dir():
        print(f"{CYAN}[*] Scanning directory:{RESET} {target} (Recursive={recursive})\n")
        files = target.rglob("*") if recursive else target.glob("*")
        for item in files:
            if item.is_file():
                anonymize_file(item, spoof=spoof)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automated File Type Detection & Metadata Anonymizer"
    )
    parser.add_argument("target", help="Target file or directory path")
    parser.add_argument("-r", "--recursive", action="store_true", help="Scan subdirectories recursively")
    parser.add_argument("-s", "--spoof", action="store_true", help="Replace wiped metadata with generic anonymous tags")
    
    args = parser.parse_args()
    process_target(args.target, recursive=args.recursive, spoof=args.spoof)
