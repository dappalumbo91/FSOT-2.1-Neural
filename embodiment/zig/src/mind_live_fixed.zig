//! Full connected mind — not a unit-test probe.
//!
//! One organism keeps:
//!   genetic multi-region brain + episodic memory + speech organ
//!   + live host senses (display/mic) + plant modulate + symbol assoc
//!   + periodic curiosity + optional speaker DAC
//!
//! This is the product "intelligence is online" loop. Finite probes stay separate.

const std = @import("std");
const fixed = @import("fixed.zig");
const organism_f = @import("organism_fixed.zig");
const host_f = @import("host_senses_fixed.zig");
const hardware_f = @import("hardware_metric_fixed.zig");
const curiosity_f = @import("curiosity_fixed.zig");
const symbol_f = @import("symbol_assoc_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const speech_f = @import("speech_organ_fixed.zig");
const audio_out = @import("host_audio_out_fixed.zig");
const pathways_f = @import("pathways_fixed.zig");
const Fixed = fixed.Fixed;

pub const LiveConfig = struct {
    /// wall ticks (each = sample + mind step). 0 = default 600 (~12s @20ms)
    n_ticks: u32 = 600,
    sleep_ms: u32 = 20,
    report_every: u32 = 30,
    /// play speech organ through speakers occasionally
    speakers: bool = true,
    speak_every: u32 = 40,
    encode_every: u32 = 8,
    curiosity_every: u32 = 25,
};

pub const LiveReport = struct {
    ok: bool,
    ticks: u32,
    spikes: u32,
    episodes: u32,
    n_live_disp: u32,
    n_live_mic: u32,
    n_encodes: u32,
    n_curiosity: u32,
    n_symbol_hits: u32,
    n_speaks: u32,
    n_retrieves: u32,
    last_symbol: u32,
    mean_s: f64,
    units: u32,
    n_syn: u32,
    n_pyr: u32,
    n_i: u32,
};

pub fn runLiveMind(cfg: LiveConfig) LiveReport {
    var org = organism_f.OrganismF.init();
    org.encode_every = 0; // we encode explicitly from live features
    org.steps_per_tick = 4;
    org.speak_every = 0; // explicit speak below (with optional DAC)

    const st0 = org.brain.structureReport();
    std.debug.print("=== FSOT LIVE MIND (connected organism) ===\n", .{});
    std.debug.print(
        "brain units={d} E={d} I={d} syn={d} Pyr/PV/SST/VIP={d}/{d}/{d}/{d}\n",
        .{ st0.n_units, st0.n_e, st0.n_i, st0.n_synapses, st0.n_pyr, st0.n_pv, st0.n_sst, st0.n_vip },
    );
    std.debug.print(
        "loop ticks={d} sleep_ms={d} encode_every={d} curiosity_every={d} speakers={}\n",
        .{ cfg.n_ticks, cfg.sleep_ms, cfg.encode_every, cfg.curiosity_every, cfg.speakers },
    );
    std.debug.print("doctrine: one organism; senses→routes→brain→memory→speech; not disconnected unit tests\n", .{});

    var n_disp: u32 = 0;
    var n_mic: u32 = 0;
    var n_enc: u32 = 0;
    var n_cur: u32 = 0;
    var n_sym: u32 = 0;
    var n_spk: u32 = 0;
    var n_ret: u32 = 0;
    var last_sym: u32 = 0;
    var last_vision: [8]Fixed = .{0} ** 8;
    var last_audio: [8]Fixed = .{0} ** 8;

    var t: u32 = 0;
    while (t < cfg.n_ticks) : (t += 1) {
        // --- plant + senses ---
        const plant = hardware_f.discoverPlant(org.tick +% 1);
        org.setMetric(plant.metric);

        var sample: host_f.HostSample = .{};
        host_f.sampleHost(&sample);
        if (sample.live_display) n_disp += 1;
        if (sample.live_mic) n_mic += 1;
        @memcpy(last_vision[0..], sample.vision[0..]);
        @memcpy(last_audio[0..], sample.audio[0..]);

        // clear bus each cycle so senses stay current (not stale packets only)
        org.bus.clear();
        org.bus.metric = plant.metric;
        org.pushSense(.vision, sample.vision[0..], fixed.fromDecimalStr("0.9"));
        org.pushSense(.audio, sample.audio[0..], fixed.fromDecimalStr("0.8"));
        org.setInject(sample.vision[0..]); // also legacy inject path for encode feats
        org.setMeaning(sample.vision[0..]);

        // --- symbol association on live vision (prototype anchors) ---
        const anc = symbol_f.nearestAnchor(&sample.vision);
        last_sym = symbol_f.anchorToken(anc);
        n_sym += 1;

        // --- mind step ---
        const tick_st = org.tickOnce();

        // --- episodic encode from LIVE features (who=symbol, what=vision-event) ---
        if (cfg.encode_every > 0 and (t % cfg.encode_every) == (cfg.encode_every - 1)) {
            const tok = [_]u32{
                last_sym,
                memory_f.hashToken("see_hear"),
                memory_f.hashToken("live"),
                0,
                0,
                memory_f.hashToken("organism"),
            };
            // joint-ish feats for memory
            var joint: [8]Fixed = undefined;
            var i: usize = 0;
            while (i < 8) : (i += 1) {
                joint[i] = fixed.add(
                    fixed.mul(last_vision[i], fixed.fromDecimalStr("0.6")),
                    fixed.mul(last_audio[i], fixed.fromDecimalStr("0.4")),
                );
            }
            org.last_encode_id = org.store.encode(&org.brain, joint[0..], 0b100111, tok);
            n_enc += 1;
        }

        // --- curiosity fill on latest episode ---
        if (cfg.curiosity_every > 0 and org.last_encode_id != 0 and (t % cfg.curiosity_every) == 0) {
            const cur = curiosity_f.runCuriosity(&org.store, org.last_encode_id, 2);
            if (cur.n_resolved > 0) n_cur += 1;
        }

        // --- retrieve: can we recognize current vision in memory? ---
        if (org.store.n >= 2 and (t % 15) == 0) {
            var sim: Fixed = 0;
            const hit = org.store.retrieve(&org.brain, last_vision[0..], &sim);
            if (hit != 0) n_ret += 1;
        }

        // --- speech plant + optional speakers ---
        if (cfg.speak_every > 0 and (t % cfg.speak_every) == 0) {
            org.speakNow();
            n_spk += 1;
            if (cfg.speakers) {
                var pcm: [1600]i16 = undefined; // ~100ms
                const n = audio_out.acousticToPcm(org.last_acoustic, pcm[0..]);
                _ = audio_out.playPcm(pcm[0..n]); // best-effort
            }
        }

        if (cfg.report_every > 0 and ((t + 1) % cfg.report_every) == 0) {
            const br = org.brain.structureReport();
            std.debug.print(
                "mind t={d}/{d} meanS={e} spikes+={d} eps={d} enc={d} cur={d} ret={d} spk={d} live_d={} live_m={} mod={s} sym={d} syn={d}\n",
                .{
                    t + 1,
                    cfg.n_ticks,
                    fixed.toF64(tick_st.mean_s),
                    tick_st.spikes,
                    tick_st.episodes,
                    n_enc,
                    n_cur,
                    n_ret,
                    n_spk,
                    sample.live_display,
                    sample.live_mic,
                    @import("modulate_fixed.zig").modeName(org.last_mod.mode),
                    anc,
                    br.n_synapses,
                },
            );
        }

        if (cfg.sleep_ms > 0) {
            std.Thread.sleep(@as(u64, cfg.sleep_ms) * std.time.ns_per_ms);
        }
    }

    const st = org.brain.structureReport();
    const ok = org.brain.totalSpikes() >= 1 and org.store.n >= 1 and n_enc >= 1;
    std.debug.print(
        "LIVE_MIND ticks={d} spikes={d} eps={d} encodes={d} curiosity={d} retrieves={d} speaks={d} live_d={d} live_m={d}\n",
        .{ cfg.n_ticks, org.brain.totalSpikes(), org.store.n, n_enc, n_cur, n_ret, n_spk, n_disp, n_mic },
    );
    std.debug.print(
        "LIVE_MIND brain still units={d} syn={d} meanS={e}\n",
        .{ st.n_units, st.n_synapses, fixed.toF64(org.brain.meanS()) },
    );
    return .{
        .ok = ok,
        .ticks = cfg.n_ticks,
        .spikes = org.brain.totalSpikes(),
        .episodes = @intCast(org.store.n),
        .n_live_disp = n_disp,
        .n_live_mic = n_mic,
        .n_encodes = n_enc,
        .n_curiosity = n_cur,
        .n_symbol_hits = n_sym,
        .n_speaks = n_spk,
        .n_retrieves = n_ret,
        .last_symbol = last_sym,
        .mean_s = fixed.toF64(org.brain.meanS()),
        .units = @intCast(st.n_units),
        .n_syn = st.n_synapses,
        .n_pyr = st.n_pyr,
        .n_i = st.n_i,
    };
}
