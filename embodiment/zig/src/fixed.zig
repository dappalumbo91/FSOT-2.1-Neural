//! Seed-scaled fixed-point — continuous FSOT values without IEEE float ops.
//!
//! Doctrine (see docs/FIXED_POINT_EXPERIMENT.md):
//!   - Constants = FSOT seeds as fixed integers
//!   - Variables live between known extremes (e.g. S ∈ [-3, 3])
//!   - Lattice quantum = 1/SCALE (deterministic host ↔ bare metal)
//!
//! Type: i64 storage, i128 intermediate for mul/div.
//! SCALE = 10^12.

pub const Fixed = i64;
pub const SCALE: i64 = 1_000_000_000_000; // 10^12

/// Construct from integer (exact).
pub fn fromInt(n: i64) Fixed {
    return n *% SCALE;
}

/// Construct from rational num/den (rounded half away from zero via integer math).
pub fn fromRatio(num: i64, den: i64) Fixed {
    if (den == 0) return 0;
    // (num * SCALE) / den with rounding
    const wide: i128 = @as(i128, num) * @as(i128, SCALE);
    const d: i128 = den;
    var q = @divTrunc(wide, d);
    const r = @rem(wide, d);
    // round half up in magnitude
    const ad = if (d < 0) -d else d;
    const ar = if (r < 0) -r else r;
    if (ar * 2 >= ad) {
        if ((wide > 0) == (d > 0)) q += 1 else q -= 1;
    }
    return @intCast(q);
}

/// Convert decimal string with optional leading minus, e.g. "3.141592653589" (max 12 frac digits used).
/// For seed load only — no float.
pub fn fromDecimalStr(s: []const u8) Fixed {
    var is_neg = false;
    var i: usize = 0;
    if (s.len > 0 and s[0] == '-') {
        is_neg = true;
        i = 1;
    }
    var int_part: i64 = 0;
    while (i < s.len and s[i] != '.') : (i += 1) {
        const d = s[i];
        if (d < '0' or d > '9') break;
        int_part = int_part *% 10 +% @as(i64, d - '0');
    }
    var frac: i64 = 0;
    var places: i64 = 0;
    if (i < s.len and s[i] == '.') {
        i += 1;
        while (i < s.len and places < 12) : (i += 1) {
            const d = s[i];
            if (d < '0' or d > '9') break;
            frac = frac *% 10 +% @as(i64, d - '0');
            places += 1;
        }
    }
    // pad frac to 12 digits
    while (places < 12) : (places += 1) frac *%= 10;
    // SCALE is 1e12 so frac is already in fixed units for fractional part
    var v: Fixed = int_part *% SCALE +% frac;
    if (is_neg) v = -%v;
    return v;
}

pub fn toParts(x: Fixed) struct { is_neg: bool, int: u64, frac: u64 } {
    const is_neg = x < 0;
    const a: u64 = @intCast(if (is_neg) -%x else x);
    return .{
        .is_neg = is_neg,
        .int = a / @as(u64, @intCast(SCALE)),
        .frac = a % @as(u64, @intCast(SCALE)),
    };
}

pub fn add(a: Fixed, b: Fixed) Fixed {
    return a +% b;
}

pub fn sub(a: Fixed, b: Fixed) Fixed {
    return a -% b;
}

pub fn negate(a: Fixed) Fixed {
    return -%a;
}

pub fn mul(a: Fixed, b: Fixed) Fixed {
    const p: i128 = @as(i128, a) * @as(i128, b);
    // divide by SCALE with rounding
    var q = @divTrunc(p, SCALE);
    const r = @rem(p, SCALE);
    const ar = if (r < 0) -r else r;
    if (ar * 2 >= SCALE) {
        if (p >= 0) q += 1 else q -= 1;
    }
    return @intCast(q);
}

pub fn div(a: Fixed, b: Fixed) Fixed {
    if (b == 0) return if (a >= 0) stdMax() else -stdMax();
    const p: i128 = @as(i128, a) * @as(i128, SCALE);
    var q = @divTrunc(p, b);
    const r = @rem(p, b);
    const ab = if (b < 0) -b else b;
    const ar = if (r < 0) -r else r;
    if (ar * 2 >= ab) {
        if ((p > 0) == (b > 0)) q += 1 else q -= 1;
    }
    return @intCast(q);
}

fn stdMax() Fixed {
    return 3 * SCALE; // clamp extreme used by scalar
}

pub fn abs(a: Fixed) Fixed {
    return if (a < 0) -%a else a;
}

pub fn clamp(x: Fixed, lo: Fixed, hi: Fixed) Fixed {
    if (x < lo) return lo;
    if (x > hi) return hi;
    return x;
}

pub fn lt(a: Fixed, b: Fixed) bool {
    return a < b;
}

pub fn gt(a: Fixed, b: Fixed) bool {
    return a > b;
}

/// Compare fixed to f64 for lab reporting only (host experiment harness).
pub fn toF64(x: Fixed) f64 {
    return @as(f64, @floatFromInt(x)) / @as(f64, @floatFromInt(SCALE));
}

pub fn fromF64Lab(x: f64) Fixed {
    // Lab-only bridge for seed import verification — not used on pure fixed path.
    const v = x * @as(f64, @floatFromInt(SCALE));
    if (v >= 0) return @intFromFloat(@floor(v + 0.5));
    return @intFromFloat(@ceil(v - 0.5));
}

// --- elementary functions via series (pure fixed) ---

const ONE = SCALE;
const TWO = 2 * SCALE;

/// exp(x) for |x| modest (series). Domain used by FSOT neuro fold is small.
pub fn exp(x: Fixed) Fixed {
    // reduce: exp(x) = exp(n*ln2 + r) not needed if |x| < ~2
    // Taylor: sum x^k / k!
    var term: Fixed = ONE;
    var sum: Fixed = ONE;
    var k: i64 = 1;
    while (k < 40) : (k += 1) {
        term = div(mul(term, x), fromInt(k));
        const prev = sum;
        sum = add(sum, term);
        if (sum == prev) break;
        if (abs(term) < 1) break; // below 1 quantum
    }
    return sum;
}

/// cos(x) Taylor
pub fn cos(x: Fixed) Fixed {
    // reduce roughly to [-pi, pi] via subtraction (crude, enough for neuro phases)
    const pi_ = fromDecimalStr("3.141592653589");
    const two_pi = mul(pi_, fromInt(2));
    var t = x;
    // wrap
    while (t > pi_) t = sub(t, two_pi);
    while (t < negate(pi_)) t = add(t, two_pi);

    var term: Fixed = ONE;
    var sum: Fixed = ONE;
    var k: i64 = 1;
    var sign: i64 = -1;
    while (k < 24) : (k += 1) {
        // term *= x^2 / ((2k-1)*2k)
        const n1 = fromInt(2 * k - 1);
        const n2 = fromInt(2 * k);
        term = div(mul(term, mul(t, t)), mul(n1, n2));
        if (sign < 0) sum = sub(sum, term) else sum = add(sum, term);
        sign = -sign;
        if (abs(term) < 1) break;
    }
    return sum;
}

/// sin(x) Taylor
pub fn sin(x: Fixed) Fixed {
    const pi_ = fromDecimalStr("3.141592653589");
    const two_pi = mul(pi_, fromInt(2));
    var t = x;
    while (t > pi_) t = sub(t, two_pi);
    while (t < negate(pi_)) t = add(t, two_pi);

    var term: Fixed = t;
    var sum: Fixed = t;
    var k: i64 = 1;
    var sign: i64 = -1;
    while (k < 24) : (k += 1) {
        const n1 = fromInt(2 * k);
        const n2 = fromInt(2 * k + 1);
        term = div(mul(term, mul(t, t)), mul(n1, n2));
        if (sign < 0) sum = sub(sum, term) else sum = add(sum, term);
        sign = -sign;
        if (abs(term) < 1) break;
    }
    return sum;
}

/// log(x) for x > 0, natural log via atanh series on (x-1)/(x+1) for x near 1,
/// or Newton. Use: ln(x) = 2*(z + z^3/3 + ...) z=(x-1)/(x+1) for x>0.
pub fn log(x: Fixed) Fixed {
    if (x <= 0) return negate(fromInt(100)); // sentinel
    // scale x into [0.5, 2) by powers of 2... skip; neuro uses D/25 near 0.5
    const z = div(sub(x, ONE), add(x, ONE));
    var z2n1 = z; // z^(2n+1)
    var sum: Fixed = z;
    var n: i64 = 1;
    while (n < 40) : (n += 1) {
        z2n1 = mul(z2n1, mul(z, z));
        const term = div(z2n1, fromInt(2 * n + 1));
        sum = add(sum, term);
        if (abs(term) < 1) break;
    }
    return mul(sum, fromInt(2));
}

/// sqrt via Newton
pub fn sqrt(x: Fixed) Fixed {
    if (x <= 0) return 0;
    var y = x;
    if (y < ONE) y = ONE;
    var i: u32 = 0;
    while (i < 32) : (i += 1) {
        // y = (y + x/y) / 2
        const t = add(y, div(x, y));
        const ny = div(t, fromInt(2));
        if (abs(sub(ny, y)) <= 1) {
            y = ny;
            break;
        }
        y = ny;
    }
    return y;
}

pub fn selfTest() bool {
    const one = fromInt(1);
    if (one != SCALE) return false;
    if (mul(fromInt(2), fromInt(3)) != fromInt(6)) return false;
    if (div(fromInt(6), fromInt(2)) != fromInt(3)) return false;
    // exp(0)=1
    if (abs(sub(exp(0), ONE)) > 2) return false;
    // cos(0)=1
    if (abs(sub(cos(0), ONE)) > 10) return false;
    // sqrt(4)=2
    if (abs(sub(sqrt(fromInt(4)), fromInt(2))) > 1000) return false;
    // pi from string
    const pi_ = fromDecimalStr("3.141592653589");
    if (abs(sub(pi_, fromRatio(3141592653589, 1000000000000))) > 2) return false;
    return true;
}
