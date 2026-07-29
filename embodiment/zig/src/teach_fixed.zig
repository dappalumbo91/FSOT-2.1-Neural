//! 5W1H teach cards on fixed lattice.
//! Replaces teach_5w1h.py structure for Zig authority (token hashes, domain mechanisms).
//! Host may mint tokens from text/captions; mind stores + probes without title cheats.

const fixed = @import("fixed.zig");
const brain_f = @import("brain_fixed.zig");
const memory_f = @import("memory_fixed.zig");
const curiosity_f = @import("curiosity_fixed.zig");
const Fixed = fixed.Fixed;

pub const Domain = enum(u8) {
    biology = 0,
    physics_fsot = 1,
    narrative = 2,
    media = 3,
    learning = 4,
    generic = 5,
};

pub const Card = struct {
    domain: Domain = .generic,
    tokens: [6]u32 = .{0} ** 6,
    slot_mask: u8 = 0,
    source_hash: u32 = 0,

    pub fn set(self: *Card, slot: curiosity_f.Slot, token: u32) void {
        if (token == 0) return;
        const i: usize = @intFromEnum(slot);
        self.tokens[i] = token;
        self.slot_mask |= @as(u8, 1) << @intFromEnum(slot);
    }

    pub fn nFilled(self: *const Card) u32 {
        var c: u32 = 0;
        var s: u3 = 0;
        while (s < 6) : (s += 1) {
            if ((self.slot_mask & (@as(u8, 1) << s)) != 0) c += 1;
        }
        return c;
    }
};

pub fn mechanismToken(domain: Domain) u32 {
    return switch (domain) {
        .biology => memory_f.hashToken("ei_balance"),
        .physics_fsot => memory_f.hashToken("scalar_S_K"),
        .narrative => memory_f.hashToken("character_goal"),
        .media => memory_f.hashToken("caption_bind"),
        .learning => memory_f.hashToken("encode_retrieve"),
        .generic => memory_f.hashToken("pattern_assoc"),
    };
}

/// Build a structured lesson (compositional, not free-text LLM).
pub fn buildLesson(
    domain: Domain,
    who: []const u8,
    what: []const u8,
    where: []const u8,
    how: []const u8,
    source: []const u8,
    fill_why: bool,
) Card {
    var c: Card = .{ .domain = domain, .source_hash = memory_f.hashToken(source) };
    c.set(.who, memory_f.hashToken(who));
    c.set(.what, memory_f.hashToken(what));
    if (where.len > 0) c.set(.where, memory_f.hashToken(where));
    if (how.len > 0) c.set(.how, memory_f.hashToken(how));
    if (fill_why) c.set(.why, mechanismToken(domain));
    // when left empty → curiosity target
    return c;
}

/// Features from card content hashes (no title channel) — content pattern only.
fn cardFeatures(card: *const Card, out: *[8]Fixed) void {
    var i: usize = 0;
    while (i < 8) : (i += 1) {
        const t: u32 = if (i < 6) card.tokens[i] else card.source_hash;
        // mix: never pure title; source only softens last dims
        const mix: u32 = t *% 2654435761 +% @as(u32, @intCast(i)) *% 97 +% @intFromEnum(card.domain) *% 13;
        const a: i64 = @intCast(mix % 200);
        out[i] = fixed.sub(fixed.div(fixed.fromInt(a), fixed.fromInt(100)), fixed.fromInt(1));
    }
    // zero "title" influence on first 5 dims — content-only spirit
    // (source_hash only affects dims 6-7 weakly via tokens path when i>=6)
}

pub const TeachReport = struct {
    ok: bool,
    n_lessons: u32,
    n_encoded: u32,
    slot_hits: u32,
    slot_probes: u32,
    slot_top1: f64,
    curiosity_resolved: u32,
    curiosity_questions: u32,
    spikes: u32,
};

pub fn runTeachProbe() TeachReport {
    var b = brain_f.BrainF.initSeeded(31, false);
    var store: memory_f.StoreF = .{};
    store.clear();

    // Three domain lessons — structured 5W1H, no title-only identity
    const lessons = [_]Card{
        buildLesson(.physics_fsot, "agent", "scalar_fold", "lattice", "fixed_step", "doc_a_physics", true),
        buildLesson(.biology, "pyr", "ei_balance", "cortex", "fi_curve", "doc_b_bio", true),
        buildLesson(.narrative, "neo", "choice", "matrix", "bind", "doc_c_story", false), // why empty
    };

    var fulls: [3][8]Fixed = undefined;
    var ids: [3]u32 = undefined;
    var i: usize = 0;
    while (i < 3) : (i += 1) {
        cardFeatures(&lessons[i], &fulls[i]);
        // encode tokens as 5W1H; retrieve will use features only
        ids[i] = store.encode(&b, fulls[i][0..], lessons[i].slot_mask, lessons[i].tokens);
    }

    // Curiosity fill on narrative (empty why)
    const cur = curiosity_f.runCuriosity(&store, ids[2], 2); // domain_tag 2 = narrative-ish

    // delay
    var ext: [brain_f.N_TOTAL]Fixed = .{fixed.fromDecimalStr("0.04")} ** brain_f.N_TOTAL;
    var d: usize = 0;
    while (d < 14) : (d += 1) b.step(ext[0..]);

    // Slot probes: retrieve by content features → check WHO token (not source title)
    var hits: u32 = 0;
    var probes: u32 = 0;
    i = 0;
    while (i < 3) : (i += 1) {
        var sim: Fixed = 0;
        const hit = store.retrieve(&b, fulls[i][0..], &sim);
        probes += 1;
        // find who of retrieved episode
        var who_got: u32 = 0;
        var j: usize = 0;
        while (j < store.n) : (j += 1) {
            if (store.episodes[j].id == hit) {
                who_got = store.episodes[j].tokens[0];
                break;
            }
        }
        if (who_got == lessons[i].tokens[0] and who_got != 0) hits += 1;
    }

    const top1 = if (probes == 0) 0.0 else @as(f64, @floatFromInt(hits)) / @as(f64, @floatFromInt(probes));
    const ok = store.n >= 3 and top1 >= 0.66 and (cur.n_questions == 0 or cur.n_resolved > 0);
    return .{
        .ok = ok,
        .n_lessons = 3,
        .n_encoded = @intCast(store.n),
        .slot_hits = hits,
        .slot_probes = probes,
        .slot_top1 = top1,
        .curiosity_resolved = cur.n_resolved,
        .curiosity_questions = cur.n_questions,
        .spikes = b.totalSpikes(),
    };
}
