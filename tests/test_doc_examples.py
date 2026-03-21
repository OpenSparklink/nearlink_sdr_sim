"""示例工程持久化测试。

导入并执行 examples/ 下所有示例函数, 验证对应文档代码始终可用。
每个测试函数对应一个示例工程中的可调用函数。
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# 动态导入 examples/ 目录下的模块
# ---------------------------------------------------------------------------

_EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _import_example(name: str):
    """按文件名导入 examples/ 下的 Python 模块。"""
    path = _EXAMPLES_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"examples.{name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# examples/getting_started.py
# ---------------------------------------------------------------------------


class TestGettingStarted:

    @pytest.fixture(autouse=True)
    def _load(self):
        self.mod = _import_example("getting_started")

    def test_gfsk_link(self):
        ber = self.mod.gfsk_link()
        assert isinstance(ber, (float, np.floating))
        assert ber < 0.1

    def test_polar_psk_link(self):
        errors, K = self.mod.polar_psk_link()
        assert errors < K

    def test_pipeline_sim(self):
        result = self.mod.pipeline_sim()
        assert "snr_db" in result
        assert "ber" in result
        assert "fer" in result

    def test_node_basic(self):
        channel, stats = self.mod.node_basic()
        assert isinstance(channel, int)
        assert isinstance(stats, dict)


# ---------------------------------------------------------------------------
# examples/qos_management.py
# ---------------------------------------------------------------------------


class TestQosManagement:

    @pytest.fixture(autouse=True)
    def _load(self):
        self.mod = _import_example("qos_management")

    def test_basic_workflow(self):
        from nearlink_sdr.mac.qos import TxDecision
        decision, fields = self.mod.qos_basic_workflow()
        assert decision == TxDecision.NEW_DATA
        assert "tx_sn" in fields

    def test_arq(self):
        arq = self.mod.arq_usage()
        assert arq.frame_type == 3

    def test_harq(self):
        mask = self.mod.harq_usage()
        assert isinstance(mask, int)

    def test_quality_tracker(self):
        adj, mcs = self.mod.quality_tracker()
        assert adj in (-1, 0, 1)
        assert isinstance(mcs, int)

    def test_flow_control(self):
        bit, paused = self.mod.flow_control()
        assert bit == 1
        assert paused is False

    def test_tx_queue(self):
        from nearlink_sdr.mac.qos import Priority
        item = self.mod.tx_queue()
        assert item is not None
        assert item.priority == Priority.CONTROL
        assert item.data == b"ctrl"


# ---------------------------------------------------------------------------
# examples/node_usage.py
# ---------------------------------------------------------------------------


class TestNodeUsage:

    @pytest.fixture(autouse=True)
    def _load(self):
        self.mod = _import_example("node_usage")

    def test_create_node(self):
        from nearlink_sdr.node import NodeRole
        node = self.mod.create_node()
        assert node.config.role == NodeRole.G_NODE

    def test_connection_lifecycle(self):
        broadcaster, scanner = self.mod.connection_lifecycle()
        assert broadcaster is not None
        assert scanner is not None

    def test_data_transfer(self):
        tx_result = self.mod.data_transfer()
        assert tx_result is not None

    def test_pairing_encryption(self):
        msgs = self.mod.pairing_encryption()
        assert isinstance(msgs, list)

    def test_event_callback(self):
        from nearlink_sdr.node import NodeCallback
        cls = self.mod.event_callback()
        assert issubclass(cls, NodeCallback)

    def test_hopping(self):
        channel = self.mod.hopping()
        assert isinstance(channel, int)

    def test_power_control(self):
        pwr = self.mod.power_control()
        assert isinstance(pwr, float)

    def test_advertising(self):
        bcast = self.mod.advertising()
        assert bcast is not None

    def test_measurement(self):
        sig = self.mod.measurement_signal()
        assert len(sig) > 0

    def test_mcs_adaptive(self):
        suggested = self.mod.mcs_adaptive()
        assert isinstance(suggested, int)

    def test_node_stats(self):
        s = self.mod.node_stats()
        assert "state" in s
        assert "tx_count" in s

    def test_disconnect_reset(self):
        node = self.mod.disconnect_reset()
        assert node is not None


# ---------------------------------------------------------------------------
# examples/run_simulation.py (轻量级快速测试)
# ---------------------------------------------------------------------------


class TestRunSimulation:

    @pytest.fixture(autouse=True)
    def _load(self):
        self.mod = _import_example("run_simulation")

    def test_ber_gfsk(self):
        result = self.mod.ber_gfsk()
        assert "snr_db" in result and "ber" in result

    def test_ber_psk(self):
        result = self.mod.ber_psk()
        assert "snr_db" in result

    def test_polar_coded_ber(self):
        result = self.mod.polar_coded_ber()
        assert "snr_db" in result

    def test_channel_model(self):
        rx = self.mod.channel_model()
        assert len(rx) > 0

    def test_hopping_sequence(self):
        seq = self.mod.hopping_sequence()
        assert len(seq) == 100

    def test_pipeline_ft2(self):
        result = self.mod.pipeline_ft2()
        assert "ber" in result and "fer" in result

    def test_pipeline_other_ft(self):
        r1, r4 = self.mod.pipeline_other_ft()
        assert "ber" in r1
        assert "ber" in r4

    def test_node_hopping_link(self):
        result = self.mod.node_hopping_link()
        assert "fer" in result

    def test_node_access_flow(self):
        result = self.mod.node_access_flow()
        assert isinstance(result, dict)

    def test_node_channel_sweep(self):
        result = self.mod.node_channel_sweep()
        assert "snr_db" in result

    def test_node_power_adapt(self):
        result = self.mod.node_power_adapt()
        assert "fer" in result

    def test_doppler_interference(self):
        r_dop, r_sir, r_mp = self.mod.doppler_interference()
        assert "doppler_hz" in r_dop and "fer" in r_dop
        assert "sir_db" in r_sir and "fer" in r_sir
        assert "doppler_hz" in r_mp and "fer" in r_mp


# ---------------------------------------------------------------------------
# examples/custom_modulation.py
# ---------------------------------------------------------------------------


class TestCustomModulation:

    def test_modulator_class(self):
        mod = _import_example("custom_modulation")
        m = mod.MyModulator(sps=4)
        assert m.sps == 4
        d = mod.MyDemodulator(sps=4)
        assert d.sps == 4
