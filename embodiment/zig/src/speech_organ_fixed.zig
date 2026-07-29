//! Speech / linguistics organ — SEPARATE from mind authority core.
//!
//! Doctrine (not LLM next-token generation):
//!   meaning (concept features from mind)
//!     → articulatory motor (tongue / jaw / lips / larynx / breath)
//!     → acoustic signature (sound of the utterance)
//!     → optional orthography (letters / alphabet as *associated* symbols)
//!
//! Humans do not think by emitting token IDs. They move the vocal tract;
//! listeners map sound ↔ meaning; writing is a later symbolic layer on sound.
//! This organ is that translation plant. The mind remains fixed lattice dynamics.

const fixed = @import("fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const Fixed = fixed.Fixed;

/// Articulatory degrees of freedom (simplified vocal tract).
pub const MOTOR_N: usize = 5;
/// Acoustic observation channels (formant / envelope proxies).
pub const ACOUSTIC_N: usize = 6;
/// Concept feature width (aligned with memory inject).
pub const MEANING_N: usize = 8;

pub const Motor = struct {
    /// tongue anterior–posterior, tongue height, jaw open, lip rounding, larynx pitch
    ch: [MOTOR_N]Fixed = .{0} ** MOTOR_N,
};

pub const Acoustic = struct {
    /// f0, F1, F2, rms, spectral tilt proxy, duration energy
    ch: [ACOUSTIC_N]Fixed = .{0} ** ACOUSTIC_N,
};

pub const SymbolBind = struct {
    /// orthographic / alphabet id (e.g. hash of letter) — NOT a next-token stream
    symbol: u32 = 0,
    motor: Motor = .{},
    acoustic: Acoustic = .{},
    meaning: [MEANING_N]Fixed = .{0} ** MEANING_N,
    valid: bool = false,
};

pub const MAX_BINDS: usize = 32;

pub const SpeechOrgan = struct {
    binds: [MAX_BINDS]SymbolBind = undefined,
    n: usize = 0,

    pub fn clear(self: *SpeechOrgan) void {
        self.n = 0;
    }

    /// Meaning → motor (plant): seed-lawful map, not a language model head.
    pub fn meaningToMotor(meaning: []const Fixed) Motor {
        var m: Motor = .{};
        var i: usize = 0;
        while (i < MOTOR_N) : (i += 1) {
            // blend concept dims into articulators
            const a = if (meaning.len > 0) meaning[i % meaning.len] else 0;
            const b = if (meaning.len > i + 1) meaning[(i + 3) % meaning.len] else a;
            // tongue/jaw-ish mix with φ scaling
            const mix = fixed.add(fixed.mul(a, fixed.fromDecimalStr("0.55")), fixed.mul(b, fixed.fromDecimalStr("0.35")));
            const bias = fixed.div(fixed.mul(seeds_f.phi, fixed.fromInt(@intCast(i + 1))), fixed.fromInt(20));
            m.ch[i] = fixed.clamp(fixed.add(mix, bias), fixed.fromInt(-1), fixed.fromInt(1));
        }
        return m;
    }

    /// Motor → acoustic (forward model of tract → sound).
    pub fn motorToAcoustic(motor: Motor) Acoustic {
        var a: Acoustic = .{};
        // f0 ~ larynx
        a.ch[0] = fixed.add(fixed.fromDecimalStr("0.2"), fixed.mul(motor.ch[4], fixed.fromDecimalStr("0.5")));
        // F1 ~ jaw open + tongue height inverse
        a.ch[1] = fixed.add(fixed.mul(motor.ch[2], fixed.fromDecimalStr("0.6")), fixed.mul(motor.ch[1], fixed.fromDecimalStr("-0.35")));
        // F2 ~ tongue anterior
        a.ch[2] = fixed.add(fixed.mul(motor.ch[0], fixed.fromDecimalStr("0.7")), fixed.mul(motor.ch[3], fixed.fromDecimalStr("0.2")));
        // rms ~ |jaw| + |larynx|
        a.ch[3] = fixed.add(fixed.abs(motor.ch[2]), fixed.mul(fixed.abs(motor.ch[4]), fixed.fromDecimalStr("0.5")));
        // tilt ~ lip round
        a.ch[4] = motor.ch[3];
        // duration energy proxy
        a.ch[5] = fixed.add(fixed.fromDecimalStr("0.3"), fixed.mul(fixed.abs(motor.ch[1]), fixed.fromDecimalStr("0.4")));
        return a;
    }

    /// Full utter: meaning → motor → sound (one gesture, not a token sequence).
    pub fn utter(meaning: []const Fixed) struct { motor: Motor, acoustic: Acoustic } {
        const motor = meaningToMotor(meaning);
        return .{ .motor = motor, .acoustic = motorToAcoustic(motor) };
    }

    /// Teach: bind orthographic symbol to this sound (and its motor).
    /// Writing/reading path: sound ↔ letter association (alphabet as secondary).
    pub fn teachSymbol(self: *SpeechOrgan, symbol: u32, meaning: []const Fixed) void {
        if (self.n >= MAX_BINDS) return;
        const u = utter(meaning);
        var b: SymbolBind = .{
            .symbol = symbol,
            .motor = u.motor,
            .acoustic = u.acoustic,
            .valid = true,
        };
        var i: usize = 0;
        while (i < MEANING_N and i < meaning.len) : (i += 1) b.meaning[i] = meaning[i];
        self.binds[self.n] = b;
        self.n += 1;
    }

    fn acousticDist(a: Acoustic, b: Acoustic) Fixed {
        var s: Fixed = 0;
        var i: usize = 0;
        while (i < ACOUSTIC_N) : (i += 1) {
            const d = fixed.sub(a.ch[i], b.ch[i]);
            s = fixed.add(s, fixed.mul(d, d));
        }
        return s;
    }

    /// Hear: acoustic only → nearest taught symbol (tutor-ablated orthography).
    pub fn hearSymbol(self: *const SpeechOrgan, acoustic: Acoustic) u32 {
        if (self.n == 0) return 0;
        var best: usize = 0;
        var best_d: Fixed = acousticDist(acoustic, self.binds[0].acoustic);
        var j: usize = 1;
        while (j < self.n) : (j += 1) {
            const d = acousticDist(acoustic, self.binds[j].acoustic);
            if (fixed.lt(d, best_d)) {
                best_d = d;
                best = j;
            }
        }
        return self.binds[best].symbol;
    }

    /// Acoustic → nearest meaning features (comprehension without letters).
    pub fn hearMeaning(self: *const SpeechOrgan, acoustic: Acoustic, out: *[MEANING_N]Fixed) bool {
        if (self.n == 0) return false;
        var best: usize = 0;
        var best_d: Fixed = acousticDist(acoustic, self.binds[0].acoustic);
        var j: usize = 1;
        while (j < self.n) : (j += 1) {
            const d = acousticDist(acoustic, self.binds[j].acoustic);
            if (fixed.lt(d, best_d)) {
                best_d = d;
                best = j;
            }
        }
        var i: usize = 0;
        while (i < MEANING_N) : (i += 1) out[i] = self.binds[best].meaning[i];
        return true;
    }
};

/// Seed meaning for a letter index (A=0…) — concept prior, not a text token stream.
fn letterMeaning(idx: u32, out: *[MEANING_N]Fixed) void {
    var i: usize = 0;
    while (i < MEANING_N) : (i += 1) {
        const u: u32 = idx *% 37 +% @as(u32, @intCast(i)) *% 11 +% 5;
        const a: i64 = @intCast(u % 181);
        out[i] = fixed.sub(fixed.div(fixed.fromInt(a), fixed.fromInt(90)), fixed.fromInt(1));
    }
}

const LETTERS = "ABCDEFGH"; // small alphabet probe (motor–sound–letter)

pub const SpeechReport = struct {
    ok: bool,
    n_letters: u32,
    /// hear acoustic → correct letter
    hear_correct: u32,
    hear_top1: f64,
    /// re-utter from meaning → acoustic still matches letter
    roundtrip_correct: u32,
    roundtrip_top1: f64,
    doctrine: []const u8 = "motor→sound→symbol; not next-token",
};

pub fn runSpeechOrganProbe() SpeechReport {
    var organ: SpeechOrgan = .{};
    organ.clear();

    const n_letters: usize = 8;
    var meanings: [8][MEANING_N]Fixed = undefined;
    var symbols: [8]u32 = undefined;

    var i: usize = 0;
    while (i < n_letters) : (i += 1) {
        letterMeaning(@intCast(i), &meanings[i]);
        // symbol = letter code (A,B,…) — orthography layer
        symbols[i] = @as(u32, LETTERS[i]);
        organ.teachSymbol(symbols[i], meanings[i][0..]);
    }

    // Test 1: produce sound from meaning, hear letter (no letter in cue)
    var hear_ok: u32 = 0;
    i = 0;
    while (i < n_letters) : (i += 1) {
        const u = SpeechOrgan.utter(meanings[i][0..]);
        // slight acoustic noise (listener channel)
        var heard = u.acoustic;
        heard.ch[3] = fixed.add(heard.ch[3], fixed.fromDecimalStr("0.02"));
        const sym = organ.hearSymbol(heard);
        if (sym == symbols[i]) hear_ok += 1;
    }

    // Test 2: motor path round-trip identity under re-utter
    var rt_ok: u32 = 0;
    i = 0;
    while (i < n_letters) : (i += 1) {
        const u = SpeechOrgan.utter(meanings[i][0..]);
        const sym = organ.hearSymbol(u.acoustic);
        if (sym == symbols[i]) rt_ok += 1;
    }

    const nf: f64 = @floatFromInt(n_letters);
    const hear_top1 = @as(f64, @floatFromInt(hear_ok)) / nf;
    const rt_top1 = @as(f64, @floatFromInt(rt_ok)) / nf;
    // above chance 1/8
    const ok = hear_top1 >= 0.75 and rt_top1 >= 0.875;
    return .{
        .ok = ok,
        .n_letters = @intCast(n_letters),
        .hear_correct = hear_ok,
        .hear_top1 = hear_top1,
        .roundtrip_correct = rt_ok,
        .roundtrip_top1 = rt_top1,
    };
}

pub fn selfTest() bool {
    return runSpeechOrganProbe().ok;
}
