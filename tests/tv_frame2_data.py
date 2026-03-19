"""FrameType 2 测试向量 TV201-TV215 清洁十六进制数据。

数据来源: TXS-10002-2025 标准附录 H, 第 14 章测试向量。
标注 'PDF verified' 的数据已从标准 PDF 直接提取并校验。
标注 'OCR' 的数据由 OCR 识别后人工校正, 尚需从 PDF 原文验证。

每条测试向量包含:
  - header: TV 参数 (FrameType, ctrlFT, MCS, mSeq, ctrlBits, dLen)
  - pid: PID 24-bit 十六进制
  - pnSeq: PN 序列 [1st_32bit, 2nd_31bit]
  - bchOut: BCH 输出 [1st, 2nd]
  - sync_word: 同步字 [1st, 2nd] (共 64 bit)
  - crc_seed: CRC 种子 (24-bit)
  - wt_seed: 白化种子 (7-bit)
  - HeadBits: 头部信息比特 (first_32bit, second_32bit)
  - txHead: 含 CRC 的头部 (first_32bit, second_32bit)
  - txHeadC: 编码后头部 (first_32bit, second_32bit)
  - txHeadW: 加扰后头部 (first_32bit, second_32bit)
  - txPyLd: 含 CRC 的载荷比特 十六进制对列表
  - txPyLdC: 编码后载荷 十六进制对列表
  - txPyLdW: 加扰后载荷 十六进制对列表

十六进制对格式: (first_32bit_hex, second_32bit_hex)
"""

# ========================== 共享字段(按 PID 分组) ==========================

# Group A: TV201-TV206, PID=0x879012  — PDF verified
GROUP_A = {
    "pid": 0x00879012,
    "pid_bits_lsb": "01001000 00001001 11100001 00000000",
    "pnSeq": (0x92DD9ABF, 0x0218A7A3),
    "bchOut": (0x77879012, 0x2DC4398F),
    "sync_word": (0xE55A0AAD, 0x2FDC9E2C),
}

# Group B: TV207-TV208, PID=0x123456  — PDF verified
GROUP_B = {
    "pid": 0x00123456,
    "pid_bits_lsb": "01101010 00101100 01001000 00000000",
    "pnSeq": (0x92DD9ABF, 0x0218A7A3),
    "bchOut": (0xA6123456, 0x5108B060),
    "sync_word": (0x34CFAEE9, 0x531017C3),
}

# Group C: TV209-TV212, PID=0x234567  — PDF verified
GROUP_C = {
    "pid": 0x00234567,
    "pid_bits_lsb": "11100110 10100010 11000100 00000000",
    "pnSeq": (0x92DD9ABF, 0x0218A7A3),
    "bchOut": (0x0A234567, 0x3FF25058),
    "sync_word": (0x98FEDFD8, 0x3DEAF7FB),
}

# Group D: TV213, PID=0x654321  — PDF verified
GROUP_D = {
    "pid": 0x00654321,
    "pid_bits_lsb": "10000100 11000010 10100110 00000000",
    "pnSeq": (0x92DD9ABF, 0x0218A7A3),
    "bchOut": (0x9D654321, 0x2874A0EE),
    "sync_word": (0x0FB8D99E, 0x2A6C074D),
}

# Group E: TV214-TV215, PID=0x345678  — PDF verified
GROUP_E = {
    "pid": 0x00345678,
    "pid_bits_lsb": "00011110 01101010 00101100 00000000",
    "pnSeq": (0x92DD9ABF, 0x0218A7A3),
    "bchOut": (0xAA345678, 0x4BF315C9),
    "sync_word": (0x38E9CCC7, 0x49EBB26A),
}


# ========================= 各 TV 详细数据 =========================

# --- TV201: FT=2, A3, MCS=7, dLen=1 — PDF verified ---
TV201 = {
    "tv_id": 201,
    "frame_type": 2,
    "ctrlFT": "A3",
    "mcs": 7,
    "mSeq": 0,
    "ctrl_bits": 36,
    "dLen": 1,
    "group": GROUP_A,
    "crc_seed": 0x00123456,
    "wt_seed": 0x52,
    # PDF verified
    "HeadBits": (0x03DE9497, 0x00000000),
    "txHead": (0x03DE9497, 0x00003380),
    "txHeadC": (0xE82429AB, 0x20DF226C),
    "txHeadW": (0x8ACF4966, 0xCFF3B24E),
    "txPyLd_val": 0x7E0AAC16,  # 32 bits (dLen=1)
    "txPyLdC": (0x6FC92D8B, 0x7E723C30),  # 64 bits
    "txPyLdW": (0xBD44EA7B, 0xD94F9D67),  # 64 bits
}

# --- TV202: FT=2, A3, MCS=7, dLen=67 — PDF verified ---
TV202 = {
    "tv_id": 202,
    "frame_type": 2,
    "ctrlFT": "A3",
    "mcs": 7,
    "mSeq": 0,
    "ctrl_bits": 36,
    "dLen": 67,
    "group": GROUP_A,
    "crc_seed": 0x00123456,
    "wt_seed": 0x53,
    # PDF verified
    "HeadBits": (0x87116A97, 0x00000000),
    "txHead": (0x87116A97, 0x00005550),
    "txHeadC": (0x08803355, 0x4004B8ED),
    "txHeadW": (0xA9D7E1D8, 0xF0621FD0),
    "txPyLdC": [  # 704 bits = 11 lines — PDF verified
        (0xBE6B5F7C, 0x35233F1C),
        (0xE0535F73, 0x5B36B8AB),
        (0x2AAD28A8, 0x4A81D417),
        (0xF32BF9D9, 0xFC46DDB2),
        (0xDA18246F, 0xD9B5C549),
        (0xB069DC1A, 0x3E498382),
        (0x28FCA54C, 0xA121F434),
        (0x1BBA9B6E, 0xD91FBDAD),
        (0xDD7E056C, 0xD0EF5852),
        (0x05F25513, 0xE8FD4D16),
        (0xA19D04C7, 0xC8F46DAE),
    ],
    "txPyLdW": [  # 704 bits = 11 lines — PDF verified
        (0xF67A6E09, 0xD6DB488A),
        (0x30F8B635, 0x8305EB35),
        (0x0EA5B012, 0x3B7DEFDC),
        (0x9B7E0D7A, 0x905F747D),
        (0x481C6832, 0x614BD8AC),
        (0x0443264B, 0x88455765),
        (0xE1FE8362, 0x7D5EFAC6),
        (0xC1AFE646, 0x8219D7DE),
        (0xB9FF167B, 0xBED0DF2B),
        (0xE8F8EB87, 0x457E782F),
        (0x13DD8D4C, 0xFFEBAE12),
    ],
}

# --- TV203: FT=2, A3, MCS=9, dLen=68 — PDF verified ---
TV203 = {
    "tv_id": 203,
    "frame_type": 2,
    "ctrlFT": "A3",
    "mcs": 9,
    "mSeq": 0,
    "ctrl_bits": 36,
    "dLen": 68,
    "group": GROUP_A,
    "crc_seed": 0x00123456,
    "wt_seed": 0x55,
    # PDF verified
    "HeadBits": (0x88643E99, 0x00000000),
    "txHead": (0x88643E99, 0x00003760),
    "txHeadC": (0x2D877741, 0x2543D5D0),
    "txHeadW": (0x9DE1D07C, 0x6D52E4A5),
    "txPyLd": [  # 576 bits = 9 lines — PDF verified
        (0x07635DC5, 0x1B2EF2A7),
        (0xD8371D6D, 0x1C6DBB6A),
        (0x5F84329F, 0x02416899),
        (0xF0E66FFA, 0xED8B74D4),
        (0x56E1ACE3, 0x647EB08E),
        (0x0CE7EF0A, 0x631DED4B),
        (0x17C91DAD, 0xBB2AF026),
        (0x0BA4A6C7, 0xE4AEC2B9),
        (0x09E5CE5E, 0x00C9AF3D),
    ],
    "txPyLdC": [  # 960 bits = 15 lines — PDF verified
        (0x0009EB4F, 0x1C01BB46),
        (0x2FA63EDE, 0xE7E53AD0),
        (0xEE4500E6, 0x398345AA),
        (0xA7E99705, 0x102FCDFA),
        (0xFC04E2DD, 0x62E28174),
        (0x725596B2, 0x5191378A),
        (0x80B3F2E6, 0xE6A8B739),
        (0x3DB491AE, 0x52C65D54),
        (0xEF9301B6, 0xA7F9BFC1),
        (0xAD401497, 0x10E39C15),
        (0x88A4B8F5, 0x42DA8496),
        (0xF6B46EE8, 0xC903647E),
        (0x465C111C, 0xADA38D6B),  # corrected: was 0x0465C11C in OCR
        (0xE775E560, 0x562F23B2),
        (0xCDFE5B68, 0xA46832FE),  # corrected: was 0xCDFFE5B6 in OCR
    ],
    "txPyLdW": [  # 960 bits = 15 lines — PDF verified
        (0xE3F19CD9, 0xCCAA5200),
        (0xF7956D40, 0xC3EDA26A),
        (0x9FB93B2D, 0x51D6B109),
        (0xCBF03ECA, 0x822B81A7),
        (0x44FAFF38, 0xD6C87B25),
        (0xC4594255, 0x989311A4),
        (0x5CCCFC14, 0x3CBDCA11),
        (0x66B2FBDD, 0x36474E43),
        (0x81AC86CF, 0x4AF30155),
        (0x00C321AE, 0xA2A3159E),
        (0xBFBB7B49, 0xB45FDBDC),
        (0x2075F474, 0x902320BB),
        (0x5DD3F0C2, 0xD6E122CE),
        (0x0C15282E, 0x7ABF01D0),  # corrected: was 0x007ABF0D in OCR
        (0x4039AB87, 0x99C9652C),
    ],
}

# --- TV204: FT=2, A3, MCS=9, dLen=238 — OCR (not yet PDF verified) ---
TV204 = {
    "tv_id": 204,
    "frame_type": 2,
    "ctrlFT": "A3",
    "mcs": 9,
    "mSeq": 0,
    "ctrl_bits": 36,
    "dLen": 238,
    "group": GROUP_A,
    "crc_seed": 0x00123456,
    "wt_seed": 0x62,
    # OCR — txPyLd (1928 bits), first 20 lines readable:
    "txPyLd": [
        (0xA5A667FF, 0x4A2C53A3),
        (0xD5102A10, 0xD0D27377),
        (0xECCBFC81, 0x8B34FCE1),
        (0xD8975947, 0xF287136B),
        (0x81F0C67B, 0x7D7116A9),
        (0x8190FA62, 0xD8D77156),
        (0xCBBCA9C1, 0x0DC75B46),
        (0x1B6EDAB6, 0xE10CA7C7),
        (0x905A2657, 0x399BFE80),
        (0x62DD353C, 0xB86B38FB),
        (0x1FAC2395, 0x39FBC299),
        (0xC77B52C3, 0xF2476B58),
        (0xCABC0985, 0xE929B1EE),
        (0x2BB0AE42, 0x797397B9),
        (0x122B50C2, 0x1BAEA285),
        (0xAA406839, 0x04028110),
        (0x93BBAAA0, 0xC379D3D3),
        (0x61FCC1F8, 0x09C5DA56),
        (0x88D57016, 0x22757414),
        (0xF1A6E7AF, 0x305E24D6),
        # lines 21-24 repeat pattern, then partial — OCR
    ],
    # txPyLdW (3136 bits) — OCR, partial extraction:
    "txPyLdW": [
        (0xAB905277, 0xC3A6AA0E),
        (0xDBAA3A90, 0x74670C00),
        (0xECCF9E05, 0xAFEB2A98),
        (0xD6A9B43C, 0x7AC6EFAE),
        (0x6232CC61, 0x3A0EBACD),
        (0x1E381B1C, 0xA1237107),
        (0x7E640FDA, 0x8835DE93),
        (0x969F1FB2, 0xA643FEFC),
        (0xBF036FAD, 0x9C012D57),
        (0x063266AB, 0xE1F84ABB),
        (0x1939C50F, 0x3B782752),
        (0x2D65FBA6, 0x17FF270B),
        # remaining lines — OCR, partially readable
    ],
}

# --- TV205: FT=2, A3, MCS=6, dLen=1 — PDF verified ---
TV205 = {
    "tv_id": 205,
    "frame_type": 2,
    "ctrlFT": "A3",
    "mcs": 6,
    "mSeq": 0,
    "ctrl_bits": 36,
    "dLen": 1,
    "group": GROUP_A,
    "crc_seed": 0x00123456,
    "wt_seed": 0x63,
    # PDF verified
    "HeadBits": (0x03769596, 0x00000000),
    "txHead": (0x03769596, 0x00005990),
    "txHeadC": (0x820A43B9, 0x4AA448D4),
    "txHeadW": (0x217BBF82, 0x85CC1D20),
    "txPyLd_val": 0x1B262C58,  # 32 bits
    "txPyLdC": (0x57624075, 0x1C290B3E),  # 64 bits
    "txPyLdW": (0x0A0E59DC, 0xF9BB0F72),  # 64 bits
}

# --- TV206: FT=2, A3, MCS=6, dLen=177 — PDF verified ---
TV206 = {
    "tv_id": 206,
    "frame_type": 2,
    "ctrlFT": "A3",
    "mcs": 6,
    "mSeq": 0,
    "ctrl_bits": 36,
    "dLen": 177,
    "group": GROUP_A,
    "crc_seed": 0x00123456,
    "wt_seed": 0x65,  # PDF verified
    # PDF verified
    "HeadBits": (0x63B96B96, 0x00000001),
    "txHead": (0x63B96B96, 0x000063A1),
    "txHeadC": (0x2C788B0D, 0x64A9001F),
    "txHeadW": (0x9E380286, 0x53B6C3A3),
    "txPyLd": [  # 1440 bits, 23 lines (last one 16 bits) — OCR
        (0x66DFB42C, 0x2BD0925B),
        (0xDCD5F046, 0x58070361),
        (0xCEBE8895, 0x7A921B4E),
        (0xE8C97D91, 0x188F5641),
        (0x1BEE8A94, 0x937BD293),
        (0x88351C2D, 0xF5A466BF),
        (0xA3E58E76, 0x297196F9),
        (0xFBE28D17, 0xE7CF1E6C),
        (0x81709659, 0x0F0663FD),
        (0x99FFC018, 0x14E8E969),
        (0x0A84128B, 0x9CDDF544),
        (0xFF207434, 0x3F387B32),
        (0xD651E2CD, 0xC4DAF625),
        (0x319EFCA1, 0x45AA607C),
        (0x3E989F5C, 0xDC55A064),
        (0x2A707635, 0xD6D1B2EF),
        (0xB6AD8371, 0x29F1C6DB),
        (0x8995F843, 0xFFA02416),
        (0x4D4F0E66, 0xCE3ED8B7),
        (0x08E56E1A, 0xF0A647EB),
        (0xD4B0CE7E, 0xDAD631DE),
        (0x02617C91, 0x6C7BB2AF),
        # last line: partial 0000004A (32 bits only) — OCR
    ],
    "txPyLdC": [  # 1984 bits = 31 lines — PDF verified
        (0x001B30AF, 0xC3876D94),
        (0x72C19E48, 0x9654183D),
        (0xCA695F8C, 0xFFDDE743),
        (0x20F5E307, 0xED5BC9FC),
        (0x8346B950, 0xBB30DA2D),
        (0x17B3C1F2, 0x9E69BA31),
        (0xBEAF4D1D, 0xE39D58F8),
        (0x8EDF1B10, 0xBD525F31),
        (0x59946979, 0xF6C5BB2C),
        (0xF20F779E, 0x05CBA726),
        (0x26F53E7B, 0xDC194639),
        (0x1085B50D, 0xB394CE35),
        (0xDC618654, 0xC8CEF943),
        (0x6844B801, 0x41EBC608),
        (0x637B9666, 0x2B60B590),
        (0x01FE8916, 0x8A725596),
        (0xBEEE8B62, 0xC7A55DB6),
        (0x4124AD84, 0x24C1C158),
        (0x2A9F71E7, 0x550F6D24),
        (0x6086844B, 0x3F841EBC),
        (0xFFA96922, 0x44920AF4),
        (0x8E7579F3, 0x6BEC9655),
        (0xE09EAA47, 0x647EF6B5),
        (0xBCCAFE77, 0xFF11B76C),
        (0x7435BD27, 0x477744F5),
        (0xDB1DB205, 0x6F72CCFA),
        (0x5D397557, 0x226EE18D),
        (0x9698BBF3, 0x70A949B0),
        (0x715D26D7, 0xA92F98C3),
        (0x872A64F5, 0xCA671A8B),
        (0xB4C666EB, 0x4436961B),
    ],
    "txPyLdW": [  # 1984 bits — OCR
        (0xF69E6FE5, 0x1546F708),
        (0x2BE1DA8D, 0x8DDBF9E3),
        (0xB12BF029, 0x14BD2A0D),
        (0x0C65C165, 0x609C3913),
        (0xBEE7EE82, 0xCE80BC8A),
        (0x81FBD0C3, 0xD88A4246),
        (0x207FE6F4, 0x59456BAB),
        (0x45FB1388, 0x1E23A30A),
        (0x96FC3C8D, 0xABA9A285),
        (0x179D73D2, 0x5473593B),
        (0xC1411481, 0xF2AF4AED),
        (0xE24CB72B, 0x9B48B13B),
        (0xAFBB9329, 0xDF95FF29),
        (0x11203912, 0xD585F98F),
        (0x5A969CD8, 0xA0CD36A5),
        (0xBD4CC99F, 0xC0454A55),
        (0x22180E3D, 0x02739C2C),
        (0x9F7D8DC0, 0x81DA4EB9),
        (0x64E43348, 0x37E40DE9),
        (0x8FAA1469, 0xED09D94C),
        (0x5894C875, 0x75E7BA92),
        (0xF9E331E2, 0x82AA75AD),
        (0xB3007AEC, 0xFCC42E86),
        (0x8701DA7F, 0x0BB2C690),
        (0xDDFAD572, 0x0B2A28EC),
        (0xC6F82001, 0x95237404),
        (0x89DEC17D, 0x04405781),
        (0x986A72F1, 0x0D8195CF),
        (0x1B2EFCC2, 0xBA38C3C5),
        (0x00530074, 0x74F374B4),
        (0x81FF8BE1, 0xCDBD3B98),
    ],
}

# --- TV207: FT=2, A7, MCS=10, dLen=178 — PDF verified ---
TV207 = {
    "tv_id": 207,
    "frame_type": 2,
    "ctrlFT": "A7",
    "mcs": 10,
    "mSeq": 0,
    "ctrl_bits": 36,
    "dLen": 178,
    "group": GROUP_B,
    "crc_seed": 0x00123456,
    "wt_seed": 0x52,
    # PDF verified
    "HeadBits": (0x64CC3F9A, 0x00000001),
    "txHead": (0x64CC3F9A, 0x000086D1),
    "txHeadC": (0xF1D237B4, 0xF9439A80),
    "txHeadW": (0x93395779, 0x166F0AA2),
    "PyLdBits": [  # 1448 bits = 23 lines (last 32 bits only) — PDF verified
        (0xE02C138B, 0xE82911AA),
        (0xCF5E44EA, 0x49ADE34D),
        (0x8A5460BC, 0x99DFD410),
        (0x8875343C, 0xCC9FDC15),
        (0x2FD2134B, 0x4F6E5AE6),
        (0x9B7ED0B2, 0xAF42496D),
        (0x7357C118, 0x601C0D87),
        (0x3AFA2255, 0xEA486D3B),
        (0xA325F645, 0x623D5907),
        (0x6FBA2A50, 0x4DEF4A4C),
        (0x20D470B6, 0xD6919AFE),
        (0x8F9639DB, 0xA5C65BE6),
        (0xEF8A345C, 0x9F3C79B3),
        (0x05C25967, 0x3C198FF6),
        (0x67FF0060, 0x53A3A5A6),
        (0x2A104A2C, 0x7377D510),
        (0xFC81D0D2, 0xFCE1ECCB),
        (0x59478B34, 0x136BD897),
        (0xC67BF287, 0x16A981F0),
        (0xFA627D71, 0x71568190),
        (0xA9C1D8D7, 0x5B46CBBC),
        (0xDAB60DC7, 0xA7C71B6E),
        (0x0000E10C, None),  # 32 bits only
    ],
    "txPyLd": [  # same as PyLdBits, last entry with CRC — PDF verified
        (0xE02C138B, 0xE82911AA),
        (0xCF5E44EA, 0x49ADE34D),
        (0x8A5460BC, 0x99DFD410),
        (0x8875343C, 0xCC9FDC15),
        (0x2FD2134B, 0x4F6E5AE6),
        (0x9B7ED0B2, 0xAF42496D),
        (0x7357C118, 0x601C0D87),
        (0x3AFA2255, 0xEA486D3B),
        (0xA325F645, 0x623D5907),
        (0x6FBA2A50, 0x4DEF4A4C),
        (0x20D470B6, 0xD6919AFE),
        (0x8F9639DB, 0xA5C65BE6),
        (0xEF8A345C, 0x9F3C79B3),
        (0x05C25967, 0x3C198FF6),
        (0x67FF0060, 0x53A3A5A6),
        (0x2A104A2C, 0x7377D510),
        (0xFC81D0D2, 0xFCE1ECCB),
        (0x59478B34, 0x136BD897),
        (0xC67BF287, 0x16A981F0),
        (0xFA627D71, 0x71568190),
        (0xA9C1D8D7, 0x5B46CBBC),
        (0xDAB60DC7, 0xA7C71B6E),
        (0xA091E10C, 0x00000023),  # CRC appended
    ],
    "txPyLdC": [  # 1984 bits = 31 lines — PDF verified (corrected from OCR)
        (0x3769FF34, 0xB0D7AF7E),
        (0x5CC7C204, 0xA4EF0321),
        (0x961A5D85, 0x19758D88),
        (0xFD476489, 0xAF7E09F0),
        (0xA5AB8B23, 0x1D14061F),
        (0x0A591365, 0xA7DA1DEB),
        (0x18749C69, 0x0CF61E16),
        (0x824F2D57, 0xBD076348),
        (0x726F9801, 0x16D5EA44),
        (0xCBFE111C, 0x5EFC13E1),
        (0x503A82DB, 0x657F3B29),
        (0x88DBB65E, 0x1EE95CFF),
        (0x2A617809, 0x4EB5F64B),
        (0x0F0B0C3A, 0x96AB867B),
        (0xB1A44127, 0x7536DE83),
        (0x3F7B5A37, 0xC86481B2),
        (0x5DB981EC, 0xAA81FF93),
        (0x613A8A99, 0x1A102009),
        (0xBFDC9160, 0x1CEAC6D8),
        (0x6E152937, 0xA147DC7F),
        (0x459CE4E4, 0x0D6EBF52),
        (0xE29C9565, 0xC194644D),
        (0x3D1EE95D, 0xD4E86E26),
        (0x3CE0604A, 0x5E9A3BB0),
        (0x0B0D139F, 0xAD6308DC),
        (0x7354F95D, 0xC63B7C6D),
        (0xE809177A, 0x7CA0132C),
        (0x44DE29C9, 0x69DC1946),
        (0x0E49F35C, 0xB51066E8),
        (0xDA626939, 0xF7F895B1),
        (0xCF6ACF6A, 0x30953095),
    ],
    "txPyLdW": [  # 1984 bits = 31 lines — PDF verified
        (0xE5E438C4, 0x17EA0E29),
        (0x6DB27262, 0xD3794B30),
        (0x7F5CBE7D, 0x4AEB5D23),
        (0x65FDBCBA, 0x94B52DF8),
        (0x5108FADF, 0xB4DB6E4A),
        (0x46047F7C, 0xBA3F8FEF),
        (0xE2252497, 0xD811AA3C),
        (0xA4619B5B, 0xB3F5AA4A),
        (0x0F47447E, 0x7CA63051),
        (0xD8E94A1A, 0xD9857760),
        (0xEEAEECE4, 0x5046D623),  # corrected: was 0x0EEAECE4 in OCR
        (0x01501BDD, 0xDD55EEBF),
        (0x752B4F16, 0xD42900CE),
        (0x4BCEDAFB, 0x7775DF5B),
        (0x1E015AA8, 0xB878A5C1),
        (0x1D19B157, 0x388BAD22),
        (0x0A6B0C2B, 0xCC26C232),
        (0x700BFF29, 0xE267B641),
        (0x1435D783, 0x2FB95808),
        (0x668D93EF, 0x5D7C175B),
        (0x10684795, 0x14C7703A),
        (0xE6D0C809, 0x3F8981DF),
        (0x17E4B8E5, 0xD83C8992),
        (0x3EC64EFC, 0x2194C979),
        (0x1E703B43, 0xAB097B06),
        (0xF247EE06, 0xF9BC0509),
        (0xE2B78314, 0xFF952AC1),
        (0x0457A264, 0x761FA5F4),
        (0x8B16B96B, 0x748AFA1E),
        (0xFA26ACEF, 0x78194BE8),
        (0x8DC56A71, 0x50587EEE),
    ],
}

# --- TV208: FT=2, A7, MCS=10, dLen=255 — OCR (not yet PDF verified) ---
TV208 = {
    "tv_id": 208,
    "frame_type": 2,
    "ctrlFT": "A7",
    "mcs": 10,
    "mSeq": 0,
    "ctrl_bits": 36,
    "dLen": 255,
    "group": GROUP_B,
    "crc_seed": 0x00123456,
    "wt_seed": 0x62,
    # 大量载荷, 部分 OCR 质量差 — OCR
    # txPyLd (2064 bits), txPyLdC (2432 bits), txPyLdW (2432 bits)
    # 数据过长, 需从标准原文 15841-16101 行提取
}

# --- TV209: FT=2, A1, MCS=11, dLen=1 — PDF verified ---
TV209 = {
    "tv_id": 209,
    "frame_type": 2,
    "ctrlFT": "A1",
    "mcs": 11,
    "mSeq": 0,
    "ctrl_bits": 28,
    "dLen": 1,
    "group": GROUP_C,
    "crc_seed": 0x00555555,
    "wt_seed": 0x55,
    # PDF verified (已在 TestTV209 中完成验证)
    "HeadBits": (0x0010945B, 0x00000000),
    "txHead": (0x2010945B, 0x0000004E),
    "txPyLd_val": 0xE5FAEA05,  # 32 bits
    "txPyLdC": (0x9DE61094, 0x9D19EF94),  # 64 bits
    "txPyLdW": (0x7E1E6702, 0x4DB206D2),  # 64 bits
    "txHeadC": (0x93C6E4E4, 0x5C6F4D2B),  # 64 bits
    "txHeadW": (0x23A043D9, 0x147E7C5E),  # 64 bits
}

# --- TV210: FT=2, A1, MCS=11, dLen=207 — OCR (not yet PDF verified) ---
TV210 = {
    "tv_id": 210,
    "frame_type": 2,
    "ctrlFT": "A1",
    "mcs": 11,
    "mSeq": 0,
    "ctrl_bits": 28,
    "dLen": 207,
    "group": GROUP_C,
    "crc_seed": 0x00555555,
    "wt_seed": 0x55,
    # txPyLd (1680 bits), txPyLdC (1984 bits), txPyLdW (1984 bits)
    # 数据过长, 需从标准原文 16140-16269 行提取 — OCR
}

# --- TV211: FT=2, A1, MCS=11, dLen=208 — OCR (not yet PDF verified) ---
TV211 = {
    "tv_id": 211,
    "frame_type": 2,
    "ctrlFT": "A1",
    "mcs": 11,
    "mSeq": 0,
    "ctrl_bits": 28,
    "dLen": 208,
    "group": GROUP_C,
    "crc_seed": 0x00555555,
    "wt_seed": 0x55,
    # txPyLd (1688 bits), txPyLdC (1984 bits), txPyLdW (1984 bits)
    # 数据过长, 需从标准原文 16270-16515 行提取 — OCR
}

# --- TV212: FT=2, A1, MCS=11, dLen=255 — OCR (not yet PDF verified) ---
TV212 = {
    "tv_id": 212,
    "frame_type": 2,
    "ctrlFT": "A1",
    "mcs": 11,
    "mSeq": 0,
    "ctrl_bits": 28,
    "dLen": 255,
    "group": GROUP_C,
    "crc_seed": 0x00555555,
    "wt_seed": 0x55,
    # txPyLd (2064 bits), txPyLdC (2432 bits), txPyLdW (2432 bits)
    # 数据过长, 需从标准原文 16516-16799 行提取 — OCR
}

# --- TV213: FT=2, A5, MCS=8, dLen=123 — PDF verified (head) ---
TV213 = {
    "tv_id": 213,
    "frame_type": 2,
    "ctrlFT": "A5",
    "mcs": 8,
    "mSeq": 0,
    "ctrl_bits": 28,
    "dLen": 123,
    "group": GROUP_D,
    "crc_seed": 0x87654321,
    "wt_seed": 0x43,
    # PDF verified
    "txHead": (0x00F69558, 0x00000044),
    "txHeadC": (0x90F61E2D, 0x5050DE8B),
    "txHeadW": (0xCD9A0784, 0xB5C2DAC7),
    "txPyLd": [  # 1016 bits = 16 lines, CRC appended — PDF verified
        (0x21B4ECEB, 0x97D917A9),
        (0xF5641E8C, 0xE8A94188),
        (0xBD2931BE, 0x51C2D937),
        (0x466BF883, 0x58E76F5A),
        (0x196F9A3E, 0x28D17297),
        (0xF1E6CFBE, 0x09659E7C),
        (0x663FD817, 0xFC0180F0),
        (0x8E96999F, 0x4128B14E),
        (0xDF5440A8, 0x074349CD),
        (0x87B32FF2, 0x1E2CD3F3),
        (0xAF625D65, 0xEFCA1C4D),
        (0xA607C319, 0x89F5C45A),
        (0x5A0643E9, 0x07635DC5),
        (0x1B2EF2A7, 0xD8371D6D),
        (0x1C6DBB6A, 0x5F84329F),
        (0xFF416899, 0x00B54034),  # last entry with CRC
    ],
    "txPyLdC": [  # MCS=8 rate 1/1, same as txPyLd — PDF verified
        (0x21B4ECEB, 0x97D917A9),
        (0xF5641E8C, 0xE8A94188),
        (0xBD2931BE, 0x51C2D937),
        (0x466BF883, 0x58E76F5A),
        (0x196F9A3E, 0x28D17297),
        (0xF1E6CFBE, 0x09659E7C),
        (0x663FD817, 0xFC0180F0),
        (0x8E96999F, 0x4128B14E),
        (0xDF5440A8, 0x074349CD),
        (0x87B32FF2, 0x1E2CD3F3),
        (0xAF625D65, 0xEFCA1C4D),
        (0xA607C319, 0x89F5C45A),
        (0x5A0643E9, 0x07635DC5),
        (0x1B2EF2A7, 0xD8371D6D),
        (0x1C6DBB6A, 0x5F84329F),
        (0xFF416899, 0x00B54034),
    ],
    "txPyLdW": [  # 1016 bits — PDF verified
        (0x700C12F6, 0x706D3D53),
        (0xDBD21258, 0x1A6043AE),
        (0x95F54EB0, 0x2218CC4A),
        (0x5130FEE9, 0x2183EE49),
        (0x8D01A5B9, 0x113C7829),
        (0x7A4B4C8B, 0xB5D7DEF5),
        (0x2C08C7D4, 0x60F705AF),
        (0x4B405805, 0x9F71910A),
        (0x7A4FCF49, 0x49380B62),
        (0xE5584F3F, 0xF10043D1),
        (0x7DEF9A95, 0x48F7BD1A),
        (0x9772737F, 0xFE638C4B),
        (0xB340A011, 0x54FD8D6E),
        (0x83942A94, 0xE3FC3965),
        (0xE8CECA96, 0xF64B5ACA),
        (0xB31C0480, 0x0050D230),
    ],
}

# --- TV214: FT=2, A2, MCS=12, dLen=33 — OCR (not yet PDF verified) ---
TV214 = {
    "tv_id": 214,
    "frame_type": 2,
    "ctrlFT": "A2",
    "mcs": 12,
    "mSeq": 0,
    "ctrl_bits": 28,
    "dLen": 33,
    "group": GROUP_E,
    "crc_seed": 0x87654321,
    "wt_seed": 0x45,  # OCR: 0000045
    # txPyLdC tail (from table, 3 lines visible) — OCR:
    "txPyLdC_tail": [
        (0x22B50C27, 0xBAEA2851),
        (0xA4068391, 0x4028110A),
        (0xC2A7DB00, 0x000000D1),
    ],
    "txPyLdW": [  # 296 bits — OCR
        (0x519120A1, 0x467CAAC6),
        (0x9D245222, 0x99CBB290),
        (0x5F9DD058, 0xD099F244),
        (0xB711D897, 0xC751758B),
        (0x7C33B53F, 0x000000DB),
    ],
}

# --- TV215: FT=2, A3, MCS=12, dLen=0 — OCR (not yet PDF verified) ---
TV215 = {
    "tv_id": 215,
    "frame_type": 2,
    "ctrlFT": "A3",
    "mcs": 12,
    "mSeq": 0,
    "ctrl_bits": 36,
    "dLen": 0,
    "group": GROUP_E,
    "crc_seed": 0x00000000,  # OCR garbled, all zeros
    "wt_seed": 0x41,  # OCR unclear (0000041)
    # dLen=0 → 无载荷数据
}


# ========================= 汇总列表 =========================
ALL_TV = [
    TV201, TV202, TV203, TV204, TV205, TV206,
    TV207, TV208,
    TV209, TV210, TV211, TV212,
    TV213,
    TV214, TV215,
]
