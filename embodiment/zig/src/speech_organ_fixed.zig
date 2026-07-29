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
/// Acoustic observation channels (rich enough for multi-tone PCM).
/// 0 f0  1 F1  2 F2  3 rms  4 tilt  5 duration  6 F3/noise  7 pitch_glide
pub const ACOUSTIC_N: usize = 8;
/// Concept feature width (aligned with memory inject).
pub const MEANING_N: usize = 8;
/// Distinct gesture / tone families (audibly different before real words).
pub const N_GESTURES: usize = 16;

pub const Motor = struct {
    /// tongue anterior–posterior, tongue height, jaw open, lip rounding, larynx pitch
    ch: [MOTOR_N]Fixed = .{0} ** MOTOR_N,
};

pub const Acoustic = struct {
    /// f0, F1, F2, rms, tilt, duration, F3/noise, pitch glide (−1..1 each)
    ch: [ACOUSTIC_N]Fixed = .{0} ** ACOUSTIC_N,
};

/// Human-readable gesture family names (sound inventory, not word tokens).
pub const GESTURE_NAMES = [_][]const u8{
    "low_hum",     // deep drone
    "high_chirp",  // short high peep
    "vowel_ah",    // open /a/-like
    "vowel_ee",    // front /i/-like
    "vowel_oo",    // rounded /u/-like
    "rise_call",   // pitch up glide
    "fall_call",   // pitch down glide
    "staccato",    // short punch
    "long_drone",  // sustained mid
    "fricative",   // noisy airy
    "pulse_2",     // two-beat
    "warm_mid",    // soft mid formants
    "bright_ping", // bright short
    "growl_low",   // low rough
    "siren_up",    // long rising
    "whisper_soft",// quiet tilt-heavy
};

pub const SymbolBind = struct {
    /// orthographic / alphabet id (e.g. hash of letter) — NOT a next-token stream
    symbol: u32 = 0,
    motor: Motor = .{},
    acoustic: Acoustic = .{},
    meaning: [MEANING_N]Fixed = .{0} ** MEANING_N,
    valid: bool = false,
};

pub const MAX_BINDS: usize = 48;

pub const SpeechOrgan = struct {
    binds: [MAX_BINDS]SymbolBind = undefined,
    n: usize = 0,
    /// Online articulatory bias from auditory feedback (self-hear residual).
    /// Biological: speaker adapts motor plan so air-heard sound matches intended.
    motor_bias: Motor = .{},
    /// How many adaptation steps applied
    n_adapt: u32 = 0,
    /// Last air-path match after adapt
    last_air_match: Fixed = 0,
    /// Running pattern index for multi-gesture exploration
    pattern_i: u32 = 0,

    pub fn clear(self: *SpeechOrgan) void {
        self.n = 0;
        self.motor_bias = .{};
        self.n_adapt = 0;
        self.last_air_match = 0;
        self.pattern_i = 0;
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

    /// Apply online motor_bias (learned from self-hear).
    pub fn applyBias(self: *const SpeechOrgan, motor: Motor) Motor {
        var m = motor;
        var i: usize = 0;
        while (i < MOTOR_N) : (i += 1) {
            m.ch[i] = fixed.clamp(fixed.add(m.ch[i], self.motor_bias.ch[i]), fixed.fromInt(-1), fixed.fromInt(1));
        }
        return m;
    }

    /// Motor → acoustic (forward model of tract → multi-tone sound).
    pub fn motorToAcoustic(motor: Motor) Acoustic {
        var a: Acoustic = .{};
        // f0 ~ larynx (wider range for distinct tones)
        a.ch[0] = fixed.clamp(
            fixed.add(fixed.mul(motor.ch[4], fixed.fromDecimalStr("0.85")), fixed.fromDecimalStr("0.05")),
            fixed.fromInt(-1),
            fixed.fromInt(1),
        );
        // F1 ~ jaw open + tongue height inverse
        a.ch[1] = fixed.clamp(
            fixed.add(fixed.mul(motor.ch[2], fixed.fromDecimalStr("0.75")), fixed.mul(motor.ch[1], fixed.fromDecimalStr("-0.4"))),
            fixed.fromInt(-1),
            fixed.fromInt(1),
        );
        // F2 ~ tongue anterior + lip
        a.ch[2] = fixed.clamp(
            fixed.add(fixed.mul(motor.ch[0], fixed.fromDecimalStr("0.8")), fixed.mul(motor.ch[3], fixed.fromDecimalStr("0.25"))),
            fixed.fromInt(-1),
            fixed.fromInt(1),
        );
        // rms ~ |jaw| + |larynx| + |tongue|
        a.ch[3] = fixed.clamp(
            fixed.add(
                fixed.add(fixed.abs(motor.ch[2]), fixed.mul(fixed.abs(motor.ch[4]), fixed.fromDecimalStr("0.55"))),
                fixed.mul(fixed.abs(motor.ch[0]), fixed.fromDecimalStr("0.25")),
            ),
            0,
            fixed.fromInt(1),
        );
        // tilt ~ lip round
        a.ch[4] = motor.ch[3];
        // duration ~ tongue height + jaw (open long vowels vs short)
        a.ch[5] = fixed.clamp(
            fixed.add(fixed.mul(motor.ch[1], fixed.fromDecimalStr("0.45")), fixed.mul(motor.ch[2], fixed.fromDecimalStr("0.35"))),
            fixed.fromInt(-1),
            fixed.fromInt(1),
        );
        // F3 / noise mix ~ lip + tongue height (fricative-ish when high)
        a.ch[6] = fixed.clamp(
            fixed.add(fixed.mul(motor.ch[3], fixed.fromDecimalStr("0.4")), fixed.mul(motor.ch[1], fixed.fromDecimalStr("0.5"))),
            fixed.fromInt(-1),
            fixed.fromInt(1),
        );
        // pitch glide ~ larynx residual vs jaw (call contour)
        a.ch[7] = fixed.clamp(
            fixed.sub(motor.ch[4], fixed.mul(motor.ch[2], fixed.fromDecimalStr("0.35"))),
            fixed.fromInt(-1),
            fixed.fromInt(1),
        );
        return a;
    }

    /// Hard motor targets for 16 audibly distinct gesture families.
    /// Values in milli-units (−1000..1000) so Fixed has no free float knobs at runtime.
    pub fn gestureMotor(id: u32) Motor {
        // tongue_ap, tongue_h, jaw, lip, larynx
        const table = [_][MOTOR_N]i64{
            .{ 0, -200, 150, 100, -850 }, // low_hum
            .{ 300, 400, -200, -100, 900 }, // high_chirp
            .{ 100, -500, 850, 100, 50 }, // vowel_ah
            .{ 850, 700, 200, -300, 250 }, // vowel_ee
            .{ -700, 200, 250, 850, -100 }, // vowel_oo
            .{ 200, 100, 300, 0, 550 }, // rise_call
            .{ 200, 100, 300, 0, -350 }, // fall_call
            .{ 0, 500, 600, 200, 400 }, // staccato
            .{ 0, -300, 200, 150, 0 }, // long_drone
            .{ 500, 850, -100, -400, 200 }, // fricative
            .{ 300, 0, 550, 100, 150 }, // pulse_2
            .{ -200, -100, 350, 350, -150 }, // warm_mid
            .{ 600, 550, -150, -200, 750 }, // bright_ping
            .{ -300, -400, 450, 200, -750 }, // growl_low
            .{ 150, 200, 250, 50, 350 }, // siren_up
            .{ 100, 300, -350, 550, 100 }, // whisper_soft
        };
        const g = id % N_GESTURES;
        var m: Motor = .{};
        var i: usize = 0;
        while (i < MOTOR_N) : (i += 1) {
            m.ch[i] = fixed.fromRatio(table[g][i], 1000);
        }
        return m;
    }

    /// Gesture-specific acoustic overrides (contour / noise / duration extremes).
    fn applyGestureStyle(gid: u32, a: *Acoustic) void {
        switch (gid % N_GESTURES) {
            0 => { // low_hum: long, low glide flat
                a.ch[0] = fixed.fromDecimalStr("-0.85");
                a.ch[5] = fixed.fromDecimalStr("0.75");
                a.ch[7] = fixed.fromDecimalStr("0.05");
                a.ch[6] = fixed.fromDecimalStr("-0.3");
            },
            1 => { // high_chirp: short high
                a.ch[0] = fixed.fromDecimalStr("0.9");
                a.ch[5] = fixed.fromDecimalStr("-0.75");
                a.ch[7] = fixed.fromDecimalStr("0.35");
                a.ch[3] = fixed.fromDecimalStr("0.7");
            },
            2 => { // ah open
                a.ch[1] = fixed.fromDecimalStr("0.85");
                a.ch[2] = fixed.fromDecimalStr("0.15");
                a.ch[5] = fixed.fromDecimalStr("0.45");
            },
            3 => { // ee front
                a.ch[1] = fixed.fromDecimalStr("-0.35");
                a.ch[2] = fixed.fromDecimalStr("0.9");
                a.ch[5] = fixed.fromDecimalStr("0.35");
            },
            4 => { // oo rounded
                a.ch[1] = fixed.fromDecimalStr("-0.25");
                a.ch[2] = fixed.fromDecimalStr("-0.7");
                a.ch[4] = fixed.fromDecimalStr("0.85");
                a.ch[5] = fixed.fromDecimalStr("0.4");
            },
            5 => { // rise
                a.ch[7] = fixed.fromDecimalStr("0.9");
                a.ch[5] = fixed.fromDecimalStr("0.55");
                a.ch[0] = fixed.fromDecimalStr("-0.15");
            },
            6 => { // fall
                a.ch[7] = fixed.fromDecimalStr("-0.9");
                a.ch[5] = fixed.fromDecimalStr("0.55");
                a.ch[0] = fixed.fromDecimalStr("0.45");
            },
            7 => { // staccato
                a.ch[5] = fixed.fromDecimalStr("-0.85");
                a.ch[3] = fixed.fromDecimalStr("0.85");
                a.ch[7] = 0;
            },
            8 => { // long drone
                a.ch[5] = fixed.fromDecimalStr("0.95");
                a.ch[3] = fixed.fromDecimalStr("0.45");
                a.ch[7] = fixed.fromDecimalStr("0.05");
            },
            9 => { // fricative
                a.ch[6] = fixed.fromDecimalStr("0.95");
                a.ch[3] = fixed.fromDecimalStr("0.55");
                a.ch[5] = fixed.fromDecimalStr("0.2");
            },
            10 => { // pulse_2 — duration mid; PCM will dip mid
                a.ch[5] = fixed.fromDecimalStr("0.5");
                a.ch[3] = fixed.fromDecimalStr("0.7");
                a.ch[7] = fixed.fromDecimalStr("0.15");
            },
            11 => { // warm mid
                a.ch[1] = fixed.fromDecimalStr("0.25");
                a.ch[2] = fixed.fromDecimalStr("0.1");
                a.ch[4] = fixed.fromDecimalStr("0.35");
                a.ch[5] = fixed.fromDecimalStr("0.4");
            },
            12 => { // bright ping
                a.ch[0] = fixed.fromDecimalStr("0.75");
                a.ch[2] = fixed.fromDecimalStr("0.7");
                a.ch[5] = fixed.fromDecimalStr("-0.65");
                a.ch[3] = fixed.fromDecimalStr("0.75");
            },
            13 => { // growl
                a.ch[0] = fixed.fromDecimalStr("-0.8");
                a.ch[6] = fixed.fromDecimalStr("0.55");
                a.ch[5] = fixed.fromDecimalStr("0.5");
                a.ch[3] = fixed.fromDecimalStr("0.65");
            },
            14 => { // siren long rise
                a.ch[7] = fixed.fromDecimalStr("0.95");
                a.ch[5] = fixed.fromDecimalStr("0.95");
                a.ch[0] = fixed.fromDecimalStr("-0.4");
                a.ch[3] = fixed.fromDecimalStr("0.6");
            },
            else => { // whisper
                a.ch[3] = fixed.fromDecimalStr("0.2");
                a.ch[6] = fixed.fromDecimalStr("0.7");
                a.ch[4] = fixed.fromDecimalStr("0.6");
                a.ch[5] = fixed.fromDecimalStr("0.35");
            },
        }
    }

    /// Full utter: meaning → motor → sound (one gesture, not a token sequence).
    pub fn utter(meaning: []const Fixed) struct { motor: Motor, acoustic: Acoustic } {
        const motor = meaningToMotor(meaning);
        return .{ .motor = motor, .acoustic = motorToAcoustic(motor) };
    }

    /// Utter with this organ's adapted motor bias (plant self-tune).
    pub fn utterAdapted(self: *const SpeechOrgan, meaning: []const Fixed) struct { motor: Motor, acoustic: Acoustic } {
        const base = meaningToMotor(meaning);
        const motor = self.applyBias(base);
        return .{ .motor = motor, .acoustic = motorToAcoustic(motor) };
    }

    /// Next inventory gesture: hard tone family + light seed color + bias.
    /// This is the main speak path — 16 distinct sounds to adapt against.
    pub fn utterNextGesture(self: *SpeechOrgan, seed_meaning: []const Fixed) struct { motor: Motor, acoustic: Acoustic, gesture_id: u32 } {
        const gid: u32 = self.pattern_i % @as(u32, N_GESTURES);
        self.pattern_i +%= 1;

        var motor = gestureMotor(gid);
        // light seed influence so mind meaning still tints the tract
        var i: usize = 0;
        while (i < MOTOR_N) : (i += 1) {
            const seed = if (seed_meaning.len > 0) seed_meaning[i % seed_meaning.len] else 0;
            motor.ch[i] = fixed.clamp(
                fixed.add(motor.ch[i], fixed.mul(seed, fixed.fromDecimalStr("0.12"))),
                fixed.fromInt(-1),
                fixed.fromInt(1),
            );
        }
        motor = self.applyBias(motor);
        var ac = motorToAcoustic(motor);
        applyGestureStyle(gid, &ac);
        return .{ .motor = motor, .acoustic = ac, .gesture_id = gid };
    }

    /// Fill meaning features from current gesture motor (for memory / teach).
    pub fn patternMeaning(self: *SpeechOrgan, seed_meaning: []const Fixed, out: *[MEANING_N]Fixed) void {
        const gid: u32 = self.pattern_i % @as(u32, N_GESTURES);
        // peek only — utterNextGesture advances pattern_i
        const m = gestureMotor(gid);
        var i: usize = 0;
        while (i < MEANING_N) : (i += 1) {
            const seed = if (i < seed_meaning.len) seed_meaning[i] else 0;
            const motor_v = if (i < MOTOR_N) m.ch[i] else 0;
            out[i] = fixed.clamp(
                fixed.add(fixed.mul(motor_v, fixed.fromDecimalStr("0.85")), fixed.mul(seed, fixed.fromDecimalStr("0.15"))),
                fixed.fromInt(-1),
                fixed.fromInt(1),
            );
        }
    }

    /// Auditory feedback adaptation (not volume war).
    /// residual_feats: cleaned residual after self-cancel (8 feats).
    /// air_match: cosine/pcm self-hear score.
    /// air_heard: air path confirmed.
    ///
    /// If air is weak: nudge larynx/jaw/rms-related motors to close residual.
    /// If air is strong: slow consolidation of current bias (keep what works).
    pub fn adaptFromSelfHear(
        self: *SpeechOrgan,
        residual_feats: *const [8]Fixed,
        air_match: Fixed,
        air_heard: bool,
    ) void {
        self.last_air_match = air_match;
        self.n_adapt += 1;

        // step size: larger when air fails (need change), smaller when air ok (stabilize)
        const lr: Fixed = if (air_heard)
            fixed.fromDecimalStr("0.04")
        else
            fixed.fromDecimalStr("0.14");

        // Map residual energy into motor corrections (inverse model sketch):
        // residual[0] ~ pitch-ish → larynx (ch4)
        // residual[1] ~ F1-ish → jaw (ch2)
        // residual[2] ~ F2-ish → tongue ant (ch0)
        // residual[3] ~ rms → jaw + larynx
        // residual[4] ~ tilt → lip (ch3)
        const r0 = residual_feats[0];
        const r1 = residual_feats[1];
        const r2 = residual_feats[2];
        const r3 = residual_feats[3];
        const r4 = residual_feats[4];

        // If residual is large and match weak, push motors opposite residual sign
        // so next forward model aims closer to what mic still "wants" after cancel.
        // sign(r) * lr * |r| capped
        const scale = if (fixed.gt(air_match, fixed.fromDecimalStr("0.5")))
            fixed.mul(lr, fixed.fromDecimalStr("0.5"))
        else
            lr;

        self.motor_bias.ch[4] = fixed.clamp(
            fixed.add(self.motor_bias.ch[4], fixed.mul(r0, scale)),
            fixed.fromDecimalStr("-0.55"),
            fixed.fromDecimalStr("0.55"),
        );
        self.motor_bias.ch[2] = fixed.clamp(
            fixed.add(self.motor_bias.ch[2], fixed.mul(fixed.add(r1, fixed.mul(r3, fixed.fromDecimalStr("0.4"))), scale)),
            fixed.fromDecimalStr("-0.55"),
            fixed.fromDecimalStr("0.55"),
        );
        self.motor_bias.ch[0] = fixed.clamp(
            fixed.add(self.motor_bias.ch[0], fixed.mul(r2, scale)),
            fixed.fromDecimalStr("-0.55"),
            fixed.fromDecimalStr("0.55"),
        );
        self.motor_bias.ch[3] = fixed.clamp(
            fixed.add(self.motor_bias.ch[3], fixed.mul(r4, scale)),
            fixed.fromDecimalStr("-0.55"),
            fixed.fromDecimalStr("0.55"),
        );
        // tongue height mild from residual envelope
        self.motor_bias.ch[1] = fixed.clamp(
            fixed.add(self.motor_bias.ch[1], fixed.mul(r3, fixed.mul(scale, fixed.fromDecimalStr("0.35")))),
            fixed.fromDecimalStr("-0.45"),
            fixed.fromDecimalStr("0.45"),
        );
    }

    /// L2-ish magnitude of motor_bias (how far adaptation has moved the tract).
    pub fn biasMagnitude(self: *const SpeechOrgan) Fixed {
        var s: Fixed = 0;
        var i: usize = 0;
        while (i < MOTOR_N) : (i += 1) {
            s = fixed.add(s, fixed.mul(self.motor_bias.ch[i], self.motor_bias.ch[i]));
        }
        return fixed.sqrt(s);
    }

    /// Last gesture family id used (0..N_GESTURES-1).
    pub fn lastPatternId(self: *const SpeechOrgan) u32 {
        if (self.pattern_i == 0) return 0;
        return (self.pattern_i -% 1) % @as(u32, N_GESTURES);
    }

    /// Teach: bind orthographic symbol to this sound (and its motor).
    /// Writing/reading path: sound ↔ letter association (alphabet as secondary).
    /// Uses adapted bias so taught sounds match what the body currently produces.
    pub fn teachSymbol(self: *SpeechOrgan, symbol: u32, meaning: []const Fixed) void {
        if (self.n >= MAX_BINDS) return;
        // update existing bind for same symbol if present
        var j: usize = 0;
        while (j < self.n) : (j += 1) {
            if (self.binds[j].valid and self.binds[j].symbol == symbol) {
                const u = self.utterAdapted(meaning);
                self.binds[j].motor = u.motor;
                self.binds[j].acoustic = u.acoustic;
                var i: usize = 0;
                while (i < MEANING_N and i < meaning.len) : (i += 1) self.binds[j].meaning[i] = meaning[i];
                return;
            }
        }
        const u = self.utterAdapted(meaning);
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

/// Name for gesture family id (module-level for reports).
pub fn gestureName(id: u32) []const u8 {
    return GESTURE_NAMES[id % N_GESTURES];
}

/// Seed meaning for a letter index (A=0…) — concept prior, not a text token stream.
fn letterMeaning(idx: u32, out: *[MEANING_N]Fixed) void {
    var i: usize = 0;
    while (i < MEANING_N) : (i += 1) {
        const u: u32 = idx *% 37 +% @as(u32, @intCast(i)) *% 11 +% 5;
        const a: i64 = @intCast(u % 181);
        out[i] = fixed.sub(fixed.div(fixed.fromInt(a), fixed.fromInt(90)), fixed.fromInt(1));
    }
}

const LETTERS = "ABCDEFGHIJKLMNOP"; // expanded alphabet scaffold (16)

/// Multi-gesture "word": coarticulated blend (onset-heavy) — still not next-token.
pub fn utterWord(meanings: []const [MEANING_N]Fixed, out: *Acoustic) void {
    var i: usize = 0;
    while (i < ACOUSTIC_N) : (i += 1) out.ch[i] = 0;
    if (meanings.len == 0) return;
    // onset (first) weighted higher — syllable nucleus bias
    const w0 = fixed.fromDecimalStr("0.72");
    const w1 = fixed.fromDecimalStr("0.28");
    const onset = SpeechOrgan.utter(meanings[0][0..]);
    i = 0;
    while (i < ACOUSTIC_N) : (i += 1) out.ch[i] = fixed.mul(onset.acoustic.ch[i], w0);
    if (meanings.len > 1) {
        const coda = SpeechOrgan.utter(meanings[1][0..]);
        i = 0;
        while (i < ACOUSTIC_N) : (i += 1) {
            out.ch[i] = fixed.add(out.ch[i], fixed.mul(coda.acoustic.ch[i], w1));
        }
    }
}

pub const SpeechReport = struct {
    ok: bool,
    n_letters: u32,
    /// hear acoustic → correct letter
    hear_correct: u32,
    hear_top1: f64,
    /// re-utter from meaning → acoustic still matches letter
    roundtrip_correct: u32,
    roundtrip_top1: f64,
    /// multi-gesture word discrimination
    word_correct: u32,
    word_n: u32,
    word_top1: f64,
    doctrine: []const u8 = "motor→sound→symbol; not next-token",
};

pub fn runSpeechOrganProbe() SpeechReport {
    var organ: SpeechOrgan = .{};
    organ.clear();

    const n_letters: usize = 16;
    var meanings: [16][MEANING_N]Fixed = undefined;
    var symbols: [16]u32 = undefined;

    var i: usize = 0;
    while (i < n_letters) : (i += 1) {
        letterMeaning(@intCast(i), &meanings[i]);
        symbols[i] = @as(u32, LETTERS[i]);
        organ.teachSymbol(symbols[i], meanings[i][0..]);
    }

    // Test 1: produce sound from meaning, hear letter
    var hear_ok: u32 = 0;
    i = 0;
    while (i < n_letters) : (i += 1) {
        const u = SpeechOrgan.utter(meanings[i][0..]);
        var heard = u.acoustic;
        heard.ch[3] = fixed.add(heard.ch[3], fixed.fromDecimalStr("0.02"));
        const sym = organ.hearSymbol(heard);
        if (sym == symbols[i]) hear_ok += 1;
    }

    // Test 2: round-trip
    var rt_ok: u32 = 0;
    i = 0;
    while (i < n_letters) : (i += 1) {
        const u = SpeechOrgan.utter(meanings[i][0..]);
        const sym = organ.hearSymbol(u.acoustic);
        if (sym == symbols[i]) rt_ok += 1;
    }

    // Test 3: words = 2-letter motor sequences → mean acoustic → first letter identity still above chance
    // (scaffold for continuous utterance; full lexicon later)
    var word_ok: u32 = 0;
    const n_words: usize = 8;
    i = 0;
    while (i < n_words) : (i += 1) {
        const pair = [_][MEANING_N]Fixed{ meanings[i], meanings[i + 1] };
        var ac: Acoustic = .{};
        utterWord(pair[0..], &ac);
        const sym = organ.hearSymbol(ac);
        // onset-heavy: expect first letter of pair
        if (sym == symbols[i]) word_ok += 1;
    }

    const nf: f64 = @floatFromInt(n_letters);
    const hear_top1 = @as(f64, @floatFromInt(hear_ok)) / nf;
    const rt_top1 = @as(f64, @floatFromInt(rt_ok)) / nf;
    const wtop = @as(f64, @floatFromInt(word_ok)) / @as(f64, @floatFromInt(n_words));
    const ok = hear_top1 >= 0.75 and rt_top1 >= 0.85 and wtop >= 0.5;
    return .{
        .ok = ok,
        .n_letters = @intCast(n_letters),
        .hear_correct = hear_ok,
        .hear_top1 = hear_top1,
        .roundtrip_correct = rt_ok,
        .roundtrip_top1 = rt_top1,
        .word_correct = word_ok,
        .word_n = @intCast(n_words),
        .word_top1 = wtop,
    };
}

pub fn selfTest() bool {
    return runSpeechOrganProbe().ok;
}
