"""Racing names. Every horse gets one, unique across the whole stud book (the living and the dead), at most
18 characters as the registry allows, plain letters only. A foal often echoes its family: it borrows a word
from its sire or its dam and pairs it with one of its own, so a line can be traced by ear.
Run: python names.py
"""
import random

_rng = random.Random(1849)   # its own stream: naming never shifts the race or breeding draws

FIRST = """Midnight Copper Silver Golden Western Northern Southern Eastern Royal Rapid Lucky Shady Silent Steady
Gallant Rebel Bold Brave Dusty Misty Stormy Sunny Rocky Rusty Wild Quiet Proud Swift Smoky Frosty Velvet Iron
Crimson Scarlet Amber Ivory Onyx Jade Cobalt Indigo Hickory Cedar Willow Maple Aspen Juniper Sterling Bronze Diamond
Captain Major Colonel Duke Baron Lady Miss Mister Sir Dame Count Chief Judge Senator Deacon Parson Doc Uncle Aunt
Country City Prairie Harbor River Valley Meadow Canyon Summit Desert Island Ocean Lake Bay Ridge Hollow Glen Ferry
Lightning Thunder Rainbow Comet Rocket Arrow Bullet Cannon Saber Lancer Ranger Drifter Rambler Rover Wanderer
Fancy Dandy Jolly Merry Happy Lively Sly Clever Noble Grand Little Big Old Young Lone Twin Double Triple High
Hidden Secret Magic Mystic Lucky Fortune Dream Spirit Shadow Echo Ghost Phantom Legend Myth Fable Saga Ballad Sonnet
Whiskey Bourbon Brandy Cider Coffee Cocoa Honey Ginger Pepper Clover Thistle Heather Ember Cinder Blaze Spark Flash
Turbo Diesel Express Rail Pacer Trotter Sulky Harness Paddock Stable Derby Classic Crown Royalty Empire Kingdom"""
SECOND = """Ledger Lane Road Trail Way Street Avenue Boulevard Crossing Bridge Gate Fence Post Mile Furlong Stretch
Express Special Delight Dancer Runner Flyer Charger Chaser Seeker Hunter Keeper Maker Breaker Rider Driver Dealer
Gambler Hustler Outlaw Bandit Rogue Rascal Pirate Sailor Soldier Knight Prince Princess King Queen Jester Bishop
Star Moon Sun Sky Cloud Rain Wind Storm Breeze Thunder Fire Flame Frost Snow Ice Stone Rock River Creek Spring
Song Tune Melody Rhythm Rhapsody Anthem Hymn Chorus Echo Whisper Promise Secret Wish Dream Hope Glory Pride Honor
Victory Triumph Fortune Treasure Jewel Gem Pearl Ruby Emerald Sapphire Opal Topaz Garnet Crystal Charm Spell Magic
Rose Lily Daisy Violet Iris Orchid Poppy Tulip Blossom Petal Ivy Fern Oak Pine Elm Birch Ash Thorn Briar Bramble
Hawk Falcon Eagle Raven Sparrow Robin Wren Lark Swallow Heron Fox Wolf Bear Lion Tiger Mustang Bronco Stallion Colt
Legacy Heritage Tradition Destiny Journey Voyage Quest Venture Adventure Odyssey Escape Dash Sprint Rush Bolt Blitz
Hall Farms Acres Ranch Valley Hill Hollow Downs Park Meadows Springs Point Ridge Heights"""
FIRST, SECOND = FIRST.split(), SECOND.split()
SHE = {"Lady", "Miss", "Dame", "Aunt", "Princess", "Queen", "Rose", "Lily", "Daisy", "Violet", "Iris", "Orchid", "Poppy", "Tulip"}
HE = {"Captain", "Major", "Colonel", "Duke", "Baron", "Mister", "Sir", "Count", "Chief", "Judge", "Senator", "Deacon",
      "Parson", "Doc", "Uncle", "Prince", "King", "Stallion", "Colt", "Knight", "Bishop", "Sailor", "Soldier"}
MAXLEN = 18
USED = set()


def _ok(n):
    return len(n) <= MAXLEN and n not in USED


def make(sire=None, dam=None, sex=None):
    """A fresh name; a foal borrows a word from a parent about half the time, more often from the sire. A filly is
    never 'Sir' or 'King', nor a colt 'Miss' or 'Queen'."""
    wrong = HE if sex == "f" else SHE if sex == "m" else set()
    words = [w for p in (sire, sire, dam) if p is not None for w in p.name.split() if (w in FIRST or w in SECOND) and w not in wrong]
    for _ in range(200):
        if words and _rng.random() < 0.5:
            w = _rng.choice(words)
            n = f"{w} {_rng.choice(SECOND)}" if w in FIRST else f"{_rng.choice(FIRST)} {w}"
        elif _rng.random() < 0.08:                        # now and then a three-word name, as the registry allows
            n = f"{_rng.choice(FIRST)} {_rng.choice(FIRST)} {_rng.choice(SECOND)}"
        else:
            n = f"{_rng.choice(FIRST)} {_rng.choice(SECOND)}"
        if _ok(n) and n.split()[0] != n.split()[-1] and not wrong & set(n.split()):
            USED.add(n)
            return n
    for k in range(2, 10 ** 6):                           # the book is full: a numeral, as real registries do
        n = f"{_rng.choice(FIRST)} {_rng.choice(SECOND)}"[:MAXLEN - 3].rstrip() + f" {k}"
        if _ok(n):
            USED.add(n)
            return n


def reserve(names):
    """A loaded game's names are taken: new foals can't reuse them."""
    USED.update(names)


if __name__ == "__main__":
    class P:
        def __init__(self, name): self.name = name
    a = [make() for _ in range(20000)]
    assert len(set(a)) == len(a) and all(len(n) <= MAXLEN and n.replace(" ", "").isalpha() for n in a if not n[-1].isdigit())
    s, d = P("Midnight Ledger"), P("Copper Rose")
    kids = [make(s, d) for _ in range(400)]
    echo = sum(any(w in k.split() for w in ("Midnight", "Ledger", "Copper", "Rose")) for k in kids) / len(kids)
    print(f"{len(a)} unique names, e.g. {a[:6]}; foals of Midnight Ledger x Copper Rose echo a parent {echo:.0%}: {kids[:5]}")
    assert 0.35 < echo < 0.7
    print("all checks passed")
