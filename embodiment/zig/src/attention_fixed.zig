//! Biological attention — sensory + meaning attunement to the subject at hand.
//!
//! Not a transformer. Two interlocking loops:
//!   1. Figure / ground (auditory scene): novelty × (1 − ignore)
//!   2. Meaning bind: symbol / retrieve / self-voice match the *subject*
//!
//! Gates are EEG-anchored (eeg_gate_anchors_fixed) + seed-lawful pathway gains.
//! Encode opens when attunement is high (SME doctrine: study vs rest).

const fixed = @import("fixed.zig");
const eeg = @import("eeg_gate_anchors_fixed.zig");
const pathways_f = @import("pathways_fixed.zig");
const Fixed = fixed.Fixed;

pub const Mode = enum(u8) {
    /// low drive — ground dominates, rest / baseline
    rest = 0,
    /// figure stands out; ignore known noise
    orient = 1,
    /// subject at hand — encode / study drive (θ elevation path)
    encode = 2,
    /// flexible reconfigure (α ideation path)
    reconfigure = 3,
};

pub const Snapshot = struct {
    /// raw residual energy after self-cancel (pre-ignore)
    novelty: Fixed = 0,
    /// how much scene classified as ignore-able noise 0..1
    ignore: Fixed = 0,
    /// self-voice match (air or internal re-afference)
    self_match: Fixed = 0,
    /// meaning / symbol / retrieve bind 0..1
    meaning: Fixed = 0,
    /// figure salience = novelty × (1 − ignore)
    figure: Fixed = 0,
    /// combined attunement to subject
    attune: Fixed = 0,
    /// whether encode gate is open (SME study path)
    encode_open: bool = false,
    /// inject gain for figure path this tick
    figure_gain: Fixed = 0,
    /// inject gain for residual ground / ambient
    ground_gain: Fixed = 0,
    mode: Mode = .rest,
};

/// Combine scene + self + meaning into one attunement snapshot.
///
/// Inputs:
///   novelty   — residual energy after noise strip (or raw residual)
///   ignore    — 0..1 scene suppress weight (1 = fully ignored ground)
///   self_match— cosine / PCM self-hear score
///   meaning   — 0..1 symbol hit or retrieve sim
pub fn attune(
    novelty: Fixed,
    ignore: Fixed,
    self_match: Fixed,
    meaning: Fixed,
) Snapshot {
    var s: Snapshot = .{};
    s.novelty = novelty;
    s.ignore = fixed.clamp(ignore, 0, fixed.fromInt(1));
    s.self_match = fixed.clamp(self_match, 0, fixed.fromInt(1));
    s.meaning = fixed.clamp(meaning, 0, fixed.fromInt(1));

    // figure = novelty × (1 − ignore)
    const keep = fixed.sub(fixed.fromInt(1), s.ignore);
    s.figure = fixed.mul(s.novelty, keep);

    // attune = figure + w_self·self + w_mean·meaning  (EEG-weighted)
    const w_self = eeg.selfSalienceWeight();
    const w_mean = eeg.meaningBindWeight();
    s.attune = fixed.add(
        s.figure,
        fixed.add(fixed.mul(w_self, s.self_match), fixed.mul(w_mean, s.meaning)),
    );

    // Encode gate: SME literature expects encode elevates θ+γ vs rest.
    // Operational proxy without full band window every tick:
    //   open when attune ≥ novelty_floor * (1 + encode_drive)  OR strong self+meaning
    const floor = eeg.noveltyFloor();
    const drive = eeg.encodeDriveFromTheta();
    const thresh = fixed.mul(floor, fixed.add(fixed.fromInt(1), drive));
    const self_and_mean = fixed.gt(s.self_match, eeg.selfMatchThreshAir()) and fixed.gt(s.meaning, fixed.fromDecimalStr("0.15"));
    s.encode_open = fixed.gt(s.attune, thresh) or self_and_mean;

    // Gains
    s.figure_gain = if (s.encode_open)
        eeg.attendedFigureGain()
    else
        fixed.mul(eeg.attendedFigureGain(), fixed.fromDecimalStr("0.65"));
    s.ground_gain = eeg.groundInjectGain();
    // If strongly ignoring, further damp ground
    if (fixed.gt(s.ignore, fixed.fromDecimalStr("0.5"))) {
        s.ground_gain = fixed.mul(s.ground_gain, fixed.sub(fixed.fromInt(1), fixed.mul(s.ignore, fixed.fromDecimalStr("0.5"))));
    }

    // Mode
    if (s.encode_open and fixed.gt(s.meaning, fixed.fromDecimalStr("0.2"))) {
        s.mode = .encode;
    } else if (fixed.gt(s.figure, floor) or fixed.gt(s.self_match, eeg.selfMatchThreshAir())) {
        s.mode = .orient;
    } else if (fixed.gt(s.attune, fixed.mul(floor, eeg.ALPHA_CONC_OVER_RELAX)) and fixed.lt(s.meaning, fixed.fromDecimalStr("0.1"))) {
        // high attune without meaning → flexible scan (α path)
        s.mode = .reconfigure;
    } else {
        s.mode = .rest;
    }

    return s;
}

pub fn modeName(m: Mode) []const u8 {
    return switch (m) {
        .rest => "rest",
        .orient => "orient",
        .encode => "encode",
        .reconfigure => "reconfig",
    };
}

/// Map attunement mode → pathway inject scale for speech_sound / attended audio.
pub fn speechInjectScale(s: *const Snapshot) Fixed {
    const g = pathways_f.pathwayGain(.primary);
    return switch (s.mode) {
        .encode => fixed.mul(g, fixed.add(fixed.fromInt(1), eeg.encodeDriveFromTheta())),
        .orient => g,
        .reconfigure => fixed.mul(g, fixed.fromDecimalStr("0.9")),
        .rest => fixed.mul(g, fixed.fromDecimalStr("0.55")),
    };
}

pub fn selfTest() bool {
    if (!eeg.selfTest()) return false;
    // High novelty + low ignore + some meaning → encode path open
    const a = attune(
        fixed.fromDecimalStr("0.4"),
        fixed.fromDecimalStr("0.1"),
        fixed.fromDecimalStr("0.2"),
        fixed.fromDecimalStr("0.3"),
    );
    if (!a.encode_open) return false;
    if (!fixed.gt(a.figure_gain, a.ground_gain)) return false;
    // Fully ignored low novelty → rest
    const b = attune(
        fixed.fromDecimalStr("0.05"),
        fixed.fromDecimalStr("0.9"),
        0,
        0,
    );
    if (b.mode == .encode) return false;
    return true;
}
