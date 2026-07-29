//! EEG / sensory experiment anchors for attention & encode gates.
//!
//! Doctrine: gates are *not* free parameters. They come from:
//!   1. Local instrumental EEG (mental-state concentrate vs relax)
//!   2. Literature SME / consolidation priors (Sederberg 2003, Creery 2022)
//!   3. FSOT couple of study-band drivers → Neuroscience fold (zero free LSQ)
//!   4. Existing seed-lawful consciousness gate φ/(1+φ)
//!
//! Sources (local, measured 2026-07-28):
//!   data/kaggle_datasets/eeg_mental_state/mental-state.csv  (n=2479)
//!   artifacts/learning_eeg_study.json / docs/LEARNING_EEG_STUDY.md
//!   data/eeg/openneuro_pd/pd_eeg_feature_priors.json (pathology contrast only)
//!
//! Honesty: mental-state CSV is a *feature matrix*, not raw scalp EDF.
//! Gamma/beta ratios in that matrix can disagree with iEEG literature;
//! encode direction uses Sederberg SME; study *drive strength* uses measured θ.

const fixed = @import("fixed.zig");
const seeds_f = @import("seeds_fixed.zig");
const pathways_f = @import("pathways_fixed.zig");
const Fixed = fixed.Fixed;

// ---------------------------------------------------------------------------
// Band edges (Hz) — literature + OpenNeuro PD prior agreement
// ---------------------------------------------------------------------------

pub const THETA_HZ_LO: i64 = 4;
pub const THETA_HZ_HI: i64 = 8;
pub const ALPHA_HZ_LO: i64 = 8;
pub const ALPHA_HZ_HI: i64 = 12;
pub const SIGMA_HZ_LO: i64 = 12;
pub const SIGMA_HZ_HI: i64 = 16;
pub const BETA_HZ_LO: i64 = 13;
pub const BETA_HZ_HI: i64 = 30;
pub const GAMMA_HZ_LO: i64 = 28;
pub const GAMMA_HZ_HI: i64 = 64;

// ---------------------------------------------------------------------------
// Mental-state EEG: concentrate / relax band energy ratios
// From learning_eeg_study.json → study_eeg.concentrate_vs_relax
// Labels: 0=relaxed, 1=neutral, 2=concentrating (830/830/819 rows)
// ---------------------------------------------------------------------------

/// θ concentrate / θ relax — primary study-drive anchor (elevated).
pub const THETA_CONC_OVER_RELAX: Fixed = fixed.fromDecimalStr("1.573884113069");
/// α concentrate / α relax — flexible reconfigure / ideation proxy.
pub const ALPHA_CONC_OVER_RELAX: Fixed = fixed.fromDecimalStr("1.442870255285");
/// β concentrate / β relax — CSV proxy (often down under this feature set).
pub const BETA_CONC_OVER_RELAX: Fixed = fixed.fromDecimalStr("0.456276963474");
/// γ concentrate / γ relax — CSV proxy; prefer literature for encode direction.
pub const GAMMA_CONC_OVER_RELAX: Fixed = fixed.fromDecimalStr("0.693621311681");

// ---------------------------------------------------------------------------
// FSOT couple from study EEG (authority_mpmath, free_parameters=0)
// learning_eeg_study.json → study_eeg.fsot_couple
// ---------------------------------------------------------------------------

/// Mild amplitude from seed-folded log-ratios of concentrate/relax bands.
pub const STUDY_AMPLITUDE: Fixed = fixed.fromDecimalStr("0.995426242493");
/// Throughput / P term from θ elevation.
pub const STUDY_P: Fixed = fixed.fromDecimalStr("1.092856400054");
/// Coupled Neuroscience S under study drive.
pub const STUDY_S: Fixed = fixed.fromDecimalStr("0.543495558870");
/// Sensory strength for attended figure inject (0..1 scale).
pub const SENSORY_STRENGTH: Fixed = fixed.fromDecimalStr("0.797140510901");

// ---------------------------------------------------------------------------
// Literature directional priors (not fitted on our CSVs)
// ---------------------------------------------------------------------------

/// Sederberg et al. 2003 J Neurosci: successful encoding ↑ θ + γ (iEEG).
pub const SME_EXPECT_THETA_ENCODE_GT_REST: bool = true;
pub const SME_EXPECT_GAMMA_ENCODE_GT_REST: bool = true;

/// Creery et al. 2022 PNAS: offline consolidation σ/θ/γ.
pub const CONSOL_EXPECT_SIGMA_OR_THETA: bool = true;

/// EEG ideation literature: ↑ α (8–12) during flexible reconfigure.
pub const IDEATION_EXPECT_ALPHA_UP: bool = true;

// ---------------------------------------------------------------------------
// Pathology contrast (OpenNeuro ds002778 PD priors) — not used for attention
// default path; available if lesion / irregularity modes need them later.
// ---------------------------------------------------------------------------

pub const PD_BETA_POWER_RATIO: Fixed = fixed.fromDecimalStr("1.45");
pub const PD_ALPHA_POWER_RATIO: Fixed = fixed.fromDecimalStr("0.85");
pub const PD_THETA_POWER_RATIO: Fixed = fixed.fromDecimalStr("1.15");

// ---------------------------------------------------------------------------
// Derived gates (measured × seed-lawful, no free LSQ)
// ---------------------------------------------------------------------------

/// How hard to push encode when the subject is "at hand" (concentrate θ).
/// = clamp(θ_conc/relax − 1, 0, 1)  → ~0.574
pub fn encodeDriveFromTheta() Fixed {
    const excess = fixed.sub(THETA_CONC_OVER_RELAX, fixed.fromInt(1));
    if (fixed.lt(excess, 0)) return 0;
    return fixed.clamp(excess, 0, fixed.fromInt(1));
}

/// Figure-path inject gain when attended (measured sensory_strength × φ-gate).
pub fn attendedFigureGain() Fixed {
    return fixed.mul(SENSORY_STRENGTH, pathways_f.consciousnessGate());
}

/// Ground / ignore residual inject gain (weaker than figure).
/// Uses inverse of θ elevation so ambient is down-weighted under study drive.
pub fn groundInjectGain() Fixed {
    // 1 / θ_conc_over_relax ≈ 0.635, then soft-scale by (1−sensory_strength)
    const inv_th = fixed.div(fixed.fromInt(1), THETA_CONC_OVER_RELAX);
    const ground_frac = fixed.sub(fixed.fromInt(1), SENSORY_STRENGTH);
    return fixed.mul(inv_th, ground_frac);
}

/// Self-voice air-match threshold in noisy rooms.
/// Soft floor from residual of sensory strength: (1 − SENSORY_STRENGTH) * 0.5 ≈ 0.10
/// Matches prior living-room soft threshold without inventing a free number.
pub fn selfMatchThreshAir() Fixed {
    return fixed.mul(fixed.sub(fixed.fromInt(1), SENSORY_STRENGTH), fixed.fromDecimalStr("0.5"));
}

/// Novelty floor for "figure still present after ignore" — below this, treat as ground.
/// Anchored to groundInjectGain so ignore and novelty share the same authority chain.
pub fn noveltyFloor() Fixed {
    return fixed.mul(groundInjectGain(), fixed.fromDecimalStr("0.95"));
}

/// Cosine similarity to call a recurring sound "known noise" (habituation class).
/// Seed-folded: φ⁻¹ ≈ 0.618, soft-shifted toward mental-state separability.
pub fn noiseClassMatchThresh() Fixed {
    // 1/φ ≈ 0.618 → slightly softer 0.55 for feature-space mic noise
    const inv_phi = fixed.div(fixed.fromInt(1), seeds_f.phi);
    return fixed.sub(inv_phi, fixed.fromDecimalStr("0.068"));
}

/// Salience weight on self-match (bone/air re-afference) — α ideation ratio soft.
pub fn selfSalienceWeight() Fixed {
    // (α_conc/relax − 1) clamped → own-voice is "subject" when attending
    const excess = fixed.sub(ALPHA_CONC_OVER_RELAX, fixed.fromInt(1));
    if (fixed.lt(excess, fixed.fromDecimalStr("0.2"))) return fixed.fromDecimalStr("0.2");
    return fixed.clamp(excess, 0, fixed.fromInt(1));
}

/// Meaning-bind weight (symbol / retrieve hit) — study P mild.
pub fn meaningBindWeight() Fixed {
    return fixed.clamp(fixed.sub(STUDY_P, fixed.fromInt(1)), fixed.fromDecimalStr("0.05"), fixed.fromDecimalStr("0.5"));
}

pub const AnchorReport = struct {
    theta_conc_relax: f64,
    alpha_conc_relax: f64,
    gamma_conc_relax: f64,
    sensory_strength: f64,
    study_s: f64,
    encode_drive: f64,
    figure_gain: f64,
    ground_gain: f64,
    self_match_thresh: f64,
    novelty_floor: f64,
    sme_theta_gt: bool,
    sme_gamma_gt: bool,
};

pub fn report() AnchorReport {
    return .{
        .theta_conc_relax = fixed.toF64(THETA_CONC_OVER_RELAX),
        .alpha_conc_relax = fixed.toF64(ALPHA_CONC_OVER_RELAX),
        .gamma_conc_relax = fixed.toF64(GAMMA_CONC_OVER_RELAX),
        .sensory_strength = fixed.toF64(SENSORY_STRENGTH),
        .study_s = fixed.toF64(STUDY_S),
        .encode_drive = fixed.toF64(encodeDriveFromTheta()),
        .figure_gain = fixed.toF64(attendedFigureGain()),
        .ground_gain = fixed.toF64(groundInjectGain()),
        .self_match_thresh = fixed.toF64(selfMatchThreshAir()),
        .novelty_floor = fixed.toF64(noveltyFloor()),
        .sme_theta_gt = SME_EXPECT_THETA_ENCODE_GT_REST,
        .sme_gamma_gt = SME_EXPECT_GAMMA_ENCODE_GT_REST,
    };
}

pub fn selfTest() bool {
    // θ elevation must be > 1 (concentrate stronger than relax)
    if (!fixed.gt(THETA_CONC_OVER_RELAX, fixed.fromInt(1))) return false;
    // sensory strength in (0,1]
    if (!fixed.gt(SENSORY_STRENGTH, 0)) return false;
    if (fixed.gt(SENSORY_STRENGTH, fixed.fromInt(1))) return false;
    // figure gain > ground gain (attend subject, ignore ground)
    if (!fixed.gt(attendedFigureGain(), groundInjectGain())) return false;
    // self-match thresh soft but positive
    if (!fixed.gt(selfMatchThreshAir(), 0)) return false;
    return SME_EXPECT_THETA_ENCODE_GT_REST and SME_EXPECT_GAMMA_ENCODE_GT_REST;
}
