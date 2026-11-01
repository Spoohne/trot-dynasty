# Engine lab mandate

Given by Patrick on 2026-10-31.

> Develop and evaluate the race and breeding engines on the local copy. Preserve the live game. Run diagnostics,
> implement isolated prototypes, and resolve technical disagreements through experiments. Use an independent model
> reviewer at meaningful milestones. Ask Patrick only when a decision changes the intended player experience, affects
> existing player assets, requires spending beyond the agreed budget, or remains unresolved after three review rounds.
> Maintain a decision log and distinguish measured findings from hypotheses. Agreement between models is not
> evidence; test results must support recommendations.

## Roles

- **Claude (world-keeper):** runs the local copy, writes the engines and the test tools, runs every experiment, keeps
  this log. Never deploys, never edits the live save, never changes `app.py`/`circuit.py`/`sim.py`/`economy.py`
  behavior for the live game without Patrick's explicit go-ahead.
- **Astra (reviewer):** gpt-6-astra over the OpenAI API (`astra_review.py`), reviewing at milestones: methods, metrics,
  interpretations, and which experiment would settle a disagreement.
- **Patrick (owner):** decides player experience, existing player assets, budget, and anything unresolved after three
  review rounds.

## Ground rules

- Everything runs on the PC copy. The live server (trotdynasty.com) and its save are untouched by this work.
- Prototype code lives beside the game (`race2.py`) or in this folder; the game doesn't import it.
- A finding is **measured** only with the experiment, sample and spread that produced it. Anything else is a
  **hypothesis** and is labelled so.
- A disagreement is closed by an experiment designed to tell the two views apart, not by argument or agreement.
- Review budget: 25 API calls (`BUDGET_CALLS` in `astra_review.py`). Going past it needs Patrick's OK.
- Game rules that bind every recommendation: no coins buy horses or racing advantage; breeding outcomes are never
  secretly weakened; the Compendium shows no numbers or mechanics; American spelling.
