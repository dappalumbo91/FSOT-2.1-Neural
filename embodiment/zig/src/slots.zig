//! 5W1H lesson slots — bare-metal card (token hashes, not free text).
//! Replaces fsot_nuron/knowledge/teach_5w1h.py structure for Zig mind.
//! Host/Python may mint tokens from captions; organism stores + queries here.

const memory = @import("memory.zig");

pub const Slot = enum(u3) {
    who = 0,
    what = 1,
    why = 2,
    where = 3,
    when = 4,
    how = 5,
};

pub const Card = struct {
    source_hash: u32 = 0,
    domain: memory.Domain = .generic,
    tokens: [6]u32 = .{0} ** 6,
    slot_mask: u8 = 0,

    pub fn set(self: *Card, slot: Slot, token: u32) void {
        if (token == 0) return;
        const i: usize = @intFromEnum(slot);
        self.tokens[i] = token;
        self.slot_mask |= @as(u8, 1) << @intFromEnum(slot);
    }

    pub fn emptyMask(self: *const Card) u8 {
        return ~self.slot_mask & 0x3F;
    }

    pub fn nEmpty(self: *const Card) u32 {
        var m = self.emptyMask();
        var c: u32 = 0;
        while (m != 0) : (m >>= 1) {
            if ((m & 1) != 0) c += 1;
        }
        return c;
    }

    pub fn nFilled(self: *const Card) u32 {
        return 6 - self.nEmpty();
    }

    /// Emit up to 6 open questions as slot tags (who=0 … how=5).
    pub fn openQuestions(self: *const Card, out: *[6]u3) u32 {
        var n: u32 = 0;
        var s: u3 = 0;
        while (s < 6) : (s += 1) {
            const bit: u8 = @as(u8, 1) << s;
            if ((self.slot_mask & bit) == 0) {
                out[n] = s;
                n += 1;
            }
        }
        return n;
    }
};

/// Mechanism templates (domain-tagged WHY tokens) — seed vocabulary ids.
pub fn mechanismToken(domain: memory.Domain) u32 {
    return switch (domain) {
        .biology => memory.hashToken("ei_balance"),
        .physics_fsot => memory.hashToken("scalar_S_K"),
        .narrative => memory.hashToken("character_goal"),
        .media => memory.hashToken("caption_bind"),
        .learning => memory.hashToken("encode_retrieve"),
        .generic => memory.hashToken("pattern_assoc"),
    };
}

/// Curiosity: for each empty slot, propose a fill from template or peer episode.
pub const CuriosityReport = struct {
    n_questions: u32 = 0,
    n_resolved: u32 = 0,
    remaining_open: u32 = 0,
};

pub fn runCuriosity(store: *memory.Store, id: u32, domain: memory.Domain) CuriosityReport {
    var rep: CuriosityReport = .{};
    const ep = store.getById(id) orelse return rep;
    var s: u3 = 0;
    while (s < 6) : (s += 1) {
        const bit: u8 = @as(u8, 1) << s;
        if ((ep.slot_mask & bit) != 0) continue;
        rep.n_questions += 1;
        // propose: WHY gets domain mechanism; others try peer with same domain
        var token: u32 = 0;
        if (s == @intFromEnum(Slot.why)) {
            token = mechanismToken(domain);
        } else {
            // scan peers for same slot filled
            var i: usize = 0;
            while (i < store.n) : (i += 1) {
                if (store.episodes[i].id == id) continue;
                if (store.episodes[i].domain != domain and store.episodes[i].domain != .generic) continue;
                if ((store.episodes[i].slot_mask & bit) == 0) continue;
                token = switch (s) {
                    0 => store.episodes[i].who,
                    1 => store.episodes[i].what,
                    2 => store.episodes[i].why,
                    3 => store.episodes[i].where,
                    4 => store.episodes[i].when,
                    5 => store.episodes[i].how,
                    else => 0,
                };
                if (token != 0) break;
            }
        }
        if (token != 0 and store.tryFillSlot(id, s, token)) {
            rep.n_resolved += 1;
        }
    }
    rep.remaining_open = store.emptySlotCount(id);
    return rep;
}

pub fn selfTest() bool {
    var c: Card = .{ .domain = .biology };
    c.set(.who, memory.hashToken("pyramidal"));
    c.set(.what, memory.hashToken("spike"));
    if (c.nFilled() != 2) return false;
    if (c.nEmpty() != 4) return false;
    var q: [6]u3 = undefined;
    const nq = c.openQuestions(&q);
    if (nq != 4) return false;

    var store: memory.Store = .{};
    store.clear();
    // encode minimal with partial slots via memory self path is heavy; unit test curiosity math only
    const mech = mechanismToken(.physics_fsot);
    if (mech == 0) return false;
    return true;
}
