//! Continuous host sense loop — sample plant → inject → tick (OS-like body cycle).
//! Still Zig-only; mind remains Fixed lattice authority.

const fixed = @import("fixed.zig");
const host_f = @import("host_senses_fixed.zig");
const organism_f = @import("organism_fixed.zig");
const speech_f = @import("speech_organ_fixed.zig");
const Fixed = fixed.Fixed;

pub const HostLoopReport = struct {
    ok: bool,
    n_ticks: u32,
    n_live_display: u32,
    n_live_mic: u32,
    spikes: u32,
    episodes: u32,
    spoke: bool,
};

/// Run N body cycles: host sample → bio inject → organism tick.
/// Optionally drive speech plant from vision mean (efferent scaffold).
pub fn runHostLoop(n_ticks: u32, do_speak: bool) HostLoopReport {
    var org = organism_f.OrganismF.init();
    org.encode_every = 6;
    org.steps_per_tick = 2;
    if (do_speak) org.speak_every = 5;

    var n_disp: u32 = 0;
    var n_mic: u32 = 0;
    var t: u32 = 0;
    while (t < n_ticks) : (t += 1) {
        var sample: host_f.HostSample = .{};
        host_f.sampleHost(&sample);
        if (sample.live_display) n_disp += 1;
        if (sample.live_mic) n_mic += 1;
        host_f.injectIntoOrganism(&org, &sample);
        if (do_speak) {
            // meaning from vision features — motor plant, not token LM
            org.setMeaning(sample.vision[0..]);
        }
        _ = org.tickOnce();
    }

    const ok = n_ticks >= 1 and org.brain.totalSpikes() >= 0 and (n_disp + n_mic > 0 or org.store.n >= 1);
    return .{
        .ok = ok,
        .n_ticks = n_ticks,
        .n_live_display = n_disp,
        .n_live_mic = n_mic,
        .spikes = org.brain.totalSpikes(),
        .episodes = @intCast(org.store.n),
        .spoke = do_speak,
    };
}
