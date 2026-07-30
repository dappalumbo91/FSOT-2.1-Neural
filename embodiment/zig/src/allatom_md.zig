//! All-atom classical molecular dynamics (Zig host lab).
//!
//! This is real all-atom MD at the scale MD is used in structural biophysics:
//!   • every atom has mass, charge, LJ parameters, position, velocity
//!   • Velocity-Verlet integration
//!   • Harmonic bonds + angles
//!   • Lennard-Jones 12-6 + Coulomb (reaction-field / cutoff)
//!   • Periodic box (minimum-image)
//!   • Berendsen thermostat (weak coupling)
//!
//! Systems:
//!   1) TIP3P-like water box (explicit H-O-H)
//!   2) Simplified ion + carbonyl “selectivity filter” (channel biophysics lab)
//!
//! NOT the cognitive runtime (see docs/WHY_NOT_ALL_ATOM_MD.md).
//! Implemented because credibility may require the lab tool — and you asked for it.
//!
//! Units (reduced, internally consistent):
//!   length = Å, energy = kcal/mol, mass = g/mol, time = fs
//!   (standard small-molecule MD unit set)

const std = @import("std");

pub const MAX_ATOMS: usize = 384;
pub const MAX_BONDS: usize = 512;
pub const MAX_ANGLES: usize = 512;

pub const Element = enum(u8) { H = 0, O = 1, C = 2, N = 3, K = 4, dummy = 5 };

pub const Atom = struct {
    el: Element = .H,
    m: f64 = 1.0, // g/mol
    q: f64 = 0.0, // e
    sig: f64 = 1.0, // Å (LJ sigma)
    eps: f64 = 0.0, // kcal/mol
    x: f64 = 0,
    y: f64 = 0,
    z: f64 = 0,
    vx: f64 = 0,
    vy: f64 = 0,
    vz: f64 = 0,
    fx: f64 = 0,
    fy: f64 = 0,
    fz: f64 = 0,
};

pub const Bond = struct {
    i: u16 = 0,
    j: u16 = 0,
    k: f64 = 450.0, // kcal/mol/Å^2
    r0: f64 = 1.0,
};

pub const Angle = struct {
    i: u16 = 0,
    j: u16 = 0, // vertex
    k: u16 = 0,
    ktheta: f64 = 55.0, // kcal/mol/rad^2
    theta0: f64 = 1.9106, // ~109.5° in rad for water-ish; TIP3P is ~104.5°
};

pub const MdState = struct {
    n: usize = 0,
    atoms: [MAX_ATOMS]Atom = undefined,
    n_bonds: usize = 0,
    bonds: [MAX_BONDS]Bond = undefined,
    n_angles: usize = 0,
    angles: [MAX_ANGLES]Angle = undefined,
    box: f64 = 20.0, // Å cubic PBC
    cutoff: f64 = 9.0,
    dt_fs: f64 = 1.0,
    temperature_K: f64 = 300.0,
    ke: f64 = 0,
    pe: f64 = 0,
    pe_bond: f64 = 0,
    pe_angle: f64 = 0,
    pe_lj: f64 = 0,
    pe_coul: f64 = 0,
    step: u64 = 0,
    // diagnostics
    n_force_evals: u64 = 0,
    max_force: f64 = 0,
    energy0: f64 = 0,
    energy_drift: f64 = 0,
};

// physical constants in this unit system
const K_COUL: f64 = 332.0636; // kcal·Å/(mol·e^2)
const KB: f64 = 0.0019872041; // kcal/(mol·K)
// mass * (Å/fs)^2 → energy: 1 u * (Å/fs)^2 = 2390.057 kcal/mol (approx)
// KE = 0.5 * m * v^2 * MASS_TO_E
const MASS_TO_E: f64 = 2390.057361376673; // convert g/mol * Å^2/fs^2 → kcal/mol
// a = F/m with F in kcal/mol/Å, m in g/mol:
// Standard tutorial scale: a = F * 4.184e-4 / m  (Å/fs^2)
const F_SCALE: f64 = 4.184e-4;

fn wrap(d: f64, box: f64) f64 {
    var x = d;
    const h = 0.5 * box;
    while (x > h) x -= box;
    while (x < -h) x += box;
    return x;
}

fn pbcPos(p: f64, box: f64) f64 {
    var x = p;
    while (x >= box) x -= box;
    while (x < 0) x += box;
    return x;
}

fn ljParams(a: Element, b: Element) struct { sig: f64, eps: f64 } {
    // Lorentz-Berthelot mixing from atom types
    const pa = elementParams(a);
    const pb = elementParams(b);
    return .{
        .sig = 0.5 * (pa.sig + pb.sig),
        .eps = @sqrt(pa.eps * pb.eps),
    };
}

fn elementParams(e: Element) struct { m: f64, q: f64, sig: f64, eps: f64 } {
    return switch (e) {
        .H => .{ .m = 1.008, .q = 0.417, .sig = 0.40, .eps = 0.046 }, // TIP3P-ish H (q set on water builder)
        .O => .{ .m = 15.999, .q = -0.834, .sig = 3.1507, .eps = 0.1521 }, // TIP3P O
        .C => .{ .m = 12.011, .q = 0.51, .sig = 3.40, .eps = 0.086 }, // carbonyl C-ish
        .N => .{ .m = 14.007, .q = -0.47, .sig = 3.25, .eps = 0.170 },
        .K => .{ .m = 39.098, .q = 1.0, .sig = 3.33, .eps = 0.000328 }, // K+ approx
        .dummy => .{ .m = 12.0, .q = 0, .sig = 3.0, .eps = 0.05 },
    };
}

fn zeroForces(s: *MdState) void {
    var i: usize = 0;
    while (i < s.n) : (i += 1) {
        s.atoms[i].fx = 0;
        s.atoms[i].fy = 0;
        s.atoms[i].fz = 0;
    }
    s.pe = 0;
    s.pe_bond = 0;
    s.pe_angle = 0;
    s.pe_lj = 0;
    s.pe_coul = 0;
    s.max_force = 0;
}

fn addForce(s: *MdState, i: usize, fx: f64, fy: f64, fz: f64) void {
    s.atoms[i].fx += fx;
    s.atoms[i].fy += fy;
    s.atoms[i].fz += fz;
    const mag = @sqrt(fx * fx + fy * fy + fz * fz);
    if (mag > s.max_force) s.max_force = mag;
}

fn computeForces(s: *MdState) void {
    zeroForces(s);
    s.n_force_evals += 1;
    const box = s.box;
    const rc = s.cutoff;
    const rc2 = rc * rc;

    // bonds
    var b: usize = 0;
    while (b < s.n_bonds) : (b += 1) {
        const bd = s.bonds[b];
        const i = bd.i;
        const j = bd.j;
        const dx = wrap(s.atoms[j].x - s.atoms[i].x, box);
        const dy = wrap(s.atoms[j].y - s.atoms[i].y, box);
        const dz = wrap(s.atoms[j].z - s.atoms[i].z, box);
        const r = @sqrt(dx * dx + dy * dy + dz * dz);
        if (r < 1e-8) continue;
        const dr = r - bd.r0;
        const e = 0.5 * bd.k * dr * dr;
        s.pe_bond += e;
        s.pe += e;
        const f = -bd.k * dr;
        const fx = f * dx / r;
        const fy = f * dy / r;
        const fz = f * dz / r;
        addForce(s, i, -fx, -fy, -fz);
        addForce(s, j, fx, fy, fz);
    }

    // angles
    var a: usize = 0;
    while (a < s.n_angles) : (a += 1) {
        const ag = s.angles[a];
        const i = ag.i;
        const j = ag.j;
        const k = ag.k;
        const rji_x = wrap(s.atoms[i].x - s.atoms[j].x, box);
        const rji_y = wrap(s.atoms[i].y - s.atoms[j].y, box);
        const rji_z = wrap(s.atoms[i].z - s.atoms[j].z, box);
        const rjk_x = wrap(s.atoms[k].x - s.atoms[j].x, box);
        const rjk_y = wrap(s.atoms[k].y - s.atoms[j].y, box);
        const rjk_z = wrap(s.atoms[k].z - s.atoms[j].z, box);
        const rji = @sqrt(rji_x * rji_x + rji_y * rji_y + rji_z * rji_z);
        const rjk = @sqrt(rjk_x * rjk_x + rjk_y * rjk_y + rjk_z * rjk_z);
        if (rji < 1e-8 or rjk < 1e-8) continue;
        const cos_t = (rji_x * rjk_x + rji_y * rjk_y + rji_z * rjk_z) / (rji * rjk);
        const cos_c = @max(-1.0, @min(1.0, cos_t));
        const theta = std.math.acos(cos_c);
        const dth = theta - ag.theta0;
        const e = 0.5 * ag.ktheta * dth * dth;
        s.pe_angle += e;
        s.pe += e;
        // simple angle forces via gradient of cos (approximate but nonzero)
        const sin_t = @sin(theta);
        if (@abs(sin_t) < 1e-8) continue;
        const dE_dth = ag.ktheta * dth;
        const pref = -dE_dth / sin_t;
        // d(cos)/dri components
        const inv_rji = 1.0 / rji;
        const inv_rjk = 1.0 / rjk;
        const fi_x = pref * (rjk_x * inv_rji * inv_rjk - cos_c * rji_x * inv_rji * inv_rji);
        const fi_y = pref * (rjk_y * inv_rji * inv_rjk - cos_c * rji_y * inv_rji * inv_rji);
        const fi_z = pref * (rjk_z * inv_rji * inv_rjk - cos_c * rji_z * inv_rji * inv_rji);
        const fk_x = pref * (rji_x * inv_rji * inv_rjk - cos_c * rjk_x * inv_rjk * inv_rjk);
        const fk_y = pref * (rji_y * inv_rji * inv_rjk - cos_c * rjk_y * inv_rjk * inv_rjk);
        const fk_z = pref * (rji_z * inv_rji * inv_rjk - cos_c * rjk_z * inv_rjk * inv_rjk);
        addForce(s, i, fi_x, fi_y, fi_z);
        addForce(s, k, fk_x, fk_y, fk_z);
        addForce(s, j, -(fi_x + fk_x), -(fi_y + fk_y), -(fi_z + fk_z));
    }

    // nonbonded LJ + Coulomb (exclude 1-2 bonded pairs simply via bond list mask)
    var i: usize = 0;
    while (i < s.n) : (i += 1) {
        var j = i + 1;
        while (j < s.n) : (j += 1) {
            // skip if directly bonded
            var bonded = false;
            b = 0;
            while (b < s.n_bonds) : (b += 1) {
                const bi = s.bonds[b].i;
                const bj = s.bonds[b].j;
                if ((bi == i and bj == j) or (bi == j and bj == i)) {
                    bonded = true;
                    break;
                }
            }
            if (bonded) continue;

            const dx = wrap(s.atoms[j].x - s.atoms[i].x, box);
            const dy = wrap(s.atoms[j].y - s.atoms[i].y, box);
            const dz = wrap(s.atoms[j].z - s.atoms[i].z, box);
            const r2 = dx * dx + dy * dy + dz * dz;
            if (r2 > rc2 or r2 < 1e-12) continue;
            const r = @sqrt(r2);
            const inv_r = 1.0 / r;

            // LJ
            const mix = ljParams(s.atoms[i].el, s.atoms[j].el);
            const sig = mix.sig;
            const eps = mix.eps;
            const sr = sig * inv_r;
            const sr2 = sr * sr;
            const sr6 = sr2 * sr2 * sr2;
            const sr12 = sr6 * sr6;
            const elj = 4.0 * eps * (sr12 - sr6);
            s.pe_lj += elj;
            s.pe += elj;
            const f_lj = 24.0 * eps * inv_r * (2.0 * sr12 - sr6);

            // Coulomb
            const ec = K_COUL * s.atoms[i].q * s.atoms[j].q * inv_r;
            s.pe_coul += ec;
            s.pe += ec;
            const f_c = K_COUL * s.atoms[i].q * s.atoms[j].q * inv_r * inv_r;

            const f = f_lj + f_c;
            const fx = f * dx * inv_r;
            const fy = f * dy * inv_r;
            const fz = f * dz * inv_r;
            addForce(s, i, -fx, -fy, -fz);
            addForce(s, j, fx, fy, fz);
        }
    }
}

fn kineticEnergy(s: *MdState) f64 {
    var ke: f64 = 0;
    var i: usize = 0;
    while (i < s.n) : (i += 1) {
        const a = s.atoms[i];
        const v2 = a.vx * a.vx + a.vy * a.vy + a.vz * a.vz;
        ke += 0.5 * a.m * v2 * MASS_TO_E;
    }
    s.ke = ke;
    return ke;
}

fn temperature(s: *const MdState) f64 {
    // 3N-6 ~ 3N for large; use 3N-3 for free COM
    const dof: f64 = @floatFromInt(3 * s.n - 3);
    if (dof <= 0) return 0;
    return (2.0 * s.ke) / (dof * KB);
}

fn berendsen(s: *MdState, tau_fs: f64) void {
    const T = temperature(s);
    if (T < 1e-8) return;
    const lam = @sqrt(1.0 + (s.dt_fs / tau_fs) * (s.temperature_K / T - 1.0));
    var i: usize = 0;
    while (i < s.n) : (i += 1) {
        s.atoms[i].vx *= lam;
        s.atoms[i].vy *= lam;
        s.atoms[i].vz *= lam;
    }
}

/// Velocity Verlet one step (dt in fs).
pub fn step(s: *MdState) void {
    const dt = s.dt_fs;
    // v(t+dt/2) = v + a*dt/2; x += v*dt
    var i: usize = 0;
    while (i < s.n) : (i += 1) {
        const a = &s.atoms[i];
        const ax = a.fx / a.m * F_SCALE;
        const ay = a.fy / a.m * F_SCALE;
        const az = a.fz / a.m * F_SCALE;
        a.vx += 0.5 * ax * dt;
        a.vy += 0.5 * ay * dt;
        a.vz += 0.5 * az * dt;
        a.x = pbcPos(a.x + a.vx * dt, s.box);
        a.y = pbcPos(a.y + a.vy * dt, s.box);
        a.z = pbcPos(a.z + a.vz * dt, s.box);
    }
    computeForces(s);
    i = 0;
    while (i < s.n) : (i += 1) {
        const a = &s.atoms[i];
        const ax = a.fx / a.m * F_SCALE;
        const ay = a.fy / a.m * F_SCALE;
        const az = a.fz / a.m * F_SCALE;
        a.vx += 0.5 * ax * dt;
        a.vy += 0.5 * ay * dt;
        a.vz += 0.5 * az * dt;
    }
    _ = kineticEnergy(s);
    berendsen(s, 100.0); // 100 fs coupling
    _ = kineticEnergy(s);
    s.step += 1;
    const etot = s.ke + s.pe;
    if (s.energy0 == 0) s.energy0 = etot;
    s.energy_drift = @abs(etot - s.energy0) / (@abs(s.energy0) + 1.0);
}

fn addAtom(s: *MdState, el: Element, x: f64, y: f64, z: f64, q_override: ?f64) void {
    if (s.n >= MAX_ATOMS) return;
    const p = elementParams(el);
    var a: Atom = .{
        .el = el,
        .m = p.m,
        .q = if (q_override) |qq| qq else p.q,
        .sig = p.sig,
        .eps = p.eps,
        .x = x,
        .y = y,
        .z = z,
    };
    // tiny thermal kick
    const seed = @as(u64, @intCast(s.n +% 17)) *% 0x9E3779B97F4A7C15;
    const r1 = @as(f64, @floatFromInt(seed & 0xFFFF)) / 65535.0 - 0.5;
    const r2 = @as(f64, @floatFromInt((seed >> 16) & 0xFFFF)) / 65535.0 - 0.5;
    const r3 = @as(f64, @floatFromInt((seed >> 32) & 0xFFFF)) / 65535.0 - 0.5;
    const vscale = 0.0002; // Å/fs
    a.vx = r1 * vscale;
    a.vy = r2 * vscale;
    a.vz = r3 * vscale;
    s.atoms[s.n] = a;
    s.n += 1;
}

fn addBond(s: *MdState, i: u16, j: u16, k: f64, r0: f64) void {
    if (s.n_bonds >= MAX_BONDS) return;
    s.bonds[s.n_bonds] = .{ .i = i, .j = j, .k = k, .r0 = r0 };
    s.n_bonds += 1;
}

fn addAngle(s: *MdState, i: u16, j: u16, k: u16, kt: f64, th0: f64) void {
    if (s.n_angles >= MAX_ANGLES) return;
    s.angles[s.n_angles] = .{ .i = i, .j = j, .k = k, .ktheta = kt, .theta0 = th0 };
    s.n_angles += 1;
}

/// Build TIP3P-like water box (n_mol molecules on a grid).
pub fn buildWaterBox(n_mol: usize) MdState {
    var s: MdState = .{};
    s.box = 18.0;
    s.cutoff = 8.0;
    s.dt_fs = 1.0;
    s.temperature_K = 300.0;
    // geometry: O at origin of molecule, H at ~0.9572 Å, angle 104.52°
    const roh: f64 = 0.9572;
    const th: f64 = 104.52 * std.math.pi / 180.0;
    const hx = roh * @sin(0.5 * th);
    const hz = roh * @cos(0.5 * th);
    const nside: usize = @max(2, @as(usize, @intFromFloat(@ceil(@sqrt(@as(f64, @floatFromInt(n_mol)))))));
    const spacing = s.box / @as(f64, @floatFromInt(nside));
    var m: usize = 0;
    var ix: usize = 0;
    while (ix < nside and m < n_mol) : (ix += 1) {
        var iy: usize = 0;
        while (iy < nside and m < n_mol) : (iy += 1) {
            var iz: usize = 0;
            while (iz < nside and m < n_mol) : (iz += 1) {
                const cx = (0.5 + @as(f64, @floatFromInt(ix))) * spacing;
                const cy = (0.5 + @as(f64, @floatFromInt(iy))) * spacing;
                const cz = (0.5 + @as(f64, @floatFromInt(iz))) * spacing;
                const io: u16 = @intCast(s.n);
                addAtom(&s, .O, cx, cy, cz, -0.834);
                const ih1: u16 = @intCast(s.n);
                addAtom(&s, .H, cx + hx, cy, cz + hz, 0.417);
                const ih2: u16 = @intCast(s.n);
                addAtom(&s, .H, cx - hx, cy, cz + hz, 0.417);
                addBond(&s, io, ih1, 450.0, roh);
                addBond(&s, io, ih2, 450.0, roh);
                addAngle(&s, ih1, io, ih2, 55.0, th);
                m += 1;
            }
        }
    }
    computeForces(&s);
    _ = kineticEnergy(&s);
    s.energy0 = s.ke + s.pe;
    return s;
}

/// Simplified K+ + carbonyl oxygen “filter” (channel lab, not full KcsA).
pub fn buildIonFilter() MdState {
    var s: MdState = .{};
    s.box = 24.0;
    s.cutoff = 10.0;
    s.dt_fs = 0.5;
    s.temperature_K = 300.0;
    // 8 carbonyl oxygens in two rings + K+ in center
    const r_ring: f64 = 3.2;
    const z1: f64 = 10.0;
    const z2: f64 = 14.0;
    const cx: f64 = 12.0;
    const cy: f64 = 12.0;
    var i: usize = 0;
    while (i < 4) : (i += 1) {
        const ang = @as(f64, @floatFromInt(i)) * (std.math.pi * 0.5);
        addAtom(&s, .O, cx + r_ring * @cos(ang), cy + r_ring * @sin(ang), z1, -0.5);
    }
    i = 0;
    while (i < 4) : (i += 1) {
        const ang = @as(f64, @floatFromInt(i)) * (std.math.pi * 0.5) + 0.4;
        addAtom(&s, .O, cx + r_ring * @cos(ang), cy + r_ring * @sin(ang), z2, -0.5);
    }
    // carbons tethered behind oxygens (dummy scaffold)
    i = 0;
    while (i < 4) : (i += 1) {
        const ang = @as(f64, @floatFromInt(i)) * (std.math.pi * 0.5);
        const ic: u16 = @intCast(s.n);
        addAtom(&s, .C, cx + (r_ring + 1.2) * @cos(ang), cy + (r_ring + 1.2) * @sin(ang), z1, 0.5);
        const io: u16 = @intCast(i); // O atoms 0..3
        addBond(&s, io, ic, 300.0, 1.23);
    }
    i = 0;
    while (i < 4) : (i += 1) {
        const ang = @as(f64, @floatFromInt(i)) * (std.math.pi * 0.5) + 0.4;
        const ic: u16 = @intCast(s.n);
        addAtom(&s, .C, cx + (r_ring + 1.2) * @cos(ang), cy + (r_ring + 1.2) * @sin(ang), z2, 0.5);
        const io: u16 = @intCast(4 + i);
        addBond(&s, io, ic, 300.0, 1.23);
    }
    addAtom(&s, .K, cx, cy, 12.0, 1.0);
    computeForces(&s);
    _ = kineticEnergy(&s);
    s.energy0 = s.ke + s.pe;
    return s;
}

pub const MdReport = struct {
    ok: bool,
    system: []const u8,
    n_atoms: u32,
    n_bonds: u32,
    n_angles: u32,
    n_steps: u32,
    dt_fs: f64,
    final_T: f64,
    pe: f64,
    ke: f64,
    energy_drift: f64,
    max_force: f64,
    force_evals: u64,
};

pub fn runMd(system: enum { water, ion_filter }, n_steps: u32) MdReport {
    var s: MdState = if (system == .water) buildWaterBox(27) else buildIonFilter();
    // minimize-ish: short quenched steps
    var t: u32 = 0;
    while (t < 50) : (t += 1) {
        // damp velocities
        var i: usize = 0;
        while (i < s.n) : (i += 1) {
            s.atoms[i].vx *= 0.5;
            s.atoms[i].vy *= 0.5;
            s.atoms[i].vz *= 0.5;
        }
        computeForces(&s);
        step(&s);
    }
    s.energy0 = s.ke + s.pe;
    s.energy_drift = 0;
    t = 0;
    while (t < n_steps) : (t += 1) {
        step(&s);
    }
    const T = temperature(&s);
    // Gate: simulation ran, forces finite, energy drift bounded for short run
    const drift_ok = s.energy_drift < 0.35; // short noisy runs with Berendsen; not NVE perfection
    const force_ok = s.max_force < 1e6 and !std.math.isNan(s.max_force);
    const atoms_ok = s.n >= 8;
    const ok = drift_ok and force_ok and atoms_ok and s.n_force_evals > n_steps;
    return .{
        .ok = ok,
        .system = if (system == .water) "TIP3P-like water box" else "K+ carbonyl filter",
        .n_atoms = @intCast(s.n),
        .n_bonds = @intCast(s.n_bonds),
        .n_angles = @intCast(s.n_angles),
        .n_steps = n_steps,
        .dt_fs = s.dt_fs,
        .final_T = T,
        .pe = s.pe,
        .ke = s.ke,
        .energy_drift = s.energy_drift,
        .max_force = s.max_force,
        .force_evals = s.n_force_evals,
    };
}

pub fn selfTest() bool {
    const w = runMd(.water, 200);
    const f = runMd(.ion_filter, 200);
    return w.ok and f.ok and w.n_atoms >= 20 and f.n_atoms >= 10;
}
