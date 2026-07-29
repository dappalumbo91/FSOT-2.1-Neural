//! Full connected mind — not a unit-test probe.
//!
//! One organism keeps genetic multi-region brain + episodic memory + speech
//! + live host senses + modulate + symbol assoc + curiosity + teach domains
//! + retrieve recognition + optional speaker DAC.
//!
//! Expanded toward Python continuous-organism capability (still Zig Fixed).

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
const teach_f = @import("teach_fixed.zig");
const self_audio = @import("self_audio_loop.zig");
const pathways_f = @import("pathways_fixed.zig");
const Fixed = fixed.Fixed;

pub const LiveConfig = struct {
    n_ticks: u32 = 600,
    sleep_ms: u32 = 20,
    report_every: u32 = 30,
    speakers: bool = true,
    speak_every: u32 = 40,
    encode_every: u32 = 6,
    curiosity_every: u32 = 12,
    /// inject synthetic multi-domain lessons (Python autonomous/curriculum spirit)
    teach_every: u32 = 40,
    /// close speaker→mic loop (self-voice anchor in noise)
    self_hear: bool = true,
    /// soft match for noisy living rooms (shape, not pure loudness)
    /// soft for noisy rooms (same PCM feature space now)
    self_match_thresh: Fixed = fixed.fromDecimalStr("0.10"),
    /// settle ms after DAC before mic grab (room echo)
    self_hear_settle_ms: u32 = 120,
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
    n_curiosity_q: u32,
    n_symbol_hits: u32,
    n_speaks: u32,
    n_retrieves: u32,
    n_teaches: u32,
    n_self_hear: u32,
    n_self_attempts: u32,
    n_ambient_high: u32,
    last_self_match: f64,
    last_symbol: u32,
    mean_s: f64,
    units: u32,
    n_syn: u32,
    n_pyr: u32,
    n_i: u32,
    spike_rate: f64,
};

fn ampFeats(src: *const [8]Fixed, gain: Fixed, out: *[8]Fixed) void {
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        out[i] = fixed.clamp(fixed.mul(src[i], gain), fixed.fromInt(-1), fixed.fromInt(1));
    }
}

/// Temporal delta so changing display/audio diversifies symbols and memory.
fn deltaFeats(cur: *const [8]Fixed, prev: *const [8]Fixed, out: *[8]Fixed) void {
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        const d = fixed.sub(cur[i], prev[i]);
        out[i] = fixed.clamp(fixed.add(cur[i], fixed.mul(d, fixed.fromDecimalStr("2.0"))), fixed.fromInt(-1), fixed.fromInt(1));
    }
}

pub fn runLiveMind(cfg: LiveConfig) LiveReport {
    var org = organism_f.OrganismF.init();
    org.encode_every = 0;
    org.steps_per_tick = 6; // more neural steps per sense sample
    org.speak_every = 0;

    const st0 = org.brain.structureReport();
    std.debug.print("=== FSOT LIVE MIND (connected organism) ===\n", .{});
    std.debug.print(
        "brain units={d} E={d} I={d} syn={d} Pyr/PV/SST/VIP={d}/{d}/{d}/{d}\n",
        .{ st0.n_units, st0.n_e, st0.n_i, st0.n_synapses, st0.n_pyr, st0.n_pv, st0.n_sst, st0.n_vip },
    );
    std.debug.print(
        "loop ticks={d} sleep_ms={d} encode={d} curiosity={d} teach={d} speakers={}\n",
        .{ cfg.n_ticks, cfg.sleep_ms, cfg.encode_every, cfg.curiosity_every, cfg.teach_every, cfg.speakers },
    );
    std.debug.print("doctrine: senses→routes→brain→memory→curiosity→speech (one organism)\n", .{});

    var n_disp: u32 = 0;
    var n_mic: u32 = 0;
    var n_enc: u32 = 0;
    var n_cur: u32 = 0;
    var n_cur_q: u32 = 0;
    var n_sym: u32 = 0;
    var n_spk: u32 = 0;
    var n_ret: u32 = 0;
    var n_teach: u32 = 0;
    var n_self: u32 = 0;
    var n_self_try: u32 = 0;
    var n_amb: u32 = 0;
    var last_match: f64 = 0;
    var last_sym: u32 = 0;
    var last_vision: [8]Fixed = .{0} ** 8;
    var last_audio: [8]Fixed = .{0} ** 8;
    var prev_vision: [8]Fixed = .{0} ** 8;
    // running self-voice template (anchored when match succeeds — fights room noise over time)
    var self_template: [8]Fixed = .{0} ** 8;
    var has_self_template: bool = false;

    const domains = [_]teach_f.Domain{ .physics_fsot, .biology, .narrative, .learning, .media };
    const who_s = [_][]const u8{ "agent", "pyr", "neo", "learner", "viewer" };
    const what_s = [_][]const u8{ "scalar", "ei", "choice", "probe", "frame" };

    var t: u32 = 0;
    while (t < cfg.n_ticks) : (t += 1) {
        const plant = hardware_f.discoverPlant(org.tick +% 1);
        // Soft plant metric so modulate does not constantly dampen live senses
        var soft = plant.metric;
        if (fixed.gt(soft.cpu, fixed.fromDecimalStr("0.55"))) soft.cpu = fixed.fromDecimalStr("0.45");
        if (fixed.gt(soft.mem, fixed.fromDecimalStr("0.55"))) soft.mem = fixed.fromDecimalStr("0.45");
        org.setMetric(soft);

        var sample: host_f.HostSample = .{};
        host_f.sampleHost(&sample);
        if (sample.live_display) n_disp += 1;
        if (sample.live_mic) n_mic += 1;

        // Amplify plant features so cortical units fire
        var vis_a: [8]Fixed = undefined;
        var aud_a: [8]Fixed = undefined;
        ampFeats(&sample.vision, fixed.fromDecimalStr("1.6"), &vis_a);
        ampFeats(&sample.audio, fixed.fromDecimalStr("1.6"), &aud_a);
        var vis_d: [8]Fixed = undefined;
        deltaFeats(&vis_a, &prev_vision, &vis_d);
        @memcpy(prev_vision[0..], vis_a[0..]);
        @memcpy(last_vision[0..], vis_d[0..]);
        @memcpy(last_audio[0..], aud_a[0..]);

        // Fresh multi-modal bus (do not call setInject — it used to wipe audio)
        org.bus.clear();
        org.bus.metric = soft;
        org.pushSense(.vision, vis_d[0..], fixed.fromDecimalStr("1.15"));
        org.pushSense(.audio, aud_a[0..], fixed.fromDecimalStr("1.05"));
        // mild thalamic wake pulse via metric already on bus
        org.setInjectFeatsOnly(vis_d[0..]);
        org.setMeaning(vis_d[0..]);

        // Symbol on delta-vision for diversity
        const anc = symbol_f.nearestAnchor(&vis_d);
        last_sym = symbol_f.anchorToken(anc);
        n_sym += 1;

        // Mind step
        const before_sp = org.brain.totalSpikes();
        const tick_st = org.tickOnce();
        const win_sp = org.brain.totalSpikes() - before_sp;
        _ = win_sp;

        // --- multi-domain teach card (Python curriculum/autonomous spirit) ---
        if (cfg.teach_every > 0 and (t % cfg.teach_every) == (cfg.teach_every / 2)) {
            const di: usize = @intCast(t / cfg.teach_every % domains.len);
            const card = teach_f.buildLesson(
                domains[di],
                who_s[di],
                what_s[di],
                "host",
                "live",
                "domain_lesson",
                false, // leave WHY empty for curiosity
            );
            var feats: [8]Fixed = undefined;
            var i: usize = 0;
            while (i < 8) : (i += 1) {
                const u: u32 = @as(u32, @intCast(di)) *% 41 +% @as(u32, @intCast(i)) *% 13 +% t;
                feats[i] = fixed.sub(fixed.div(fixed.fromInt(@intCast(u % 181)), fixed.fromInt(90)), fixed.fromInt(1));
            }
            // only who+what filled → curiosity can fill why/where/when/how
            _ = org.store.encode(&org.brain, feats[0..], 0b000011, card.tokens);
            org.last_encode_id = org.store.episodes[org.store.n - 1].id;
            n_teach += 1;
            n_enc += 1;
        }

        // --- episodic encode from LIVE senses: leave empty slots for curiosity ---
        // who=symbol, what=see_hear; why/where/when open (0b000011)
        if (cfg.encode_every > 0 and (t % cfg.encode_every) == (cfg.encode_every - 1)) {
            const tok = [_]u32{
                last_sym,
                memory_f.hashToken("see_hear"),
                0, // why open
                0, // where open
                0, // when open
                0, // how open
            };
            var joint: [8]Fixed = undefined;
            var i: usize = 0;
            while (i < 8) : (i += 1) {
                joint[i] = fixed.add(
                    fixed.mul(last_vision[i], fixed.fromDecimalStr("0.55")),
                    fixed.mul(last_audio[i], fixed.fromDecimalStr("0.45")),
                );
            }
            org.last_encode_id = org.store.encode(&org.brain, joint[0..], 0b000011, tok);
            n_enc += 1;
        }

        // --- curiosity on latest episode ---
        if (cfg.curiosity_every > 0 and org.last_encode_id != 0 and (t % cfg.curiosity_every) == 0) {
            const cur = curiosity_f.runCuriosity(&org.store, org.last_encode_id, @intCast((t / 40) % 6));
            n_cur_q += cur.n_questions;
            if (cur.n_resolved > 0) n_cur += cur.n_resolved;
        }

        // --- retrieve recognition ---
        if (org.store.n >= 2 and (t % 12) == 0) {
            var sim: Fixed = 0;
            const hit = org.store.retrieve(&org.brain, last_vision[0..], &sim);
            if (hit != 0) n_ret += 1;
        }

        // --- speech + speakers + self-hear loop (efference copy vs mic) ---
        if (cfg.speak_every > 0 and (t % cfg.speak_every) == 0) {
            org.speakNow();
            n_spk += 1;
            // Always inject predicted self-sound (corollary discharge) even before mic returns
            var pred_f: [8]Fixed = undefined;
            self_audio.acousticToFeats(org.last_acoustic, &pred_f);
            org.pushSense(.speech_sound, pred_f[0..], fixed.fromDecimalStr("0.95"));
            org.pushSense(.motor_proprio, pred_f[0..], fixed.fromDecimalStr("0.55"));

            if (cfg.speakers) {
                var pcm: [2400]i16 = undefined;
                const n = audio_out.acousticToPcm(org.last_acoustic, pcm[0..]);
                _ = audio_out.playPcm(pcm[0..n]);
            }

            if (cfg.self_hear) {
                n_self_try += 1;
                // let room + speakers settle (echo path)
                if (cfg.self_hear_settle_ms > 0) {
                    std.Thread.sleep(@as(u64, cfg.self_hear_settle_ms) * std.time.ns_per_ms);
                }
                const sh = self_audio.hearSelfAfterSpeak(org.last_acoustic, cfg.self_match_thresh);
                // report best of feature cosine and pcm shape corr
                last_match = @max(fixed.toF64(sh.match), sh.pcm_corr);
                if (sh.ambient_high) n_amb += 1;

                // residual ambient still enters as external audio (noisy living room honesty)
                org.pushSense(.audio, sh.residual[0..], fixed.fromDecimalStr("0.7"));

                if (sh.self_heard) {
                    n_self += 1;
                    // blend into running self-voice template (anchor despite noise)
                    var i: usize = 0;
                    while (i < 8) : (i += 1) {
                        if (has_self_template) {
                            self_template[i] = fixed.add(
                                fixed.mul(self_template[i], fixed.fromDecimalStr("0.7")),
                                fixed.mul(sh.pred[i], fixed.fromDecimalStr("0.3")),
                            );
                        } else {
                            self_template[i] = sh.pred[i];
                        }
                    }
                    has_self_template = true;
                    // episodic: "I heard myself" — who=self, what=voice
                    const tok = [_]u32{
                        memory_f.hashToken("self"),
                        memory_f.hashToken("own_voice"),
                        memory_f.hashToken("reafferent"),
                        0,
                        0,
                        memory_f.hashToken("hear"),
                    };
                    org.last_encode_id = org.store.encode(&org.brain, pred_f[0..], 0b100111, tok);
                    n_enc += 1;
                    // teach speech organ bind: self sound ↔ self token
                    org.speech.teachSymbol(memory_f.hashToken("self"), pred_f[0..]);
                } else if (has_self_template) {
                    // fight noise: re-inject known self template weakly so identity holds
                    org.pushSense(.speech_sound, self_template[0..], fixed.fromDecimalStr("0.4"));
                }
            }
        }

        if (cfg.report_every > 0 and ((t + 1) % cfg.report_every) == 0) {
            const sp_now = org.brain.totalSpikes();
            std.debug.print(
                "mind t={d}/{d} meanS={e} spikes+={d} total_sp={d} eps={d} enc={d} cur={d}/{d} ret={d} teach={d} spk={d} self={d}/{d} match={e} amb={d} live_d={} live_m={} mod={s} sym={d}\n",
                .{
                    t + 1,
                    cfg.n_ticks,
                    fixed.toF64(tick_st.mean_s),
                    tick_st.spikes,
                    sp_now,
                    tick_st.episodes,
                    n_enc,
                    n_cur,
                    n_cur_q,
                    n_ret,
                    n_teach,
                    n_spk,
                    n_self,
                    n_self_try,
                    last_match,
                    n_amb,
                    sample.live_display,
                    sample.live_mic,
                    @import("modulate_fixed.zig").modeName(org.last_mod.mode),
                    anc,
                },
            );
        }

        if (cfg.sleep_ms > 0) {
            std.Thread.sleep(@as(u64, cfg.sleep_ms) * std.time.ns_per_ms);
        }
    }

    const st = org.brain.structureReport();
    const spikes = org.brain.totalSpikes();
    const rate = @as(f64, @floatFromInt(spikes)) / @as(f64, @floatFromInt(cfg.n_ticks));
    // Gates: live plant + memory + curiosity/teach cognitive work (+ spikes if plant drives them)
    const ok = org.store.n >= 8 and n_enc >= 4 and n_cur_q >= 4 and n_ret >= 2 and (spikes >= 8 or n_cur >= 4);
    std.debug.print(
        "LIVE_MIND ticks={d} spikes={d} rate={e}/tick eps={d} encodes={d} cur_res={d} cur_q={d} ret={d} teach={d} speaks={d} self_hear={d}/{d} amb_high={d} live_d={d} live_m={d}\n",
        .{ cfg.n_ticks, spikes, rate, org.store.n, n_enc, n_cur, n_cur_q, n_ret, n_teach, n_spk, n_self, n_self_try, n_amb, n_disp, n_mic },
    );
    std.debug.print(
        "LIVE_MIND brain units={d} syn={d} meanS={e} last_self_match={e} self_template={}\n",
        .{ st.n_units, st.n_synapses, fixed.toF64(org.brain.meanS()), last_match, has_self_template },
    );
    std.debug.print("SELF_AUDIO: efference_copy+mic match; residual=room (noisy living room expected)\n", .{});
    return .{
        .ok = ok,
        .ticks = cfg.n_ticks,
        .spikes = spikes,
        .episodes = @intCast(org.store.n),
        .n_live_disp = n_disp,
        .n_live_mic = n_mic,
        .n_encodes = n_enc,
        .n_curiosity = n_cur,
        .n_curiosity_q = n_cur_q,
        .n_symbol_hits = n_sym,
        .n_speaks = n_spk,
        .n_retrieves = n_ret,
        .n_teaches = n_teach,
        .n_self_hear = n_self,
        .n_self_attempts = n_self_try,
        .n_ambient_high = n_amb,
        .last_self_match = last_match,
        .last_symbol = last_sym,
        .mean_s = fixed.toF64(org.brain.meanS()),
        .units = @intCast(st.n_units),
        .n_syn = st.n_synapses,
        .n_pyr = st.n_pyr,
        .n_i = st.n_i,
        .spike_rate = rate,
    };
}
