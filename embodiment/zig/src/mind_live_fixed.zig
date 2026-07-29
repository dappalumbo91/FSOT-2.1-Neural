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
// speech_f also used for gestureName / N_GESTURES in reports
const self_audio = @import("self_audio_loop.zig");
const pathways_f = @import("pathways_fixed.zig");
const scene_f = @import("ambient_scene_fixed.zig");
const attention_f = @import("attention_fixed.zig");
const eeg = @import("eeg_gate_anchors_fixed.zig");
const machine_lang = @import("machine_lang_fixed.zig");
const lexicon_en = @import("lexicon_en_fixed.zig");
const host_tts = @import("host_tts_fixed.zig");
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
    /// soft match for noisy living rooms — default from EEG sensory residual
    self_match_thresh: Fixed = eeg.selfMatchThreshAir(),
    /// settle ms after DAC before mic grab (room echo)
    self_hear_settle_ms: u32 = 120,
    /// English lexicon + TTS plant (machine language → real words)
    english_tts: bool = true,
    /// keep formant acoustic plant (optional; language out is TTS)
    formant_speech: bool = true,
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
    n_self_air: u32,
    n_self_internal: u32,
    n_self_attempts: u32,
    n_ambient_high: u32,
    n_noise_ignored: u32,
    n_scene_samples: u32,
    n_encode_open: u32,
    n_speech_adapt: u32,
    n_pattern_binds: u32,
    n_machine_emit: u32,
    n_machine_bytes: u32,
    n_english_say: u32,
    n_tts_spoken: u32,
    last_self_match: f64,
    last_attune: f64,
    last_bias_mag: f64,
    last_pattern: u32,
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
    std.debug.print("doctrine: senses→scene→attention→routes→brain→memory→curiosity→speech\n", .{});
    // EEG / experiment anchors (not free parameters)
    const ar = eeg.report();
    std.debug.print(
        "EEG_ANCHORS θconc/rel={e} α={e} γcsv={e} sens={e} studyS={e} enc_drive={e} fig={e} gnd={e} self_thr={e} nov_floor={e} SME θ↑={} γ↑={}\n",
        .{
            ar.theta_conc_relax,
            ar.alpha_conc_relax,
            ar.gamma_conc_relax,
            ar.sensory_strength,
            ar.study_s,
            ar.encode_drive,
            ar.figure_gain,
            ar.ground_gain,
            ar.self_match_thresh,
            ar.novelty_floor,
            ar.sme_theta_gt,
            ar.sme_gamma_gt,
        },
    );
    std.debug.print(
        "EEG_SRC mental-state.csv concentrate vs relax + Sederberg2003 SME + FSOT couple (0 free params)\n",
        .{},
    );

    var scene = scene_f.SceneAnalyzer.init();
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
    var n_self_air: u32 = 0;
    var n_self_int: u32 = 0;
    var n_self_try: u32 = 0;
    var n_amb: u32 = 0;
    var n_noise_ign: u32 = 0;
    var n_enc_open: u32 = 0;
    var n_pat_bind: u32 = 0;
    var n_mach: u32 = 0;
    var n_mach_bytes: u32 = 0;
    var n_en: u32 = 0;
    var n_tts: u32 = 0;
    var last_match: f64 = 0;
    var last_phrase: [80]u8 = .{0} ** 80;
    var last_phrase_n: usize = 0;
    var last_attune: f64 = 0;
    var last_bias: f64 = 0;
    var last_pat: u32 = 0;
    var last_mode: []const u8 = "rest";
    var last_sym: u32 = 0;
    var last_vision: [8]Fixed = .{0} ** 8;
    var last_audio: [8]Fixed = .{0} ** 8;
    var prev_vision: [8]Fixed = .{0} ** 8;
    // running self-voice template (anchored when match succeeds — fights room noise over time)
    var self_template: [8]Fixed = .{0} ** 8;
    var has_self_template: bool = false;
    var last_meaning: Fixed = 0;
    var last_attn = attention_f.attune(0, 0, 0, 0);

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

        // --- quiet-tick ambient scene (not during speak ticks) ---
        const is_speak_tick = cfg.speak_every > 0 and (t % cfg.speak_every) == 0;
        if (!is_speak_tick and (t % 3) == 0) {
            var amb_mic: [8]Fixed = undefined;
            if (scene_f.captureMicFeats(&amb_mic)) {
                scene.observeAmbient(&amb_mic);
            } else {
                // host sample audio still teaches baseline when mic capture busy
                scene.observeAmbient(&aud_a);
            }
        }

        // Filter world audio: strip baseline + known noise classes → figure path
        var aud_clean: [8]Fixed = undefined;
        const filt = scene.filterMic(&aud_a, &aud_clean);
        if (filt.ignored) n_noise_ign += 1;
        @memcpy(last_audio[0..], aud_clean[0..]);

        // Symbol on delta-vision for diversity (meaning seed for attention)
        const anc = symbol_f.nearestAnchor(&vis_d);
        last_sym = symbol_f.anchorToken(anc);
        n_sym += 1;
        // meaning proxy: later overwritten by retrieve sim when available
        last_meaning = fixed.fromDecimalStr("0.2"); // symbol present

        // Pre-tick attention on scene (self_match updated after speak)
        last_attn = attention_f.attune(
            filt.novelty,
            if (filt.ignored) filt.suppressed else fixed.mul(filt.suppressed, fixed.fromDecimalStr("0.4")),
            if (has_self_template) fixed.fromDecimalStr("0.15") else 0,
            last_meaning,
        );
        last_attune = fixed.toF64(last_attn.attune);
        last_mode = attention_f.modeName(last_attn.mode);
        if (last_attn.encode_open) n_enc_open += 1;

        // Fresh multi-modal bus (do not call setInject — it used to wipe audio)
        org.bus.clear();
        org.bus.metric = soft;
        org.pushSense(.vision, vis_d[0..], fixed.fromDecimalStr("1.15"));
        // figure audio at attended gain; if ignored ground, weak residual only
        const aud_gain = if (filt.ignored) last_attn.ground_gain else last_attn.figure_gain;
        org.pushSense(.audio, aud_clean[0..], aud_gain);
        // mild thalamic wake pulse via metric already on bus
        org.setInjectFeatsOnly(vis_d[0..]);
        org.setMeaning(vis_d[0..]);

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
        // SME doctrine: prefer encode when attention encode_open (study vs rest)
        if (cfg.encode_every > 0 and (t % cfg.encode_every) == (cfg.encode_every - 1)) {
            const force_or_attend = last_attn.encode_open or (t % (cfg.encode_every * 3) == (cfg.encode_every - 1));
            if (force_or_attend) {
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
            if (hit != 0) {
                n_ret += 1;
                last_meaning = fixed.clamp(sim, 0, fixed.fromInt(1));
            }
        }

        // --- machine language + English lexicon (choose words → TTS) ---
        // Native: TritWord frame. Translation: English dictionary. Plant: OS TTS.
        if (is_speak_tick) {
            // meaning from live vision+audio (what the mind is attending)
            var meaning: [8]Fixed = undefined;
            var mi: usize = 0;
            while (mi < 8) : (mi += 1) {
                meaning[mi] = fixed.add(
                    fixed.mul(last_vision[mi], fixed.fromDecimalStr("0.55")),
                    fixed.mul(last_audio[mi], fixed.fromDecimalStr("0.45")),
                );
            }
            org.setMeaning(meaning[0..]);

            var phrase: [lexicon_en.MAX_PHRASE]u8 = undefined;
            var frame: machine_lang.MachineFrame = .{};
            const ut = lexicon_en.utterEnglish(&meaning, phrase[0..], &frame);
            n_en += 1;
            last_phrase_n = @min(ut.phrase_n, last_phrase.len);
            @memcpy(last_phrase[0..last_phrase_n], phrase[0..last_phrase_n]);

            // machine frame bytes + self-ingest
            var mraw: [machine_lang.MAX_FRAME_BYTES]u8 = undefined;
            const nb = frame.toBytes(mraw[0..]);
            n_mach += 1;
            n_mach_bytes += @intCast(nb);
            var mfeats: [8]Fixed = undefined;
            _ = machine_lang.understandToFeatures(&frame, &mfeats);
            org.pushSense(.text, mfeats[0..], fixed.fromDecimalStr("1.0"));
            org.pushSense(.custom, mfeats[0..], fixed.fromDecimalStr("0.8"));

            const mtok_ep = [_]u32{
                memory_f.hashToken("self"),
                memory_f.hashToken("english"),
                memory_f.hashToken("say"),
                @as(u32, @truncate(frame.words[0].pack)),
                0,
                memory_f.hashToken("phrase"),
            };
            org.last_encode_id = org.store.encode(&org.brain, mfeats[0..], 0b100111, mtok_ep);
            n_enc += 1;

            // TTS plant — real English words out the speakers
            if (cfg.english_tts and ut.phrase_n > 0) {
                const tr = host_tts.speakEnglish(phrase[0..ut.phrase_n]);
                if (tr.spoken) n_tts += 1;
            }

            if ((t / cfg.speak_every) < 4 or ((t + 1) % cfg.report_every) == 0) {
                var hex: [64]u8 = undefined;
                const hl = machine_lang.frameToHex(mraw[0..@min(nb, 24)], hex[0..]);
                std.debug.print(
                    "EN_SAY t={d} \"{s}\" | MACHINE words={d} bytes={d} hex={s}\n",
                    .{ t, phrase[0..ut.phrase_n], frame.n_words, nb, hex[0..hl] },
                );
            }
        }

        // --- optional formant speech plant (bio acoustic; language path is TTS) ---
        if (is_speak_tick and cfg.formant_speech) {
            org.speakNow();
            n_spk += 1;
            // Always inject predicted self-sound (corollary discharge) even before mic returns
            var pred_f: [8]Fixed = undefined;
            self_audio.acousticToFeats(org.last_acoustic, &pred_f);
            const sp_scale = attention_f.speechInjectScale(&last_attn);
            org.pushSense(.speech_sound, pred_f[0..], sp_scale);
            org.pushSense(.motor_proprio, pred_f[0..], fixed.mul(sp_scale, fixed.fromDecimalStr("0.58")));

            // Formant DAC only if English TTS is off (avoid double-talk on same speakers)
            if (cfg.speakers and !cfg.english_tts) {
                var pcm: [audio_out.PCM_MAX]i16 = undefined;
                const n = audio_out.acousticToPcm(org.last_acoustic, pcm[0..]);
                _ = audio_out.playPcm(pcm[0..n]);
            }

            if (cfg.self_hear) {
                n_self_try += 1;
                // let room + speakers settle (echo path)
                if (cfg.self_hear_settle_ms > 0) {
                    std.Thread.sleep(@as(u64, cfg.self_hear_settle_ms) * std.time.ns_per_ms);
                }
                const sh = self_audio.hearSelfAfterSpeak(org.last_acoustic, cfg.self_match_thresh, &scene);
                // report best of feature cosine and pcm shape corr
                last_match = @max(fixed.toF64(sh.match), sh.pcm_corr);
                if (sh.ambient_high) n_amb += 1;
                if (sh.noise_ignored) n_noise_ign += 1;
                if (sh.self_heard_internal) n_self_int += 1;
                if (sh.self_heard_air) n_self_air += 1;

                // Re-attune with self-match + residual novelty after scene clean
                const ign = if (sh.noise_ignored) fixed.fromDecimalStr("0.75") else fixed.fromDecimalStr("0.2");
                last_attn = attention_f.attune(
                    self_audio.energy(&sh.residual),
                    ign,
                    sh.match,
                    last_meaning,
                );
                last_attune = fixed.toF64(last_attn.attune);
                last_mode = attention_f.modeName(last_attn.mode);
                if (last_attn.encode_open) n_enc_open += 1;

                // residual world at ground gain (kids/room honesty, selectively ignored)
                org.pushSense(.audio, sh.residual[0..], last_attn.ground_gain);

                // --- adapt speech motor from residual (next utter retunes) ---
                org.adaptSpeechFromHear(&sh.residual, sh.match, sh.self_heard_air);
                last_bias = fixed.toF64(org.speech.biasMagnitude());
                last_pat = org.speech.lastPatternId();

                // Internal self always updates template from *what we played* (bone-like)
                // Air match strengthens it further when room allows
                {
                    const blend = if (sh.self_heard_air) fixed.fromDecimalStr("0.45") else fixed.fromDecimalStr("0.25");
                    const keep = fixed.sub(fixed.fromInt(1), blend);
                    var i: usize = 0;
                    while (i < 8) : (i += 1) {
                        if (has_self_template) {
                            self_template[i] = fixed.add(fixed.mul(self_template[i], keep), fixed.mul(sh.pred[i], blend));
                        } else {
                            self_template[i] = sh.pred[i];
                        }
                    }
                    has_self_template = true;
                }

                if (sh.self_heard) {
                    n_self += 1;
                    const what = if (sh.self_heard_air) memory_f.hashToken("own_voice_air") else memory_f.hashToken("own_voice_internal");
                    const tok = [_]u32{
                        memory_f.hashToken("self"),
                        what,
                        memory_f.hashToken("reafferent"),
                        0,
                        0,
                        memory_f.hashToken("hear"),
                    };
                    org.last_encode_id = org.store.encode(&org.brain, pred_f[0..], 0b100111, tok);
                    n_enc += 1;
                    org.speech.teachSymbol(memory_f.hashToken("self"), pred_f[0..]);

                    // bind this gesture family as a distinct sound↔motor (16-tone inventory)
                    const gname = speech_f.gestureName(last_pat);
                    const before_binds = org.speech.n;
                    org.speech.teachSymbol(memory_f.hashToken(gname), pred_f[0..]);
                    if (org.speech.n > before_binds) n_pat_bind += 1;

                    const ptok = [_]u32{
                        memory_f.hashToken("self"),
                        memory_f.hashToken(gname),
                        memory_f.hashToken("gesture"),
                        0,
                        0,
                        memory_f.hashToken("speak"),
                    };
                    _ = org.store.encode(&org.brain, pred_f[0..], 0b100111, ptok);
                    n_enc += 1;
                }
                // Always keep self template on bus (identity under chaos) at speech inject scale
                if (has_self_template) {
                    org.pushSense(.speech_sound, self_template[0..], fixed.mul(sp_scale, fixed.fromDecimalStr("0.5")));
                }
            }
        }

        if (cfg.report_every > 0 and ((t + 1) % cfg.report_every) == 0) {
            const sp_now = org.brain.totalSpikes();
            std.debug.print(
                "mind t={d}/{d} meanS={e} spikes+={d} total_sp={d} eps={d} enc={d} cur={d}/{d} ret={d} teach={d} spk={d} self={d}/{d} air={d} int={d} match={e} amb={d} ign={d} att={e} mode={s} adapt={d} bias={e} pat={d} src={d} live_d={} live_m={} mod={s} sym={d}\n",
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
                    n_self_air,
                    n_self_int,
                    last_match,
                    n_amb,
                    n_noise_ign,
                    last_attune,
                    last_mode,
                    org.speech.n_adapt,
                    last_bias,
                    last_pat,
                    scene.last_match_src,
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
    last_bias = fixed.toF64(org.speech.biasMagnitude());
    last_pat = org.speech.lastPatternId();
    std.debug.print(
        "LIVE_MIND ticks={d} spikes={d} rate={e}/tick eps={d} encodes={d} cur_res={d} cur_q={d} ret={d} teach={d} speaks={d} self={d}/{d} air={d} int={d} amb_high={d} ign={d} scene={d} enc_open={d} live_d={d} live_m={d}\n",
        .{ cfg.n_ticks, spikes, rate, org.store.n, n_enc, n_cur, n_cur_q, n_ret, n_teach, n_spk, n_self, n_self_try, n_self_air, n_self_int, n_amb, n_noise_ign, scene.n_samples, n_enc_open, n_disp, n_mic },
    );
    std.debug.print(
        "LIVE_MIND brain units={d} syn={d} meanS={e} last_self_match={e} attune={e} mode={s} self_template={} noise_src={d}\n",
        .{ st.n_units, st.n_synapses, fixed.toF64(org.brain.meanS()), last_match, last_attune, last_mode, has_self_template, scene.last_match_src },
    );
    std.debug.print(
        "SPEECH_ADAPT n_adapt={d} bias_mag={e} gesture={d}/{d} name={s} pattern_binds={d} speech_binds={d}\n",
        .{ org.speech.n_adapt, last_bias, last_pat, speech_f.N_GESTURES, speech_f.gestureName(last_pat), n_pat_bind, org.speech.n },
    );
    std.debug.print(
        "MACHINE_LANG emits={d} total_bytes={d} | ENGLISH says={d} tts_spoken={d}\n",
        .{ n_mach, n_mach_bytes, n_en, n_tts },
    );
    if (last_phrase_n > 0) {
        std.debug.print("LAST_ENGLISH \"{s}\"\n", .{last_phrase[0..last_phrase_n]});
    }
    std.debug.print("SELF_AUDIO: int=bone-like reafference; air=scene-filtered mic; ignore=habituation on known noise\n", .{});
    std.debug.print("ATTENTION: figure=novelty×(1-ignore) + self + meaning; encode gate = SME study path (EEG θ)\n", .{});
    std.debug.print("TALK: machine frame (native) → English lexicon (choose) → TTS (real words)\n", .{});
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
        .n_self_air = n_self_air,
        .n_self_internal = n_self_int,
        .n_self_attempts = n_self_try,
        .n_ambient_high = n_amb,
        .n_noise_ignored = n_noise_ign,
        .n_scene_samples = scene.n_samples,
        .n_encode_open = n_enc_open,
        .n_speech_adapt = org.speech.n_adapt,
        .n_pattern_binds = n_pat_bind,
        .n_machine_emit = n_mach,
        .n_machine_bytes = n_mach_bytes,
        .n_english_say = n_en,
        .n_tts_spoken = n_tts,
        .last_self_match = last_match,
        .last_attune = last_attune,
        .last_bias_mag = last_bias,
        .last_pattern = last_pat,
        .last_symbol = last_sym,
        .mean_s = fixed.toF64(org.brain.meanS()),
        .units = @intCast(st.n_units),
        .n_syn = st.n_synapses,
        .n_pyr = st.n_pyr,
        .n_i = st.n_i,
        .spike_rate = rate,
    };
}
