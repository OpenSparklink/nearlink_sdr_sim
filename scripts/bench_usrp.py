"""USRP 仿真性能基准测试脚本。"""
import cProfile
import pstats
import io
import numpy as np
from nearlink_sdr.sim.usrp_sim import USRPLoopbackSim
from nearlink_sdr.phy.tx_pipeline import TxConfig

sim = USRPLoopbackSim(snr_db=50.0)
payload = b'Hello SLE Benchmark Data Payload!'
cfg = TxConfig(frame_type=2, mcs_index=7)

pr = cProfile.Profile()
pr.enable()
for _ in range(100):
    sim.loopback_mac_data(payload, cfg)
pr.disable()

s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
ps.print_stats(30)
print(s.getvalue())
sim.close()
