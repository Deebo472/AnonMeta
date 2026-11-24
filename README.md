# AnonMeta - Automated File Type Detection & Metadata Anonymizer

AnonMeta is a lightweight Python CLI tool built for Penetration Testers, Bug Bounty Hunters, and Security Researchers to maintain strong Operational Security (OpSec) by automatically detecting file types and stripping sensitive metadata before sharing reports, PoCs, or screenshots.

## Features
1. True File Type Detection: Uses libmagic (Magic Bytes) rather than relying on file extensions.
2. Deep Sanitization: Rebuilds files using mat2 to permanently strip hidden layers and incremental PDF updates.
3. Optional Spoofing: Injects neutral, generic metadata tags via exiftool to avoid leaving empty/suspicious metadata signatures.

## Prerequisites (Debian / Kali Linux)
    sudo apt update && sudo apt install mat2 libimage-exiftool-perl python3-magic -y

## Installation
    git clone https://github.com/Deebo472/AnonMeta.git
    cd AnonMeta
    chmod +x anonmeta.py
    sudo cp anonmeta.py /usr/local/bin/anonmeta

## Usage
- Deep wipe a single file: anonmeta report.pdf
- Deep wipe & spoof: anonmeta report.pdf -s
- Recursive directory clean: anonmeta ./PoC_Folder -r -s
