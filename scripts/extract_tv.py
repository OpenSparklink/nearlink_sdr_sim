"""从 PDF 中提取 FrameType 2 测试向量数据。

提取格式:
  #TV NNN FrameType X ctrlFT AX MCS N ...
  ===1st==:===2nd==: ... txPyLdC (NNNN) --->MSB
  HHHHHHHH:HHHHHHHH: binary...
"""
import re
import json
import fitz  # pymupdf

PDF_PATH = "/home/sanchuanhehe/Documents/Summary-of-Sparkling-Information/Standard/TXS-10002-2025接入层-同步低功耗空口 sle技术要求和测试方法.pdf"

doc = fitz.open(PDF_PATH)

# Collect all text from hex data pages (540-753)
all_text = ""
for i in range(540, 753):
    all_text += doc[i].get_text() + "\n"

# Parse TV sections
# Pattern: #TV NNN FrameType ...
tv_pattern = re.compile(r'#TV\s+(\d+)\s+FrameType\s+(\d+)\s+ctrlFT\s+(\w+)\s+MCS\s+(\d+)')

# Split text into TV sections
tv_sections = {}
parts = re.split(r'(#TV\s+\d+)', all_text)
current_tv = None
for part in parts:
    m = re.match(r'#TV\s+(\d+)', part)
    if m:
        current_tv = int(m.group(1))
        tv_sections[current_tv] = part
    elif current_tv is not None:
        tv_sections[current_tv] += part

# Extract hex data for specific TVs
def extract_hex_pairs(text, label):
    """Extract hex pairs from '===1st==:===2nd==: ... label ...' sections."""
    # Find the section for the label
    pattern = rf'===1st==:===2nd==:.*?{label}\s*\(\d+\)'
    m = re.search(pattern, text)
    if not m:
        # Try single-column format
        pattern2 = rf'========:.*?{label}\s*\(\d+\)'
        m = re.search(pattern2, text)
        if not m:
            return None

    # Get text after the header until next section or end
    start = m.end()
    # Find next section header
    next_section = re.search(r'===(?:1st|====)', text[start:])
    if next_section:
        end = start + next_section.start()
    else:
        end = len(text)

    section_text = text[start:end]

    # Extract hex:hex pairs
    hex_pairs = []
    # Pattern: 8-hex:8-hex: binary... or 8-hex: binary...
    for line in section_text.split('\n'):
        # Two-column: HHHHHHHH:HHHHHHHH:
        m2 = re.match(r'\s*([0-9A-Fa-f]{8}):([0-9A-Fa-f]{8}):', line)
        if m2:
            hex_pairs.append((int(m2.group(1), 16), int(m2.group(2), 16)))
            continue
        # Single column (last line): HHHHHHHH:
        m1 = re.match(r'\s*([0-9A-Fa-f]{8}):', line)
        if m1:
            hex_pairs.append((int(m1.group(1), 16), None))

    return hex_pairs if hex_pairs else None

# Extract single-value hex
def extract_single_hex(text, label):
    pattern = rf'========:.*?{label}\s*\(\d+\)'
    m = re.search(pattern, text)
    if not m:
        return None
    start = m.end()
    next_line = text[start:start+200].split('\n')
    for line in next_line:
        m2 = re.match(r'\s*([0-9A-Fa-f]{8}):', line)
        if m2:
            return int(m2.group(1), 16)
    return None

# Process each target TV
target_tvs = [201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215]

for tv_id in target_tvs:
    if tv_id not in tv_sections:
        print(f"TV{tv_id}: NOT FOUND")
        continue

    section = tv_sections[tv_id]
    print(f"\n{'='*60}")
    print(f"TV{tv_id}")
    print(f"{'='*60}")

    # Extract header info
    m = tv_pattern.search(section)
    if m:
        print(f"  FrameType={m.group(2)}, ctrlFT={m.group(3)}, MCS={m.group(4)}")

    # Extract various fields
    for field in ['PID', 'pnSeq', 'bchOut', 'SyncWord', 'crcSeed', 'wtSeed',
                  'HeadBits', 'txHead', 'txHeadC', 'txHeadW',
                  'PyLdBits', 'txPyLd', 'txPyLdC', 'txPyLdW']:
        pairs = extract_hex_pairs(section, field)
        if pairs:
            print(f"  {field}: {len(pairs)} entries")
            for j, (a, b) in enumerate(pairs):
                if b is not None:
                    print(f"    [{j:3d}] (0x{a:08X}, 0x{b:08X})")
                else:
                    print(f"    [{j:3d}] (0x{a:08X}, None)")
        else:
            val = extract_single_hex(section, field)
            if val is not None:
                print(f"  {field}: 0x{val:08X}")



