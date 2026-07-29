//! Biological sensory I/O loop on fixed lattice.
//!
//! Afferent:  host/world features → modality routes → thal/sens/assoc/hipp
//! Efferent:  mind meaning → speech organ motor → acoustic
//! Re-afferent: own speech sound + motor proprio re-enter audio/hid paths
//!
//! NOT next-token generation. Sound is the speech channel.

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const sensory_f = @import("sensory_fixed.zig");
const pathways_f = @import("pathways_fixed.zig");
const speech_f = @import("speech_organ_fixed.zig");
const modulate_f = @import("modulate_fixed.zig");
const inject_f = @import("inject_io_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const Fixed = fixed.Fixed;

pub const BioIoReport = struct {
    ok: bool,
    pathways_ok: bool,
    sensory_bus_ok: bool,
    /// vision inject produced spikes
    afferent_vision_spikes: u32,
    /// audio inject produced spikes
    afferent_audio_spikes: u32,
    /// intero thal drive present
    intero_ok: bool,
    /// meaning → motor → acoustic → re-afferent hear letter
    efferent_roundtrip_ok: bool,
    /// multi-frame syllable motor trajectory length
    syllable_frames: u32,
    hear_correct: u32,
    hear_n: u32,
    hear_top1: f64,
    spikes_total: u32,
};

/// Multi-frame motor trajectory (syllable-ish) — continuous plant motion, not tokens.
pub fn utterSyllable(meaning: []const Fixed, n_frames: usize, motors: []speech_f.Motor, acoustics: []speech_f.Acoustic) usize {
    const n = @min(n_frames, @min(motors.len, acoustics.len));
    if (n == 0) return 0;
    // base gesture
    const base = speech_f.SpeechOrgan.meaningToMotor(meaning);
    var f: usize = 0;
    while (f < n) : (f += 1) {
        var m = base;
        // coarticulation sweep over frames
        const phase = fixed.div(fixed.fromInt(@intCast(f)), fixed.fromInt(@intCast(n)));
        var k: usize = 0;
        while (k < speech_f.MOTOR_N) : (k += 1) {
            const sweep = fixed.mul(phase, fixed.fromDecimalStr("0.15"));
            const sign: Fixed = if ((k + f) % 2 == 0) sweep else fixed.negate(sweep);
            m.ch[k] = fixed.clamp(fixed.add(m.ch[k], sign), fixed.fromInt(-1), fixed.fromInt(1));
        }
        motors[f] = m;
        acoustics[f] = speech_f.SpeechOrgan.motorToAcoustic(m);
    }
    return n;
}

fn meanAcoustic(ac: []const speech_f.Acoustic, out: *speech_f.Acoustic) void {
    var i: usize = 0;
    while (i < speech_f.ACOUSTIC_N) : (i += 1) out.ch[i] = 0;
    if (ac.len == 0) return;
    var f: usize = 0;
    while (f < ac.len) : (f += 1) {
        i = 0;
        while (i < speech_f.ACOUSTIC_N) : (i += 1) {
            out.ch[i] = fixed.add(out.ch[i], ac[f].ch[i]);
        }
    }
    const nf = fixed.fromInt(@intCast(ac.len));
    i = 0;
    while (i < speech_f.ACOUSTIC_N) : (i += 1) out.ch[i] = fixed.div(out.ch[i], nf);
}

fn acousticToFeats(a: speech_f.Acoustic, out: *[8]Fixed) void {
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        out[i] = if (i < speech_f.ACOUSTIC_N) a.ch[i] else fixed.fromDecimalStr("0.1");
    }
}

fn motorToFeats(m: speech_f.Motor, out: *[8]Fixed) void {
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        out[i] = if (i < speech_f.MOTOR_N) m.ch[i] else 0;
    }
}

fn runAfferentEpoch(mod: pathways_f.Modality, feats: []const Fixed, steps: usize) u32 {
    var b = brain_f.BrainF.initSeeded(11, false);
    var bus: sensory_f.BusF = .{};
    bus.push(sensory_f.PacketF.fromSlice(mod, feats, fixed.fromDecimalStr("0.9")));
    bus.metric = .{
        .cpu = fixed.fromDecimalStr("0.15"),
        .mem = fixed.fromDecimalStr("0.2"),
        .disk = fixed.fromDecimalStr("0.05"),
        .net = 0,
        .temp = fixed.fromDecimalStr("0.1"),
    };
    var ext: [brain_f.N_TOTAL]Fixed = undefined;
    const before = b.totalSpikes();
    var t: usize = 0;
    while (t < steps) : (t += 1) {
        bus.buildExternal(&b, fixed.fromInt(1), ext[0..]);
        b.step(ext[0..]);
    }
    return b.totalSpikes() - before;
}

pub fn runBioIoProbe() BioIoReport {
    const pathways_ok = pathways_f.selfTest();
    const sensory_bus_ok = sensory_f.selfTest();

    // --- Afferent: vision / audio ---
    var vfeat: [8]Fixed = undefined;
    var afeat: [8]Fixed = undefined;
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        vfeat[i] = fixed.sub(fixed.div(fixed.fromInt(@intCast((i * 17 + 3) % 100)), fixed.fromInt(50)), fixed.fromInt(1));
        afeat[i] = fixed.sub(fixed.div(fixed.fromInt(@intCast((i * 23 + 9) % 100)), fixed.fromInt(50)), fixed.fromInt(1));
    }
    const v_sp = runAfferentEpoch(.vision, vfeat[0..], 40);
    const a_sp = runAfferentEpoch(.audio, afeat[0..], 40);

    // intero: metric-only bus, check thal drive non-baseline
    var b_int = brain_f.BrainF.initSeeded(5, false);
    var bus_i: sensory_f.BusF = .{};
    bus_i.metric = .{
        .cpu = fixed.fromDecimalStr("0.8"),
        .mem = fixed.fromDecimalStr("0.7"),
        .disk = fixed.fromDecimalStr("0.2"),
        .net = fixed.fromDecimalStr("0.1"),
        .temp = fixed.fromDecimalStr("0.3"),
    };
    var ext_i: [brain_f.N_TOTAL]Fixed = undefined;
    bus_i.buildExternal(&b_int, fixed.fromInt(1), ext_i[0..]);
    var intero_ok = false;
    i = 0;
    while (i < b_int.n) : (i += 1) {
        if (b_int.region_of[i] == .thal and fixed.gt(ext_i[i], fixed.fromDecimalStr("0.05"))) {
            intero_ok = true;
            break;
        }
    }

    // --- Efferent + re-afferent speech loop ---
    var organ: speech_f.SpeechOrgan = .{};
    organ.clear();
    const n_let: usize = 6;
    var meanings: [6][speech_f.MEANING_N]Fixed = undefined;
    var symbols: [6]u32 = undefined;
    const letters = "ABCDEF";
    i = 0;
    while (i < n_let) : (i += 1) {
        var j: usize = 0;
        while (j < speech_f.MEANING_N) : (j += 1) {
            const u: u32 = @as(u32, @intCast(i)) *% 37 +% @as(u32, @intCast(j)) *% 11 +% 5;
            meanings[i][j] = fixed.sub(fixed.div(fixed.fromInt(@intCast(u % 181)), fixed.fromInt(90)), fixed.fromInt(1));
        }
        symbols[i] = @as(u32, letters[i]);
        organ.teachSymbol(symbols[i], meanings[i][0..]);
    }

    const SYL: usize = 4;
    var motors: [SYL]speech_f.Motor = undefined;
    var acoustics: [SYL]speech_f.Acoustic = undefined;
    var hear_ok: u32 = 0;
    i = 0;
    while (i < n_let) : (i += 1) {
        const nf = utterSyllable(meanings[i][0..], SYL, motors[0..], acoustics[0..]);
        var mean_ac: speech_f.Acoustic = .{};
        meanAcoustic(acoustics[0..nf], &mean_ac);

        // re-afferent: own sound into audio path + motor proprio into hid-like
        var brain = brain_f.BrainF.initSeeded(19, false);
        var bus: sensory_f.BusF = .{};
        var a_feats: [8]Fixed = undefined;
        var m_feats: [8]Fixed = undefined;
        acousticToFeats(mean_ac, &a_feats);
        motorToFeats(motors[nf / 2], &m_feats);
        bus.push(sensory_f.PacketF.fromSlice(.speech_sound, a_feats[0..], fixed.fromDecimalStr("0.85")));
        bus.push(sensory_f.PacketF.fromSlice(.motor_proprio, m_feats[0..], fixed.fromDecimalStr("0.5")));
        var ext: [brain_f.N_TOTAL]Fixed = undefined;
        var t: usize = 0;
        while (t < 24) : (t += 1) {
            bus.buildExternal(&brain, fixed.fromInt(1), ext[0..]);
            brain.step(ext[0..]);
        }
        // hear from acoustic (organ), not from LM
        if (organ.hearSymbol(mean_ac) == symbols[i]) hear_ok += 1;
    }

    const hear_n: u32 = @intCast(n_let);
    const hear_top1 = @as(f64, @floatFromInt(hear_ok)) / @as(f64, @floatFromInt(hear_n));
    const efferent_ok = hear_top1 >= 0.75;

    const ok = pathways_ok and sensory_bus_ok and v_sp >= 1 and a_sp >= 1 and intero_ok and efferent_ok;
    return .{
        .ok = ok,
        .pathways_ok = pathways_ok,
        .sensory_bus_ok = sensory_bus_ok,
        .afferent_vision_spikes = v_sp,
        .afferent_audio_spikes = a_sp,
        .intero_ok = intero_ok,
        .efferent_roundtrip_ok = efferent_ok,
        .syllable_frames = SYL,
        .hear_correct = hear_ok,
        .hear_n = hear_n,
        .hear_top1 = hear_top1,
        .spikes_total = v_sp + a_sp,
    };
}
