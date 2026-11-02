"""Outcome model v4 (OUTCOME_SPEC, DECISIONS 204-205): who wins, decided by a transparent model, vectorized over races.

    start order   e = gate' - c_post*(post-1) + s_start*z            (gate' = gate + form: form counts once)
    roles (fixed rules): top e leads; a second within DUEL of the top presses it (counted first-over, a duel);
                  the next tucks in the pocket; one mid-pack horse moves first-over (weighted by cruise), the next
                  N_FOLLOW in line take its cover (followed); the rest stay in line (back)
    performance   P = w_c*cruise' + w_k*kick' + A[role] + g*duel*(grit - rival grit) + s_eps*u - BREAK*broke
    result        order by P; margin (lengths) = s_margin*(P_win - P_i)

    python v4_outcome.py fit <track> [iters]      fit one track's parameters to the targets (writes v4/fit_<track>.json)
    python v4_outcome.py report <track>           the full report on untouched seeds"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "v4")
os.makedirs(OUT, exist_ok=True)
SD = 0.4                                     # trait spread within a class (the lab's one class)
ROLES = ("lead", "pocket", "first_over", "followed", "back")
DUEL, P_NONE, N_FOLLOW, A_FO, BREAK = 0.15, 0.10, 2, 6.0, 3.0   # A_FO 6: drivers send the horse with the most stamina   # fixed design rules (review 19)
N_STARTERS = {"half": 8, "mile": 10}
FO_MAX = {"half": 4, "mile": 5}     # first-over comes from mid-pack: start ranks up to this (0-based; Patrick's replay note, DECISIONS 213)
POST_T = {"half": [18.6, 14.9, 12.8, 12.0, 10.0, 7.6, 7.1, 5.9], "mile": [13, 12, 11, 11, 10, 10, 9, 9, 8, 7]}
TRIP_T = {"half": [35, 22, 15, 15, 13], "mile": [25, 18, 17, 20, 20]}
WORTH_T = {"half": dict(gate=.45, cruise=.35, kick=.20, grit=.0526), "mile": dict(gate=.20, cruise=.20, kick=.45, grit=.0458)}   # grit share 5% (DECISIONS 224)
RAIL_T = {"half": dict(lead=25, top3=79), "mile": dict(lead=None, top3=37)}
FIXED = dict(g=0.25, s_form=0.15, s_choice=0.1)   # g 0.25: grit fills gaps; a 10-vs-3 fight is worth ~2 bars of stamina (DECISIONS 224)   # s_choice: how imperfect drivers' trip choices are (design)          # design values, not fitted (review 20: g barely identified and saturating; form shapes the whole race)
NAMES = ("c_post", "s_start", "omega", "A_lead", "A_pocket", "A_fo", "A_fol", "s_eps", "s_margin", "k_close", "b_depth")
BOUNDS = [(0.0, 0.4), (0.0, 1.0), (0.05, 0.70), (-1.5, 1.5), (-1.5, 1.5), (-1.5, 1.5), (-1.5, 1.5), (0.02, 1.0), (1.0, 40.0),
          (0.0, 1.5), (0.0, 0.4)]
MIX = {"half": {8: .908, 7: .046, 6: .022, 5: .008, 4: .007, 3: .005, 2: .005},
       "mile": {10: .879, 9: .024, 8: .028, 7: .020, 6: .012, 5: .011, 4: .005, 3: .010, 2: .010}}
ABS = os.environ.get("V4_ABS") == "1"      # Pareto check: fit the contract's absolute worths instead of shares


def draws(N, n, seed, track=None, sd=SD):
    """Every random number one batch of races needs (common random numbers across settings). With a track, field
    sizes follow the live game's mix: posts past the field size are empty."""
    r = np.random.default_rng(seed)
    size = np.full(N, n) if track is None else r.choice(list(MIX[track]), N, p=np.array(list(MIX[track].values())) / sum(MIX[track].values()))
    return dict(traits=r.normal(0, sd, (N, n, 5)), form=r.normal(0, 1, (N, n)), z=r.normal(0, 1, (N, n)),
                u=r.normal(0, 1, (N, n)), gum=r.gumbel(0, 1, (N, n)), none=r.random(N), brk=r.random((N, n)),
                cg=r.gumbel(0, 1, (N, n, 5)),
                present=np.arange(n)[None, :] < size[:, None])


def race(p, D, track, traits=None, n=None):
    """Vectorized races. traits (N, n, 5): gate, cruise, kick, manners, grit. Returns P (N, n), roles (N, n), rank_e.
    Trips are chosen, not assigned (Patrick, DECISIONS 215: speed gives options, never obligations): in the order they
    come out of the gate, each driver takes the best trip still open to its horse (lead; pocket; first-over from
    mid-pack, or pressing the leader from second; following the first-over horse's cover; sitting in the line), with a
    little noise because drivers aren't perfect. A quicker horse picks earlier, so it has more options."""
    traits = D["traits"] if traits is None else traits
    N, n, _ = traits.shape
    f = D["form"] * p["s_form"]
    gate, cruise, kick, manners, grit = (traits[..., k] for k in range(5))
    gate, cruise, kick = gate + f, cruise + f, kick + f
    post = np.arange(n)[None, :]
    present = D.get("present", np.ones((N, n), bool))
    e = np.where(present, gate - p["c_post"] * post + p["s_start"] * D["z"], -1e9)
    order = np.argsort(-e, axis=1)                                  # order out of the gate
    rank = np.argsort(order, axis=1)
    rows = np.arange(N)
    es = np.take_along_axis(e, order, axis=1)
    w_k = 1 - p["omega"]
    A = np.array([p["A_lead"], p["A_pocket"], p["A_fo"], p["A_fol"], 0.0])
    cg = D.get("cg")
    if cg is None:
        cg = np.random.default_rng(0).gumbel(0, 1, (N, n, 5))
    role = np.full((N, n), 4)
    depth = np.zeros((N, n))
    lead = np.full(N, -1); pocket_taken = np.zeros(N, bool); mover = np.full(N, -1); followers = np.zeros(N, int)
    line_count = np.zeros(N)
    can_move = D["none"] >= P_NONE
    for k in range(n):
        h = order[:, k]
        live = present[rows, h]
        kh, gh = kick[rows, h], grit[rows, h]
        lg = np.where(lead >= 0, grit[rows, np.clip(lead, 0, None)], 0.0)
        v = np.full((N, 5), -np.inf)
        v[:, 0] = np.where(lead < 0, A[0] + w_k * kh, -np.inf)
        v[:, 1] = np.where(~pocket_taken, A[1] + w_k * kh, -np.inf)   # the first out may tuck and let the next one lead
        press = (k == 1) & ((es[:, 0] - es[:, 1]) < DUEL)            # second out, right with the leader: may press
        mid = (k >= 2) & (k <= FO_MAX[track]) & can_move
        v[:, 2] = np.where((mover < 0) & (press | mid), A[2] + w_k * kh + p["g"] * (gh - lg), -np.inf)
        v[:, 3] = np.where((mover >= 0) & (followers < N_FOLLOW), A[3] + (w_k + p["k_close"]) * kh, -np.inf)
        v[:, 4] = (w_k + p["k_close"]) * kh - p["b_depth"] * line_count
        pick = np.argmax(v + p["s_choice"] * cg[:, k, :], axis=1)
        pick = np.where(live, pick, 4)
        role[rows, h] = pick
        depth[rows, h] = np.where(pick == 4, line_count, 0)
        lead = np.where(live & (pick == 0), h, lead)
        pocket_taken |= live & (pick == 1)
        mover = np.where(live & (pick == 2), h, mover)
        followers += live & (pick == 3)
        line_count += live & (pick == 4)
    nolead = lead < 0                                               # nobody wanted it: the first one out leads anyway
    first = order[:, 0]
    role[rows[nolead], first[nolead]] = 0; depth[rows[nolead], first[nolead]] = 0
    lead = np.where(nolead, first, lead)
    moves = mover >= 0
    gdiff = np.zeros((N, n))
    lead_grit = grit[rows, lead]
    mg = np.where(moves, grit[rows, np.clip(mover, 0, None)], 0.0)
    gdiff[rows[moves], mover[moves]] = (mg - lead_grit)[moves]      # the head-and-head with the leader: grit decides
    gdiff[rows[moves], lead[moves]] = (lead_grit - mg)[moves]
    p_break = 0.005 * np.exp(-2.88 * manners)                       # the manners curve (DECISIONS 163)
    broke = D["brk"] < p_break
    closing = (role == 3) | (role == 4)
    P = (p["omega"] * cruise + (w_k + p["k_close"] * closing) * kick + A[role] - p["b_depth"] * depth + p["g"] * gdiff
         + p["s_eps"] * D["u"] - BREAK * broke)
    P = np.where(present, P, -1e9)
    return P, role, rank


def measures(p, track, D, Drep):
    """Every Part 1 measure for one parameter set on fixed draws (review 20: contracted definitions)."""
    N, n, _ = D["traits"].shape
    present = D["present"]
    P, role, rank_e = race(p, D, track)
    second = np.argmax(rank_e == 1, axis=1)
    win = np.argmax(P, axis=1)
    rows = np.arange(N)
    m = {}
    m["post"] = 100 * np.bincount(win, minlength=n) / np.maximum(1, present.sum(axis=0))   # wins per start
    m["trips"] = 100 * np.bincount(role[rows, win], minlength=5) / N
    m["rail_lead"] = 100 * np.mean(rank_e[:, 0] == 0)          # the start order, which holds to the half in this model
    m["rail_top3"] = 100 * np.mean(rank_e[:, 0] <= 2)
    srt = np.sort(P, axis=1)
    gap = (srt[:, -1] - srt[:, -2]) * p["s_margin"]
    m["margin_med"] = float(np.median(gap)); m["photo"] = 100 * float(np.mean(gap < 0.25))
    duel = role[rows, second] == 2                                  # the second horse out is pressing the leader
    place = np.argsort(np.argsort(-P, axis=1), axis=1)
    rs = np.random.default_rng(5)
    subj = np.floor(rs.random(N) * present.sum(axis=1)).astype(int)   # a horse that's in the race
    for k, name in ((0, "gate"), (1, "cruise"), (2, "kick"), (4, "grit")):   # +0.5 to one horse per race, same draws
        t2 = D["traits"].copy(); t2[rows, subj, k] += 0.5
        P2, _, _ = race(p, D, track, traits=t2)
        place2 = np.argsort(np.argsort(-P2, axis=1), axis=1)
        d = place[rows, subj] - place2[rows, subj]
        m[name] = float(np.mean(d))
        if name == "gate":
            m["gate_costs"] = 100 * float(np.mean(d < 0))       # extra gate speed lost places ("too quick for its own good")
            m["gate_gains"] = 100 * float(np.mean(d > 0))
    m["duel_rate"] = 100 * float(np.mean(duel))
    m["duel_margin"] = float(np.median(gap[duel])) if duel.any() else 0.0
    for key, R in (("class", Drep["class"]), ("mixed", Drep["mixed"])):
        F, K = R["F"], R["K"]
        Pr, _, _ = race(p, R["D"], track)
        w = np.argmax(Pr, axis=1).reshape(F, K)
        nn = R["D"]["traits"].shape[1]
        h1 = np.stack([np.bincount(w[f, :K // 2], minlength=nn) for f in range(F)])   # pick on one half of the reruns...
        h2 = np.stack([np.bincount(w[f, K // 2:], minlength=nn) for f in range(F)])   # ...score on the other
        cnt = h1 + h2
        if key == "class":
            m["repeat"] = 100 * float(np.mean((np.sum(cnt * cnt, axis=1) - K) / (K * (K - 1))))
            best1, best2 = h1.argmax(axis=1), h2.argmax(axis=1)
            m["best"] = 100 * float(np.mean((h2[np.arange(F), best1] + h1[np.arange(F), best2]) / K))
        else:
            pres = R["D"]["present"].reshape(F, K, nn)[:, 0, :]
            up = []
            for f in range(F):
                live = np.flatnonzero(pres[f]); k3 = -(-len(live) // 3)
                for a, b in ((h1, h2), (h2, h1)):
                    bottom = live[np.argsort(a[f, live], kind="stable")[:k3]]
                    up.append(b[f, bottom].sum() / (K // 2))
            m["upsets"] = 100 * float(np.mean(up))
    return m


def rerun_draws(F, K, n, seed, track=None, sd=SD):
    """F fields, each rerun K times with fresh form and luck (the same horses and posts)."""
    r = np.random.default_rng(seed)
    base = np.repeat(r.normal(0, sd, (F, 1, n, 5)), K, axis=1).reshape(F * K, n, 5)
    D = draws(F * K, n, seed + 1, track); D["traits"] = base
    if track is not None:                                       # one field size per field, kept across its reruns
        size = r.choice(list(MIX[track]), F, p=np.array(list(MIX[track].values())) / sum(MIX[track].values()))
        D["present"] = np.repeat((np.arange(n)[None, :] < size[:, None])[:, None, :], K, axis=1).reshape(F * K, n)
    return dict(F=F, K=K, D=D)


def rerun_sets(F, K, track, seed):
    """Item 6-7: one-class fields of 8 starters; items 4-5: mixed fields (spread 0.55) in the live size mix."""
    return dict(**{"class": rerun_draws(F, K, 8, seed)}, mixed=rerun_draws(F, K, N_STARTERS[track], seed + 7, track, 0.55))


def loss(m, track):
    """Zero inside each target's tolerance; squared, scaled excess outside it."""
    def band(x, lo, hi, scale):
        return 0.0 if lo <= x <= hi else ((lo - x if x < lo else x - hi) / scale) ** 2
    L = sum(band(x, t - 3, t + 3, 3) for x, t in zip(m["post"], POST_T[track]))
    L += sum(band(x, t - 6, t + 6, 6) for x, t in zip(m["trips"], TRIP_T[track]))
    tot, ttot = sum(m[k] for k in WORTH_T[track]), sum(WORTH_T[track].values())
    if ABS:                                                   # the contract's absolute worths
        L += sum(band(m[k], t - .08, t + .08, .08) for k, t in WORTH_T[track].items())
    else:                                                     # the balance's shape: each trait's share (DECISIONS 206)
        L += sum(band(m[k] / max(tot, 1e-6), t / ttot - .05, t / ttot + .05, .05) for k, t in WORTH_T[track].items())
    L += band(m["upsets"], 5, 11, 3)
    if RAIL_T[track]["lead"] is not None:
        L += band(m["rail_lead"], 17, 33, 8)
    L += band(m["rail_top3"], RAIL_T[track]["top3"] - 10, RAIL_T[track]["top3"] + 10, 10)
    L += band(m["repeat"], 39, 51, 6)
    L += band(m["margin_med"], 0.8, 2.0, 0.5) + band(m["photo"], 8, 17, 4)
    return L


def unpack(x):
    return dict(FIXED, **dict(zip(NAMES, x)))


def mono_set(track, M=24, K=600, seed=29):
    """Fixed fields for the per-horse check inside the fit: one horse per field, each bar raised by 1."""
    n = N_STARTERS[track]; r = np.random.default_rng(seed); out = []
    for f in range(M):
        t0 = r.normal(0, SD, (n, 5)); i = int(r.integers(n))
        D = draws(K, n, seed * 1000 + f); D["present"] = np.ones((K, n), bool)
        out.append((t0, i, D))
    return out


def mono_penalty(p, track, ms):
    """Sum of win-point drops beyond half a point when a bar is raised (0 when every bar only helps)."""
    pen = 0.0
    for t0, i, D in ms:
        K = D["u"].shape[0]
        D["traits"] = np.repeat(t0[None], K, 0)
        base = np.mean(np.argmax(race(p, D, track)[0], 1) == i)
        for k in (0, 1, 2, 4):
            t1 = t0.copy(); t1[i, k] += 0.2
            D["traits"] = np.repeat(t1[None], K, 0)
            d = 100 * (np.mean(np.argmax(race(p, D, track)[0], 1) == i) - base)
            pen += max(0.0, -d - 0.5)
    return pen


class Objective:
    """Picklable for parallel workers: the fixed training draws travel with it (common random numbers)."""
    def __init__(self, track):
        n = N_STARTERS[track]
        self.track, self.D, self.Drep = track, draws(3000, n, 11, track), rerun_sets(120, 24, track, 13)
        self.ms = mono_set(track)

    def __call__(self, x):
        p = unpack(x)                                           # every bar must only help (Patrick, DECISIONS 215)
        return loss(measures(p, self.track, self.D, self.Drep), self.track) + 0.5 * mono_penalty(p, self.track, self.ms)


def fit(track, iters):
    from scipy.optimize import differential_evolution
    res = differential_evolution(Objective(track), BOUNDS, maxiter=iters, popsize=12, seed=3, tol=1e-6, polish=False,
                                 workers=9, updating="deferred")
    p = unpack(res.x)
    json.dump(dict(params=p, loss=float(res.fun)), open(os.path.join(OUT, f"fit_{track}{'_abs' if ABS else ''}.json"), "w"), indent=1)
    print(track, "loss", round(res.fun, 3), {k: round(v, 3) for k, v in p.items()})


def monotone(p, track, M=60, K=2000, seed=71):
    """Per-horse check (DECISIONS 215): raise one bar by 1 (0.2 in trait units) for one horse in each of M fields;
    K reruns with the same luck. Returns the share of (horse, bar) cases where the win chance drops by more than
    half a point, the worst drop, and the average gain per bar."""
    n = N_STARTERS[track]; r = np.random.default_rng(seed)
    out = {}
    worst, bad, tot = 0.0, 0, 0
    for f in range(M):
        t0 = r.normal(0, SD, (n, 5)); i = int(r.integers(n))
        D = draws(K, n, seed * 1000 + f); D["present"] = np.ones((K, n), bool)
        D["traits"] = np.repeat(t0[None], K, 0)
        base = np.mean(np.argmax(race(p, D, track)[0], 1) == i)
        for k, name in ((0, "gate"), (1, "cruise"), (2, "kick"), (4, "grit")):
            t1 = t0.copy(); t1[i, k] += 0.2
            D["traits"] = np.repeat(t1[None], K, 0)
            d = 100 * (np.mean(np.argmax(race(p, D, track)[0], 1) == i) - base)
            out.setdefault(name, []).append(d); tot += 1
            bad += d < -0.5; worst = min(worst, d)
    return 100 * bad / tot, worst, {k: round(float(np.mean(v)), 2) for k, v in out.items()}


def report(track, p=None):
    p = p or json.load(open(os.path.join(OUT, f"fit_{track}{'_abs' if ABS else ''}.json")))["params"]
    n = N_STARTERS[track]
    D, Drep = draws(20000, n, 901, track), rerun_sets(400, 24, track, 903)      # untouched seeds
    m = measures(p, track, D, Drep)
    print(f"== {track} (untouched seeds; loss {loss(m, track):.2f})")
    print("   wins by post", [round(x, 1) for x in m["post"]], "target", POST_T[track])
    print("   trips (lead/pocket/fo/followed/back)", [round(x) for x in m["trips"]], "target", TRIP_T[track])
    tot, ttot = sum(m[k] for k in WORTH_T[track]), sum(WORTH_T[track].values())
    print("   places for +0.5:", {k: round(m[k], 2) for k in WORTH_T[track]}, "| shares", {k: round(m[k] / tot, 2) for k in WORTH_T[track]},
          "target shares", {k: round(t / ttot, 2) for k, t in WORTH_T[track].items()})
    print(f"   rail at the half (start order): leads {m['rail_lead']:.0f}%  top three {m['rail_top3']:.0f}%  | repeat {m['repeat']:.0f}% (39-51)"
          f" | best horse {m['best']:.0f}% (reported, split halves) | upsets {m['upsets']:.0f}% (5-11)")
    print(f"   margin median {m['margin_med']:.2f} L, photos {m['photo']:.0f}% | extra gate: gained places {m['gate_gains']:.0f}%, cost places {m['gate_costs']:.0f}%"
          f" | duels {m['duel_rate']:.0f}% of races, their median margin {m['duel_margin']:.2f} L | worth total {tot:.2f} (contract {ttot:.2f})")
    bad, worst, gain = monotone(p, track)
    print(f"   per-horse check: raising a bar by 1 cut the win chance by >0.5 pt in {bad:.0f}% of cases (worst {worst:.1f} pt);"
          f" average win-point gain per bar {gain}")
    return m


if __name__ == "__main__":
    if sys.argv[1] == "fit":
        fit(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 40)
    else:
        report(sys.argv[2])
