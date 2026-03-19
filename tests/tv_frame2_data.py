"""FrameType 2 测试向量 TV201-TV215 清洁十六进制数据。

数据来源: TXS-10002-2025 标准附录 H, 第 14 章测试向量。
OCR 识别后人工校正, 已知混淆字符: O↔0, I↔1, l↔1。
标注 'OCR unclear' 的字段因原始文档 OCR 质量过低无法可靠提取。

每条测试向量包含:
  - header: TV 参数 (FrameType, ctrlFT, MCS, mSeq, ctrlBits, dLen)
  - pid: PID 24-bit 十六进制
  - pnSeq: PN 序列 [1st_32bit, 2nd_31bit]
  - bchOut: BCH 输出 [1st, 2nd]
  - sync_word: 同步字 [1st, 2nd] (共 64 bit)
  - crc_seed: CRC 种子 (24-bit)
  - wt_seed: 白化种子 (7-bit)
  - txPyLd: 载荷比特 [1st:2nd, ...] 十六进制对列表
  - txPyLdC: 编码后载荷 [1st:2nd, ...] 十六进制对列表
  - txPyLdW: 加扰后载荷 [1st:2nd, ...] 十六进制对列表

十六进制对格式: (first_32bit_hex, second_32bit_hex)
"""

# ========================== 共享字段(按 PID 分组) ==========================

# Group A: TV201-TV206, PID=0x00879012, ctrlFT=A3
GROUP_A = {
    "pid": 0x00879012,
    "pid_bits_lsb": "01001000 00001001 11100001 00000000",
    "pnSeq": (0x92DD9ABF, 0x0218A7A3),
    "bchOut": (0x77879012, 0x2DC4398F),
    "sync_word": (0xE55A0AAD, 0x2FDC9E2C),
}

# Group B: TV207-TV208, PID=0x00123456, ctrlFT=A7
GROUP_B = {
    "pid": 0x00123456,
    "pid_bits_lsb": "01101010 00101100 01001000 00000000",
    "pnSeq": (0x92DD9ABF, 0x0218A7A3),
    "bchOut": (0xA6123456, 0x5108B060),
    "sync_word": (0x34CFAEE9, 0x531017C3),
}

# Group C: TV209-TV212, PID=0x00234567, ctrlFT=A1
GROUP_C = {
    "pid": 0x00234567,
    "pid_bits_lsb": "11100110 10100010 11000100 00000000",
    "pnSeq": (0x92DD9ABF, 0x0218A7A3),
    "bchOut": (0x0A234567, 0x3FF25058),
    "sync_word": (0x98FEDFD8, 0x3DEAF7FB),
}

# Group D: TV213, PID=0x00654321, ctrlFT=A5
GROUP_D = {
    "pid": 0x00654321,
    "pid_bits_lsb": "10000100 11000010 10100110 00000000",
    "pnSeq": (0x92DD9ABF, 0x0218A7A3),
    "bchOut": (0x9D654321, 0x2874A0EE),
    "sync_word": (0x0FB8D99E, 0x2A6C074D),
}

# Group E: TV214-TV215, PID=0x00345678, ctrlFT=A2/A3
GROUP_E = {
    "pid": 0x00345678,
    "pid_bits_lsb": "00011110 01101010 00101100 00000000",
    "pnSeq": (0x92DD9ABF, 0x0218A7A3),
    "bchOut": (0xAA345678, 0x4BF315C9),
    "sync_word": (0x38E9CCC7, 0x49EBB26A),
}


# ========================= 各 TV 详细数据 =========================

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
    # HeadBits/txHead/txHeadC/txHeadW: OCR unclear
    # dLen=1B → very short payload, OCR corrupted
}

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
    # txPyLd 尾部可识别 (部分, 704 bits total)
    "txPyLd_tail": [
        (0x62DD353C, 0xB86B38FB),
        (0x1FAC2395, 0x39FBC299),
        (0xC77B52C3, 0xF2476B58),
        (0xCABC0985, 0xE929B1EE),
        (0xBCB0AE42, 0x0000A53D),
    ],
    "txPyLdC": [  # 704 bits = 11 lines
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
    "txPyLdW": [  # 704 bits = 11 lines
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
    "txPyLdC": [  # 960 bits = 15 lines
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
        (0x0465C11C, 0xADA38D6B),  # note: first hex OCR'd as 465C11C, likely 0465C11C
        (0xE775E560, 0x562F23B2),
        (0xCDFFE5B6, 0xA46832FE),  # note: OCR had extra 8 → CDFFE5B68, likely CDFFE5B6
    ],
    "txPyLdW": [  # 960 bits = 15 lines
        (0xE3F19CD9, 0xCCAA5200),
        (0xF7956D40, 0xC3EDA26A),
        (0x9FB93B2D, 0x51D6B109),
        (0xCBF03ECA, 0x822B81A7),
        (0x44FAFF38, 0xD6C87B25),
        (0xC4594255, 0x989311A4),
        (0x5CCCFC14, 0x3CBDCA11),
        (0x66B2FBDD, 0x36474E43),
        (0x81AC86CF, 0x4AF30155),
        (0x00C321AE, 0xA2A3159E),  # OCR: OC321AE → 0C321AE, possibly 00C321AE
        (0xBFBB7B49, 0xB45FDBDC),
        (0x2075F474, 0x902320BB),
        (0x5DD3F0C2, 0xD6E122CE),
        (0x0C15282E, 0x007ABF0D),  # OCR: OC15282E:7ABF0D → 0C15282E:007ABF0D
        (0x4039AB87, 0x99C9652C),
    ],
}

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
    # txPyLd (1928 bits) - first 20 lines readable:
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
        # lines 21-24 repeat pattern, then partial
    ],
    # txPyLdW (3136 bits) - partial extraction (tables):
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
        # remaining lines in table format, partially OCR'd
    ],
}

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
    # dLen=1B → very short payload, OCR corrupted for HeadBits/txHead
}

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
    "wt_seed": 0x65,
    "txPyLd": [  # 1440 bits, 23 lines (last one 16 bits)
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
        # last line: partial 0000004A (32 bits only)
    ],
    "txPyLdC": [  # 1984 bits = 31 lines
        (0x001B30AF, 0xC3876D94),
        (0x72C19E48, 0x9654183D),
        (0xCA695F8C, 0xFFDDE743),
        # remaining lines in table, partially readable
    ],
    "txPyLdW": [  # 1984 bits - from table
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
    "txPyLd": [  # 1448 bits
        (0x67FF0060, 0x53A3A5A6),
        (0x2A104A2C, 0x7377D510),
        (0xFC81D0D2, 0xFCE1ECCB),
        (0x59478B34, 0x136BD897),
        (0xC67BF287, 0x16A981F0),
        (0xFA627D71, 0x71568190),
        (0xA9C1D8D7, 0x5B46CBBC),
        (0xDAB60DC7, 0xA7C71B6E),
        # last: 0000E10C (32 bits only)
    ],
    "txPyLdC": [  # 1984 bits (from clean hex:binary lines)
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
        (0xA091E10C, 0x00000023),
    ],
    "txPyLdW": [  # 1984 bits (from table)
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
        (0x0EEAECE4, 0x5046D623),
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
        (0x8DC56A71, 0x50587EEE),  # last line (partial 56 bits)
    ],
}

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
    # 大量载荷, 部分 OCR 质量差, 从上下文推断
    # txPyLd (2064 bits), txPyLdC (2432 bits), txPyLdW (2432 bits)
    # 数据过长, 需从标准原文 15841-16101 行提取
}

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
    # 已在 TestTV209 中完成验证
    "txPyLd_val": 0xE5FAEA05,  # 32 bits
    "txPyLdC": (0x9DE61094, 0x9D19EF94),  # 64 bits
    "txPyLdW": (0x7E1E6702, 0x4DB206D2),  # 64 bits
    "txHead_val": 0x2010945B,
    "txHead_hi": 0x4E,
    "txHeadC": (0x93C6E4E4, 0x5C6F4D2B),  # 64 bits
    "txHeadW": (0x23A043D9, 0x147E7C5E),  # 64 bits
}

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
    # 数据过长, 需从标准原文 16140-16269 行提取
}

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
    # 数据过长, 需从标准原文 16270-16515 行提取
}

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
    # 数据过长, 需从标准原文 16516-16799 行提取
}

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
    "wt_seed": 0x43,  # OCR unclear (0000043)
    "txPyLd": [  # 1016 bits = 16 lines (incl. 1st partial)
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
        (0x00416899, None),  # 32 bits only (last word)
    ],
    "txPyLdC": [  # 1016 bits (same content as txPyLd for this TV)
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
    "txPyLdW": [  # 1016 bits (from table)
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
    # txPyLdC tail (from table, 3 lines visible):
    "txPyLdC_tail": [
        (0x22B50C27, 0xBAEA2851),
        (0xA4068391, 0x4028110A),
        (0xC2A7DB00, 0x000000D1),
    ],
    "txPyLdW": [  # 296 bits (from table)
        (0x519120A1, 0x467CAAC6),
        (0x9D245222, 0x99CBB290),
        (0x5F9DD058, 0xD099F244),
        (0xB711D897, 0xC751758B),
        (0x7C33B53F, 0x000000DB),
    ],
}

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
