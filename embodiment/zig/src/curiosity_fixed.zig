//! Active curiosity — fill empty 5W1H slots on fixed episodic memory.
//! Replaces knowledge/curiosity.py for Zig fixed authority (no Python).

const fixed = @import("fixed.zig");
const memory_f = @import("memory_fixed.zig");
const brain_f = @import("brain_fixed.zig");
const Fixed = fixed.Fixed;

pub const Slot = enum(u3) {
    who = 0,
    what = 1,
    why = 2,
    where = 3,
    when = 4,
    how = 5,
};

pub const CuriosityReport = struct {
    n_questions: u32 = 0,
    n_resolved: u32 = 0,
    remaining_open: u32 = 0,
    ok: bool = false,
};

fn mechanismToken(domain_tag: u32) u32 {
    // domain_tag 0..5 → seed vocabulary
    return switch (domain_tag % 6) {
        0 => memory_f.hashToken("ei_balance"),
        1 => memory_f.hashToken("scalar_S_K"),
        2 => memory_f.hashToken("character_goal"),
        3 => memory_f.hashToken("caption_bind"),
        4 => memory_f.hashToken("encode_retrieve"),
        else => memory_f.hashToken("pattern_assoc"),
    };
}

fn emptyCount(mask: u8) u32 {
    var c: u32 = 0;
    var s: u3 = 0;
    while (s < 6) : (s += 1) {
        const bit: u8 = @as(u8, 1) << s;
        if ((mask & bit) == 0) c += 1;
    }
    return c;
}

/// Fill empty slots on episode `id` from peer episodes or domain mechanism templates.
pub fn runCuriosity(store: *memory_f.StoreF, id: u32, domain_tag: u32) CuriosityReport {
    var rep: CuriosityReport = .{};
    var ep_i: ?usize = null;
    var i: usize = 0;
    while (i < store.n) : (i += 1) {
        if (store.episodes[i].id == id) {
            ep_i = i;
            break;
        }
    }
    const ei = ep_i orelse return rep;
    var s: u3 = 0;
    while (s < 6) : (s += 1) {
        const bit: u8 = @as(u8, 1) << s;
        if ((store.episodes[ei].slot_mask & bit) != 0) continue;
        rep.n_questions += 1;
        var token: u32 = 0;
        if (s == @intFromEnum(Slot.why)) {
            token = mechanismToken(domain_tag);
        } else {
            // peer scan for same slot filled
            var j: usize = 0;
            while (j < store.n) : (j += 1) {
                if (j == ei) continue;
                if ((store.episodes[j].slot_mask & bit) == 0) continue;
                token = store.episodes[j].tokens[s];
                if (token != 0) break;
            }
        }
        if (token != 0) {
            store.episodes[ei].tokens[s] = token;
            store.episodes[ei].slot_mask |= bit;
            rep.n_resolved += 1;
        }
    }
    rep.remaining_open = emptyCount(store.episodes[ei].slot_mask);
    rep.ok = rep.n_questions == 0 or rep.n_resolved > 0;
    return rep;
}

/// Full probe: encode partial lessons, run curiosity, score filled slots.
pub fn runCuriosityProbe() struct {
    ok: bool,
    n_episodes: u32,
    questions: u32,
    resolved: u32,
    open_after: u32,
} {
    var b = brain_f.BrainF.initSeeded(11, false);
    var store: memory_f.StoreF = .{};
    store.clear();

    // Episode A: who+what filled, why empty
    var f0: [8]Fixed = undefined;
    var k: usize = 0;
    while (k < 8) : (k += 1) f0[k] = fixed.fromDecimalStr("0.5");
    const tok_a = [_]u32{
        memory_f.hashToken("alice"),
        memory_f.hashToken("runs"),
        0,
        0,
        0,
        memory_f.hashToken("step"),
    };
    const id_a = store.encode(&b, f0[0..], 0b100011, tok_a); // who what how

    // Episode B: who+what+why filled (peer for why)
    var f1: [8]Fixed = undefined;
    k = 0;
    while (k < 8) : (k += 1) f1[k] = fixed.fromDecimalStr("-0.4");
    const tok_b = [_]u32{
        memory_f.hashToken("bob"),
        memory_f.hashToken("sings"),
        memory_f.hashToken("joy"),
        memory_f.hashToken("stage"),
        0,
        memory_f.hashToken("step"),
    };
    _ = store.encode(&b, f1[0..], 0b101111, tok_b);

    const cur = runCuriosity(&store, id_a, 2); // narrative domain
    return .{
        .ok = cur.ok and cur.n_resolved >= 1,
        .n_episodes = @intCast(store.n),
        .questions = cur.n_questions,
        .resolved = cur.n_resolved,
        .open_after = cur.remaining_open,
    };
}
