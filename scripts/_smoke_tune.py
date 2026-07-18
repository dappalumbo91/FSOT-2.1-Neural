import torch
from fsot_nuron.neuron_batch import FSOTNeuronBatch, NeuronConfig
from fsot_nuron.validate import run_validation
from fsot_nuron.reservoir import FluidReservoir, ReservoirConfig

for pat in ["rest", "random", "periodic", "constant", "fi_step"]:
    n = FSOTNeuronBatch(NeuronConfig(n_units=8), device="cpu")
    h = n.run(1000, stimulus_pattern=pat, record=True)
    print(
        f"{pat:10s} rate={float(h['firing_rate_Hz'].mean()):6.2f} "
        f"spikes={float(h['spike_count'].float().mean()):5.1f} "
        f"maxS={float(h['S'].max()):.2f}"
    )

r = run_validation(n_units=64, steps=1000, device="cpu", use_api=False)
print("--- ALLEN VALIDATION ---")
ev, sp = r["evoked"], r["spontaneous"]
print(
    "EVOKED rate",
    round(ev["population"]["mean_firing_rate_Hz"], 2),
    "adapt",
    round(ev["population"]["mean_adaptation_index"], 3),
    "ISI",
    ev["population"]["mean_isi_ms"],
)
print("EVOKED band", ev["bands"]["pass_rate"], [(x["metric"], x["value"], x["in_band"]) for x in ev["bands"]["rows"]])
print("SPONT rate", round(sp["population"]["mean_firing_rate_Hz"], 2), "cv", sp["population"]["mean_isi_cv"])
print("SPONT band", sp["bands"]["pass_rate"], [(x["metric"], x["value"], x["in_band"]) for x in sp["bands"]["rows"]])
print("PER", round(r["periodic"]["population"]["mean_firing_rate_Hz"], 2))
print("ISI rel_err", r["comparison_to_allen_sample"]["isi_rel_error"])
print("adapt rel_err", r["comparison_to_allen_sample"]["adaptation_rel_error"])
print("REST", r["rest"]["bands"]["pass_rate"], r["rest"]["population"].get("configured_vrest_mV"))

res = FluidReservoir(ReservoirConfig(n_units=32, device="cpu"))
stim = torch.zeros(500)
for t in range(500):
    stim[t] = 0.8 if (t % 80 < 20) else 0.1
out = res.run_sequence(stim)
print(
    "RES rate",
    round(float(out["firing_rate_Hz"].mean()), 2),
    "enc/mid/dec mean spikes",
    round(float(res.enc.spike_count.float().mean()), 1),
    round(float(res.mid.spike_count.float().mean()), 1),
    round(float(res.dec.spike_count.float().mean()), 1),
)
