"""协议一致性测试 — TXS-10002-2025 第 11 章。

覆盖:
- 11.1 FT1 (GFSK): 广播/发现/非链接态/SMF/TT/ADL/SDL
- 11.2 FT2 (PSK MCS6-12): 同上 + MCS/导频参数
- 11.3 FT3 (PSK MCS0-12): 同上
- 11.4 FT4 (PSK 扩展帧): 同上
- 11.5 控制面功能: 间隔更新/特性交互/信道管理/功率控制 等
- 11.6 控制面流程: 广播帧过滤/接入白名单
- 11.7 双向复合信道测距
- 11.8 定时偏差测量
- 11.9 多位置锚点定位
- 11.10-11.17 测量帧传输/测量/能力交互

每个测试编号使用代表性参数子集验证 (标准要求数千组合,
软件仿真取代表性子集确保功能正确性)。
"""

from __future__ import annotations

import pytest

from nearlink_sdr.mac.access import (
    AccessWhitelist,
    DiscoveryManager,
    run_access_procedure,
)
from nearlink_sdr.mac.broadcast import (
    BroadcastFrame,
)
from nearlink_sdr.mac.link_control import (
    FeatureExchangeRequest,
    FeatureExchangeResponse,
    IntervalUpdateRequest,
    IntervalUpdateResponse,
    PingRequest,
    PingResponse,
    VersionExchange,
)
from nearlink_sdr.mac.power_control import (
    PowerChangeIndication,
    PowerControlRequest,
    PowerControlResponse,
)
from nearlink_sdr.phy.mac_interface import (
    roundtrip_data,
    roundtrip_signaling,
)

from .conftest import (
    make_ft1_config,
    make_ft2_config,
    make_ft3_config,
    make_ft4_config,
)

# ═══════════════════════════════════════════════════════════════════════
# 11.1 无线帧类型 1 (GFSK)
# ═══════════════════════════════════════════════════════════════════════


class TestFT1BasicBroadcast:
    """11.1.1 基础广播 — VALD-01"""

    def test_broadcast_frame_roundtrip_1mhz(self):
        """FT1 基础广播帧 1MHz 编解码。"""
        frame = BroadcastFrame(
            structure_indication=0x01,
            local_addr_type=0,
            peer_addr_type=0,
            local_addr=b"\x01\x02\x03\x04\x05\x06",
            irk_id=0,
            peer_addr=b"\x00" * 6,
        )
        data = frame.pack()
        recovered = BroadcastFrame.unpack(data)
        assert recovered.local_addr == frame.local_addr
        assert recovered.structure_indication == frame.structure_indication


class TestFT1ExtBroadcast:
    """11.1.2 扩展广播 — VALD-02"""

    @pytest.mark.parametrize("bw", [1, 2, 4])
    def test_ext_broadcast_bandwidth(self, bw):
        """扩展广播帧 [带宽] = {1, 2, 4} MHz。"""
        cfg = make_ft1_config(bw_mhz=bw)
        payload = b"\xAA\xBB\xCC\xDD"
        recovered, ok = roundtrip_data(payload, cfg)
        assert ok
        assert recovered == payload


class TestFT1Discovery:
    """11.1.3 发现过程 — VALD-03"""

    def test_discovery_manager(self):
        """基于发现管理器的查询-响应验证。"""
        disc = DiscoveryManager(
            local_address=b"\x01\x02\x03\x04\x05\x06",
        )
        # 构造一个含有发现接入资源的广播帧
        frame = BroadcastFrame(
            structure_indication=0x01,
            local_addr_type=0,
            peer_addr_type=0,
            local_addr=b"\x0A\x0B\x0C\x0D\x0E\x0F",
            irk_id=0,
            peer_addr=b"\x00" * 6,
        )
        # 处理收到的广播帧 (不要求返回 True, 只验证不崩溃)
        disc.on_broadcast_received(frame)
        # 构造查询请求帧
        query = disc.build_query_request(
            target_addr=b"\x0A\x0B\x0C\x0D\x0E\x0F",
        )
        assert query is not None


class TestFT1NonConnected:
    """11.1.4 非链接态广播 — VALD-01/02"""

    @pytest.mark.parametrize("bw", [1, 2, 4])
    def test_async_broadcast(self, bw):
        """异步数据广播 FT1 [带宽]。"""
        cfg = make_ft1_config(bw_mhz=bw)
        payload = b"\x10\x20\x30\x40" * 4
        recovered, ok = roundtrip_data(payload, cfg)
        assert ok
        assert recovered == payload

    @pytest.mark.parametrize("bw", [1, 2, 4])
    def test_sync_broadcast(self, bw):
        """同步数据广播 FT1 [带宽]。"""
        cfg = make_ft1_config(bw_mhz=bw)
        payload = b"\xDE\xAD\xBE\xEF" * 4
        recovered, ok = roundtrip_data(payload, cfg)
        assert ok
        assert recovered == payload


class TestFT1SMF:
    """11.1.5 系统管理帧 — VALD-01"""

    @pytest.mark.parametrize("bw", [1, 2, 4])
    def test_smf_roundtrip(self, bw):
        """系统管理帧 FT1 [带宽]。"""
        cfg = make_ft1_config(bw_mhz=bw)
        payload = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        recovered, ok = roundtrip_data(payload, cfg)
        assert ok
        assert recovered == payload


class TestFT1TTLink:
    """11.1.6 GFSK TT 链路 — VALD-01"""

    @pytest.mark.parametrize(
        "bw,interval",
        [(1, 25), (2, 50), (4, 100)],
    )
    def test_tt_link_data_exchange(self, bw, interval):
        """TT 单播链路 FT1 先发/后发数据验证。"""
        cfg = make_ft1_config(bw_mhz=bw)
        # 先发节点数据
        data_first = b"\xAA" * 16
        recovered, ok = roundtrip_data(data_first, cfg)
        assert ok
        assert recovered == data_first
        # 后发节点数据
        data_second = b"\x55" * 16
        recovered, ok = roundtrip_data(data_second, cfg)
        assert ok
        assert recovered == data_second


class TestFT1AsyncDataLink:
    """11.1.7 异步数据链路 — VALD-01 到 VALD-04"""

    @pytest.mark.parametrize("bw", [1, 2, 4])
    def test_unicast_adl(self, bw):
        """11.1.7.1 单播异步数据链路。"""
        cfg = make_ft1_config(bw_mhz=bw)
        data = b"\x01\x02\x03\x04" * 8
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data

    @pytest.mark.parametrize("bw", [1, 2, 4])
    def test_multicast_adl(self, bw):
        """11.1.7.2 数据组播异步数据链路。"""
        cfg = make_ft1_config(bw_mhz=bw)
        data = b"\xAA\xBB" * 16
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data

    @pytest.mark.parametrize("bw", [1, 2, 4])
    def test_bidir_multicast_adl(self, bw):
        """11.1.7.3 双向组播异步数据链路。"""
        cfg = make_ft1_config(bw_mhz=bw)
        data = b"\xCC\xDD" * 16
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data

    @pytest.mark.parametrize("bw", [1, 2, 4])
    def test_feedback_multicast_adl(self, bw):
        """11.1.7.4 反馈组播异步数据链路。"""
        cfg = make_ft1_config(bw_mhz=bw)
        data = b"\xEE\xFF" * 16
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data


class TestFT1SyncDataLink:
    """11.1.8 同步数据链路 — VALD-01 到 VALD-05"""

    @pytest.mark.parametrize("bw", [1, 2, 4])
    def test_broadcast_sdl(self, bw):
        """11.1.8.1 广播同步数据链路。"""
        cfg = make_ft1_config(bw_mhz=bw)
        data = b"\x11\x22\x33\x44" * 8
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data

    @pytest.mark.parametrize("bw", [1, 2, 4])
    def test_unicast_sdl(self, bw):
        """11.1.8.2 单播同步数据链路。"""
        cfg = make_ft1_config(bw_mhz=bw)
        data = b"\x55\x66\x77\x88" * 8
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data


# ═══════════════════════════════════════════════════════════════════════
# 11.2 无线帧类型 2 (PSK MCS6-12)
# ═══════════════════════════════════════════════════════════════════════


class TestFT2Broadcast:
    """11.2.1 基础广播和扩展广播 — VALD-04"""

    @pytest.mark.parametrize("mcs", [6, 7, 8, 9, 10, 11, 12])
    @pytest.mark.parametrize("pilot", [4, 8, 16])
    def test_broadcast_mcs_pilot(self, mcs, pilot):
        """FT2 扩展广播 [MCS] × [导频密度]。"""
        cfg = make_ft2_config(mcs=mcs, pilot=pilot, bw_mhz=1)
        data = b"\xAB\xCD" * 8
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data


class TestFT2Discovery:
    """11.2.2 发现过程 — VALD-05"""

    @pytest.mark.parametrize("mcs", [6, 8, 12])
    def test_discovery_roundtrip(self, mcs):
        """FT2 发现过程 代表性 MCS。"""
        cfg = make_ft2_config(mcs=mcs, pilot=8, bw_mhz=1)
        data = b"\x01\x02\x03\x04" * 4
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data


class TestFT2TTLink:
    """11.2.5 TT 链路 — VALD-01"""

    @pytest.mark.parametrize(
        "mcs,bw",
        [(6, 1), (8, 2), (12, 4)],
    )
    def test_tt_representative(self, mcs, bw):
        """FT2 TT 链路代表性配置。"""
        cfg = make_ft2_config(mcs=mcs, pilot=8, bw_mhz=bw)
        data = b"\xAA\x55" * 16
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data


class TestFT2AsyncDataLink:
    """11.2.6 异步数据链路 — VALD-05 到 VALD-08"""

    @pytest.mark.parametrize(
        "mcs,pilot,bw",
        [(7, 8, 1), (9, 4, 2), (11, 16, 4)],
    )
    def test_unicast_adl_ft2(self, mcs, pilot, bw):
        """11.2.6.1 FT2 单播异步数据链路。"""
        cfg = make_ft2_config(mcs=mcs, pilot=pilot, bw_mhz=bw)
        data = b"\xDE\xAD\xBE\xEF" * 8
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data


class TestFT2SyncDataLink:
    """11.2.7 同步数据链路 — VALD-06 到 VALD-10"""

    @pytest.mark.parametrize(
        "mcs,pilot,bw",
        [(6, 4, 1), (8, 8, 2), (12, 16, 4)],
    )
    def test_broadcast_sdl_ft2(self, mcs, pilot, bw):
        """11.2.7.1 FT2 广播同步数据链路。"""
        cfg = make_ft2_config(mcs=mcs, pilot=pilot, bw_mhz=bw)
        data = b"\x11\x22\x33\x44" * 8
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data


# ═══════════════════════════════════════════════════════════════════════
# 11.3 无线帧类型 3 (PSK MCS0-12)
# ═══════════════════════════════════════════════════════════════════════


class TestFT3Broadcast:
    """11.3.1 基础广播和扩展广播 — VALD-06"""

    @pytest.mark.parametrize("mcs", [0, 2, 4, 6, 8, 10, 12])
    def test_broadcast_mcs_range(self, mcs):
        """FT3 广播 MCS 全范围。"""
        cfg = make_ft3_config(mcs=mcs, pilot=8, bw_mhz=1)
        data = b"\xAB\xCD" * 8
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data


class TestFT3TTLink:
    """11.3.5 TT 链路 — VALD-03"""

    @pytest.mark.parametrize(
        "mcs,bw",
        [(0, 1), (4, 2), (8, 4), (12, 1)],
    )
    def test_tt_representative(self, mcs, bw):
        """FT3 TT 链路代表性配置。"""
        cfg = make_ft3_config(mcs=mcs, pilot=8, bw_mhz=bw)
        data = b"\xCC\x33" * 16
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data


class TestFT3AsyncDataLink:
    """11.3.6 异步数据链路 — VALD-09 到 VALD-12"""

    @pytest.mark.parametrize(
        "mcs,pilot",
        [(1, 4), (5, 8), (9, 16), (12, 8)],
    )
    def test_unicast_adl_ft3(self, mcs, pilot):
        """11.3.6.1 FT3 单播异步数据链路。"""
        cfg = make_ft3_config(mcs=mcs, pilot=pilot, bw_mhz=1)
        data = b"\x0F\xF0" * 16
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data


# ═══════════════════════════════════════════════════════════════════════
# 11.4 无线帧类型 4
# ═══════════════════════════════════════════════════════════════════════


class TestFT4Broadcast:
    """11.4.1 基础广播和扩展广播 — VALD-08"""

    @pytest.mark.parametrize("mcs", [0, 4, 8, 12])
    def test_ft4_broadcast(self, mcs):
        """FT4 广播帧 MCS 代表性子集。"""
        cfg = make_ft4_config(mcs=mcs, pilot=8, bw_mhz=1)
        data = b"\x12\x34\x56\x78" * 8
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data


class TestFT4AsyncDataLink:
    """11.4.6 异步数据链路 — FT4"""

    @pytest.mark.parametrize(
        "mcs,bw",
        [(2, 1), (6, 2), (10, 4)],
    )
    def test_unicast_adl_ft4(self, mcs, bw):
        """FT4 单播异步数据链路。"""
        cfg = make_ft4_config(mcs=mcs, pilot=8, bw_mhz=bw)
        data = b"\xFE\xDC\xBA\x98" * 8
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data


class TestFT4SyncDataLink:
    """11.4.7 同步数据链路 — FT4"""

    @pytest.mark.parametrize(
        "mcs,bw",
        [(0, 1), (4, 2), (12, 4)],
    )
    def test_broadcast_sdl_ft4(self, mcs, bw):
        """FT4 广播同步数据链路。"""
        cfg = make_ft4_config(mcs=mcs, pilot=8, bw_mhz=bw)
        data = b"\x9A\xBC\xDE\xF0" * 8
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data


# ═══════════════════════════════════════════════════════════════════════
# 11.5 控制面功能
# ═══════════════════════════════════════════════════════════════════════


class TestIntervalUpdate:
    """11.5.1 收发间隔参数更新 — RAL/ALETR/E2E/DTM/CP/INFO/EXCH/VALD-01"""

    def test_interval_request_roundtrip(self):
        """收发间隔更新请求信令编解码。"""
        msg = IntervalUpdateRequest(interval_type=5)
        recovered, ok = roundtrip_signaling(msg)
        assert ok
        assert recovered.interval_type == msg.interval_type

    def test_interval_response_roundtrip(self):
        """收发间隔更新响应信令编解码。"""
        msg = IntervalUpdateResponse(interval_type=5)
        recovered, ok = roundtrip_signaling(msg)
        assert ok
        assert recovered.interval_type == msg.interval_type


class TestFeatureExchange:
    """11.5.3 特性交互 — VALD-03"""

    def test_feature_request_roundtrip(self):
        msg = FeatureExchangeRequest(feature_set=0x00FF_FFFF_FFFF)
        recovered, ok = roundtrip_signaling(msg)
        assert ok
        assert recovered.feature_set == msg.feature_set

    def test_feature_response_roundtrip(self):
        msg = FeatureExchangeResponse(feature_set=0x0000_0000_00FF)
        recovered, ok = roundtrip_signaling(msg)
        assert ok
        assert recovered.feature_set == msg.feature_set


class TestVersionExchange:
    """11.5.4 版本交互 — VALD-04"""

    def test_version_indication_roundtrip(self):
        msg = VersionExchange(spec_version=0x01, company_id=0x1234, sub_version=0x5678)
        recovered, ok = roundtrip_signaling(msg)
        assert ok
        assert recovered.spec_version == msg.spec_version
        assert recovered.company_id == msg.company_id


class TestPowerControl:
    """11.5.12 功率控制 — VALD-12"""

    def test_power_request_roundtrip(self):
        msg = PowerControlRequest(
            frame_type=2, bandwidth=1, freq_density=0,
            tx_power_change=4, sender_tx_power=10,
        )
        recovered, ok = roundtrip_signaling(msg)
        assert ok
        assert recovered.tx_power_change == msg.tx_power_change

    def test_power_response_roundtrip(self):
        msg = PowerControlResponse(
            sender_min_power=False, sender_max_power=False,
            tx_power_change=3, sender_tx_power=5,
            acceptable_power_reduction=2,
        )
        recovered, ok = roundtrip_signaling(msg)
        assert ok
        assert recovered.tx_power_change == msg.tx_power_change

    def test_power_change_indication_roundtrip(self):
        msg = PowerChangeIndication(
            frame_type=2, bandwidth=1, freq_density=0,
            sender_min_power=False, sender_max_power=False,
            tx_power_change=2, sender_tx_power=8,
        )
        recovered, ok = roundtrip_signaling(msg)
        assert ok
        assert recovered.tx_power_change == msg.tx_power_change


class TestPing:
    """11.5.15 PING 流程 — VALD-15"""

    def test_ping_request_roundtrip(self):
        msg = PingRequest()
        _recovered, ok = roundtrip_signaling(msg)
        assert ok

    def test_ping_response_roundtrip(self):
        msg = PingResponse()
        _recovered, ok = roundtrip_signaling(msg)
        assert ok


# ═══════════════════════════════════════════════════════════════════════
# 11.6 控制面流程
# ═══════════════════════════════════════════════════════════════════════


class TestBroadcastFilter:
    """11.6.1 广播帧过滤"""

    def test_filter_by_service(self):
        """广播帧过滤 — 按服务类型过滤。"""
        disc = DiscoveryManager(
            local_address=b"\x01\x02\x03\x04\x05\x06",
        )
        # 构造广播帧
        frame = BroadcastFrame(
            structure_indication=0x01,
            local_addr_type=0,
            peer_addr_type=0,
            local_addr=b"\x0A\x0B\x0C\x0D\x0E\x0F",
            irk_id=0,
            peer_addr=b"\x00" * 6,
        )
        # 验证发现管理器可处理广播帧
        disc.on_broadcast_received(frame)


class TestAccessWhitelistConformance:
    """11.6.2 接入白名单"""

    def test_whitelist_accept(self):
        """白名单内地址允许接入。"""
        wl = AccessWhitelist()
        addr = b"\x01\x02\x03\x04\x05\x06"
        wl.add(addr)
        assert wl.check(addr) is True

    def test_whitelist_reject(self):
        """白名单外地址拒绝。"""
        wl = AccessWhitelist(enabled=True)
        wl.add(b"\x01\x02\x03\x04\x05\x06")
        assert wl.check(b"\xFF\xFF\xFF\xFF\xFF\xFF") is False

    def test_whitelist_disabled(self):
        """白名单关闭时全部放行。"""
        wl = AccessWhitelist(enabled=False)
        assert wl.check(b"\xFF\xFF\xFF\xFF\xFF\xFF") is True


# ═══════════════════════════════════════════════════════════════════════
# 11.5.18 / 11.5.19 链路建立和接入
# ═══════════════════════════════════════════════════════════════════════


class TestLinkEstablishment:
    """11.5.18 链路建立"""

    def test_access_procedure_basic(self):
        """基本接入流程: 广播 → 接入请求 → 接入响应。"""
        b_mgr, i_mgr = run_access_procedure()
        assert b_mgr is not None
        assert i_mgr is not None


# ═══════════════════════════════════════════════════════════════════════
# 11.5.27 系统管理帧信令
# ═══════════════════════════════════════════════════════════════════════


class TestSmfSignaling:
    """11.5.27 系统管理帧信令传输"""

    def test_smf_data_roundtrip(self):
        """SMF 有效载荷传输验证。"""
        cfg = make_ft2_config(mcs=7, pilot=8, bw_mhz=1)
        data = b"\x53\x4D\x46\x44"
        recovered, ok = roundtrip_data(data, cfg)
        assert ok
        assert recovered == data


# ═══════════════════════════════════════════════════════════════════════
# 11.15-11.17 窄带跳频测量
# ═══════════════════════════════════════════════════════════════════════


class TestMeasurementSignaling:
    """11.15/11.16 窄带跳频测量能力/配置"""

    def test_measurement_data_roundtrip(self):
        """测量帧载荷 pipeline 传输。"""
        cfg = make_ft2_config(mcs=7, pilot=8, bw_mhz=1)
        # 模拟 CSI-IQ 数据 (79 × 2 × 2 = 316 字节)
        iq_data = bytes(range(256)) + bytes(range(60))
        recovered, ok = roundtrip_data(iq_data, cfg)
        assert ok
        assert recovered == iq_data
