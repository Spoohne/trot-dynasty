# RaceGod targets

What "realistic" means, as numbers `audit.py` measures each night against. Each band says where it came from.
**Measured** bands come from published race summaries (`research/engine_lab/chart_targets.md`). **Hypothesis** bands are
RaceGod's starting guesses: Patrick confirms or changes them, and they stay labeled until real charts back them.
Calibration only: nothing here goes into game text.

Field sizes differ, so post figures are wins per start from posts 1 and 8 in fields of 8 or more.

```json
{
  "half_post1_win":      {"band": [19, 27], "basis": "measured: Canadian half-mile tracks, ~10,000 races; Yonkers 26.5%"},
  "half_post8_win":      {"band": [1, 6],   "basis": "measured: Canadian half-mile tracks 5.3%, Yonkers 6.1%, Buffalo 1.2%"},
  "mile_post1_win":      {"band": [15, 20], "basis": "soft: Rideau-Carleton, a five-eighths track (no true mile oval found)"},
  "mile_post8_win":      {"band": [6, 10],  "basis": "soft: Rideau-Carleton"},
  "winner_near_lead_at_half": {"band": [60, 90], "basis": "weak: Meadowlands, 9 of 13 and 12 of 15 within a few lengths at the half"},
  "half_winner_from_back":    {"band": [0, 15],  "basis": "weak: Yonkers winners are rarely back markers (described, not counted)"},
  "favorite_win":        {"band": [30, 45], "basis": "hypothesis"},
  "margin_median_l":     {"band": [1.0, 3.0], "basis": "hypothesis"},
  "photo_pct":           {"band": [5, 15],  "basis": "hypothesis: a photo is a winning margin of a neck or less (0.3 L)"},
  "limited_pct":         {"band": [0, 10],  "basis": "hypothesis: the speed limit should rarely overrule the model's margins"}
}
```

"Near the lead" is within 3 lengths of the leader at the half. A "back" winner sat 4 or more lengths off at the half.
