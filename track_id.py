"""Each track's identity: its colors, its nameplate type, its badge and a motto, for the program, the replay and the rest."""

# id -> (primary, accent, type style, motto); the badge is mockups/brand/tracks/<id>.png
TRACKS = {
    "hp": ("#1d3f9a", "#f2c14e", "classic", "The flagship mile since the circuit began"),
    "rd": ("#0f766e", "#d6dde5", "pixel", "Where the good ones prove it"),
    "ml": ("#3f8f2f", "#f3ecd2", "pixel", "Spring starts here"),
    "gh": ("#4b5563", "#f97316", "pixel", "Tight turns, hard horses"),
    "bf": ("#c0262d", "#facc15", "fair", "Come for the fair, stay for the races"),
    "cr": ("#1e2a5a", "#ff5a6e", "classic", "Big city, big purses"),
    "ls": ("#3a8fd6", "#ffffff", "pixel", "Racing by the water"),
    "ng": ("#1f5f3a", "#a5e3f5", "pixel", "Cold nights, quick miles"),
    "sh": ("#c9a46a", "#c0562d", "pixel", "Deep sand, long stretch"),
    "pr": ("#2f5d3a", "#8b5a2b", "pixel", "Racing in the pines"),
}
FONT = {"classic": "'Cinzel',serif", "pixel": "'Jersey 10',sans-serif", "fair": "'Bungee',sans-serif"}


def look(vid):
    """(primary, accent, font stack, motto, badge path) for a track id; a plain default for anything unknown."""
    p, a, t, m = TRACKS.get(vid, ("#111a2b", "#e8a33a", "pixel", ""))
    return p, a, FONT[t], m, f"/mock/brand/tracks/{vid}.png"


assert len(TRACKS) == 10 and look("hp")[2].startswith("'Cinzel'")
