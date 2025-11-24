# BUS Core – Method / Process SoT (Offshoot v0.2.2)  
(The Real Story: How a Guy With Zero Training Built a Local-First ERP Using Only LLMs and Refusal to Stop)

This document is the **single source of truth for the method**.  
The technical product SoT remains canonical for what the code actually does.  
This one is canonical for **how** it got built and **how** you can do it again.

This version expands the method SoT from a mostly technical process log into my **personal method “bible”**: part workflow, part portfolio, part journal of how this actually felt and what I learned.

---

## 0) Authority, Scope & Versioning (locked)

- If this doc contradicts your memory of the process → **this doc wins** until you update it.  
- If this doc contradicts the **technical BUS Core SoT** → technical SoT wins.  
- Anything not written here is **“not specified in the method”**.

### 0.1 Version number format (X.Y.Z)

All method documents (and, ideally, all SoTs and specs going forward) use:

- **X – Release track**  
  - 0 = pre-“official teaching release” (internal method, in flux)  
  - 1 = first formal, public/teaching release of the method  
  - 2+ = later major eras (e.g., big rewrites, new stacks, etc.)

- **Y – Document / product major version**  
  - Increment when structure or meaning changes in a way that could confuse someone on an old version  
  - Example triggers:
    - New major sections added or removed  
    - Rules rewritten or reversed  
    - Core definitions changed

- **Z – Iteration / patch**  
  - Increment for **every change**, no matter how small:
    - Typos
    - Wording tweaks
    - Reordering
    - Added TODOs
  - Z is effectively unbounded (0, 1, 2, …).

This file is currently **v0.2.2**:

- `0` = pre-public, internal method track  
- `2` = second major structure of the method (includes orchestration, generalization, and personal/teaching intent)  
- `2` = second patch on that structure (documented how the first SoT was forged from the repo itself)

### 0.2 Versioning rules (non-optional)

- **Any modification to this document** – including typo fixes, formatting, word changes, reordering, or added TODOs – **MUST**:
  - bump the **Z** component at minimum (e.g., `0.2.2 → 0.2.3`), and  
  - append a new, dated entry in the **Changelog** (§22) describing what changed.
- If you make a structural or conceptual change that would confuse someone reading an older version:
  - bump **Y** and reset Z to 0 (e.g., `0.2.9 → 0.3.0`), and log it.
- Only change **X** when you intentionally declare a new release track:
  - e.g., “internal method” → “public teaching method” → “method v2 on new architecture”.
- **Never edit an old version in place.**  
  - When updating, copy forward the latest version, bump `X.Y.Z` as needed, and log changes.
- If multiple copies of this file exist:
  - The **highest version number** (by X, then Y, then Z) is the current canonical Method SoT.  
  - Older versions are **archives only** and must not be edited.

This is not polished marketing.  
This is the working record of *how the thing really got built*.

### 0.3 Why This Document Exists (Author’s Intent)

This Method SoT is not here to impress anyone. It exists for three reasons:

1. **Future Me**  
   This is my **personal bible** for the method — how I think, how I build, and what actually worked when BUS Core went from nothing to a real, running system.  
   It’s my memory backup: a logbook, a proto-wiki, and the place I can come back to when I forget how I pulled this off the first time.

2. **Future Builders**  
   If someone who doesn’t know how to code wants to build something real using LLMs without getting lost in hype, gatekeeping, and “AI prompt bundles”, this document should give them enough **facts, patterns, and scars** to stand on my shoulders instead of starting from zero.  
   Not because I think I’m special — just because I’ve already paid the cost in time, frustration, and late nights.

3. **Future Teaching / Portfolio**  
   If I ever use this work to teach, consult, or get a job or funding, this is the **canonical record** of what actually happened.  
   Not a polished narrative after the fact.  
   Not a fake hero story.  
   Just the receipts: the loop, the controls, the failures, the thinking, the emotional reality, and the method that made it repeatable.

I often feel silly writing this, like it might read as pompous or self-important.  
But it feels right to document it anyway.

If a section ever feels like ego or fluff, it should be rewritten until it is just:

> **What I did. What happened. What I learned. What someone else could reuse.**

---

## 1) The Core Loop (the only thing that actually matters)

1. Ask an LLM for the next chunk of code / design / refactor  
2. Force it to update the living Source of Truth **before** it is allowed to give code  
3. Apply the change (PR, patch, or direct)  
4. Run smoke → must stay green (launch, hit endpoints, validate persistence)  
5. Commit / merge  
6. Repeat, over and over

Key facts (public side):

- Public repo: https://github.com/truegoodcraft/TGC-BUS-Core

The exact day count and commit velocity for the *pre-GitHub* phase are not yet fully reconstructed.  
For now, the method treats it as:

> “Run that loop as many times per day as life allows, for weeks, without breaking it.”

Everything else in this document is a side effect of never letting that loop die.

---

## 2) The Five Controls That 99.9% of People Never Use

| Control                                 | What it actually does                                           | Why almost nobody does it                               | Real effect (observed)                                  |
|-----------------------------------------|------------------------------------------------------------------|---------------------------------------------------------|---------------------------------------------------------|
| **Living Source of Truth (SoT)**        | Single markdown/core doc that must be patched before code lands | “Too much paperwork”, “I’ll remember”                   | Kills drift, naming wars, and schema hallucinations     |
| **Update-SoT-First rule**              | LLM is literally not allowed to output code until SoT is updated| People rarely think to *handcuff* the model            | Forces models to read their own prior work              |
| **Smoke that restarts the server**      | Full end-to-end validation after each change                    | “Too slow”, “I’ll just click around”                    | Makes regressions visible immediately                   |
| **One-letter branch switch (`p branch`)** | Instant checkout + fetch of any branch                        | Many people re-clone or click UIs every time           | Removes setup/teardown friction completely              |
| **“Too dumb to stop” as a feature**     | No ego protection, no “real engineers don’t do it this way”     | Trained devs defend their schooling & patterns         | Ignores 20 years of cargo-cult rules that slow others   |

The method is not “be clever”.  
The method is: **lock in these controls and keep turning the crank.**

---

## 3) What Zero Training Gave Me (the actual unfair advantages)

| Problem most trained devs have          | I never had it because…                                 | Result                                          |
|-----------------------------------------|---------------------------------------------------------|-------------------------------------------------|
| Architecture astronauts                 | Didn’t know big design up front was “mandatory”        | Shipped instead of debating for months          |
| Framework religion                      | Had zero opinion on React vs Vue vs htmx               | Picked whatever worked fastest *that day*       |
| Impostor syndrome about patterns        | Never learned them                                      | No paralysis — just made it work                |
| Fear of “ugly” code                     | Didn’t know what “ugly” was supposed to look like      | Ruthless pragmatism that actually shipped       |
| Over-engineering for hypothetical scale | Had no sense of “scale” yet                            | Stayed minimal, local-first, fast to iterate    |

Accidental advantage: by skipping the “proper curriculum”, I also skipped most of the **brakes** that curriculum installs.

---

## 4) Roadblocks I Hit That Trained Devs Almost Never See

| Roadblock                                   | Why it normally kills solo AI projects                  | How I survived                                          |
|--------------------------------------------|----------------------------------------------------------|---------------------------------------------------------|
| Constant model drift / hallucinated schemas| Most people accept it, then refactor forever            | SoT + “update first” rule turned models into one coherent dev team |
| 4 a.m. rage sessions when smoke was red    | Normal humans quit                                       | Treated red smoke as the only authority and kept going  |
| Throttling / quota walls across providers  | Most users never push that hard, give up when throttled | Rotated models like ammo belts and kept the loop running|
| Zero external validation for weeks         | Solo devs usually need likes / feedback to keep going   | Green smoke became the only dopamine that mattered      |
| Windows path / AppData hell                | Many people silently accept fragile paths               | Kept hammering until paths were canonical and testable  |

Unusual *non*-problems (things I didn’t have to fight):

- No legacy team, no old patterns to defend  
- No stakeholder meetings or Jira process to satisfy  
- No performance marketing or launch deadline distorting decisions  

That let the loop stay **brutally simple**.

---

## 5) What I’m Doing That’s Still Rare (as of late 2025)

1. Treating LLMs as **junior devs who must check in design docs** before touching code  
2. Using **smoke failure**, not feelings, as the only “this is broken” signal  
3. Shipping a real local-first product *while learning the stack live*  
4. Maintaining a living, enforceable SoT that gets patched before the code does  
5. Building licensing tiers, encrypted export/import, manufacturing endpoints, a tray launcher, and path migrations with **LLM-driven PRs only**, no local hand-coding

I am not claiming I’m the “only one in the world” doing it.  
But this specific combo — SoT-first, smoke-gated, LLM-as-junior-dev, no prior experience — is **objectively rare**.

---

## 6) What I’m NOT Doing (that everyone else wastes time on)

- Writing big design docs *before* touching anything concrete  
- Arguing about frameworks on Discord / Reddit  
- Premature optimization or architecting for hypothetical scale  
- Seeking permission, approval, or validation before changing direction  
- Obsessing over “best practices” that don’t ship working code  
- Spending hours on YouTube tutorials instead of pushing one more green smoke

---

## 7) Verified Public Receipts (as of 2025-11-23)

These are the **public, checkable numbers** backing the story.

- **Repo:** `truegoodcraft/TGC-BUS-Core` on GitHub  
- **Closed PRs (Codex/GitHub loop):**
  - Pull Requests tab with filter `is:pr is:closed` shows  
    **0 Open / 336 Closed**.  
  - For this method SoT, those **336 closed PRs** are the canonical count of “loop iterations” from the start of the Codex+GitHub workflow up to the first public MVP.
- **Account-level activity (GitHub profile):**
  - “**1,047 contributions in the last year**” (profile header).  
  - Under **November 2025**:  
    “**Created 239 commits in 1 repository**” (that repository is BUS Core).
- **Smoke harness:** `buscore-smoke.ps1` in the repo root (plus `scripts/dev_bootstrap.ps1` as dev launcher) is the canonical test gate for each loop.

If future snapshots show different numbers (more PRs, more commits), those must be treated as activity **after** this MVP window unless this section is explicitly updated with a new version and Changelog entry.

---

## 8) Missing Pieces I Still Need to Write

These are **TODO hooks** for future versions of this Method SoT:

- Exact log of one 4 a.m. rage-quit smoke failure night:
  - What broke  
  - What I tried  
  - What finally fixed it  
  - What I felt before/after
- The day I realized **SoT was the real product**, not the code  
- The first time smoke went green after being red for hours straight  
- How many times I almost quit and didn’t (with specific dates and reasons)  
- A clear section on how this felt **emotionally**: exhaustion, doubt, stubbornness, why I kept turning the handle  
- A comparison of **LLM behaviours**:
  - How GPT, Grok, and Claude “feel” different in practice  
  - Where each tends to hallucinate or over-confidently riff  
  - How I route different tasks to different models

Until those are written, they are **not specified**; this list is here to remind me where the story is still missing meat.

---

## 9) Why This Is Worth Teaching

This method shows, with public receipts, that in 2025:

- You do **not** need:
  - A CS degree  
  - A bootcamp  
  - A team  
  - A detailed roadmap  

- You *do* need:
  1. A Source of Truth the model is forced to respect  
  2. A smoke test that the model is forced to pass  
  3. The willingness to keep turning the handle when you’re tired and annoyed

Two extreme takes are both wrong:

- **“AI will steal all the jobs”** → assumes typing “make me rich” is enough  
- **“AI is just slop/hype”** → only sees prompt spam and vibe-coded junk

This method is the **third path**:

> A regular person, with no formal training, using LLMs as slightly drunk junior devs, backed by a hard SoT and a hard smoke test, can quietly out-ship both camps.

The point is not that I’m special.  
The point is that the **loop** is special.

---

## 10) Inputs & Cost (Non-time)

For the method SoT, money matters because it proves the barrier really is low.

**Direct spend for this run (to be refined if needed):**

- GPT Pro (ChatGPT Plus) for ~2 months  
- Grok Pro for ~2 months  

> “My cost is the price of GPT Pro and Grok Pro for 2 months. That’s it.  
> No other money or YouTube tutorials or time spent other than brainstorming my plan, chatting with AI, and documenting.”

No paid bootcamps.  
No paid “learn to code” coursework.  
No extra tooling subscriptions beyond normal OS + basic dev stack.

Time cost = every margin of time I was willing to throw at the loop.

---

## 11) How I Talk to the Models (Real Quotes, Real Pattern)

These quotes are here to remind future-me how I actually steer the models in practice.

**Correcting wrong assumptions**

> “No you are wrong  
>   
> Apply changes via Codex  
>   
> ***Edit files in D:\BUSCore-Test (you’re on feature/short-name).****  
>   
> The edit in D:\ is wrong. I never edit locally. CODEX will be applying PR to a branch in Github… that way i never have to touch code or file and just manage where Codex is pointed on Github.”

**Enforcing SoT over vibes**

> “No, But i need to update the SOT to reflect the DB structure to avoide any drift or halucinations in the future.  
> Now output the entire SOT with these modifications and full notations on changes.”

**Treating some LLMs as unreliable narrators**

> “Do not treat the quoted information as Cannonical. It is from Grok who likes the halucinate increadably confidantly. *notate that id like to describe the llms difrences i have seen*”

**Controlling how code is used**

> “ok, i will never had you ‘code’ to use. Just detailed descriptions on how to structure the code learnt from other sorces.  
> Also, I can hand you code for files to get you to give me a cicinct description of fucntion or structure etc. not ‘use this code’”

**Demanding SoT-level logging**

> “I Need you to log all changes / updates and mark anything that **Should** become canonical in SOT to protect us and other in the future…”

Pattern:

- I **correct** the model bluntly when it’s wrong  
- I **elevate SoT** above any single answer  
- I treat **some models as idea generators**, not authorities  
- I constantly ask for **structure and logs**, not just “answers”

This behaviour is part of the method.  
The loop only works because I am willing to argue with the models and force them to align with the SoT.

---

## 12) The Method in One Sentence

> Lock a Source of Truth and a smoke test in front of the LLM,  
> then be stubborn enough to keep turning the handle until something real exists.

This method is now its own machine.  
I just turn the handle.

---

## 13) The Orchestration Principle (Who’s Actually in Charge)

The core fact:

> **The LLM is not the intelligence. I am.  
> The LLM is the typing pool, wired to a giant library.**

The method is not about “letting AI build an app”.  
The method is about **orchestrating** a predictive engine like you would orchestrate a very fast, very literal junior team.

Practical consequences:

- The model does not decide architecture — the SoT and my constraints do.  
- The model does not decide naming — the vocabulary section and my corrections do.  
- The model does not decide when we’re done — the smoke test and my requirements do.

This means:

- Any reasonably capable LLM can be slotted into this method.  
- Multiple different LLMs can be rotated without losing coherence, **as long as they all read and respect the same SoT**.  
- In theory, a team of human devs could be dropped in and the process would still work: SoT-first, smoke-gated, incremental.

The “novelty” here is not a model trick.  
The novelty is: **treating all agents (human or machine) as replaceable executors inside a fixed process that I control.**

---

## 14) LLMs as Prediction Engines (Not “AI”)

This method explicitly rejects the idea that these tools are “intelligent teammates”.

> “It’s not an AI. It’s a prediction machine with a lot of information behind it.  
> The better you can give it scope, the better it can predict what you want.”

Working assumption:

- The model is a **probability machine**, not a mind.  
- When it has to guess the context, results get sloppy (“AI slop”).  
- When the context is fully specified in SoT + prompt, results become boringly reliable.

So the method is built around:

- **Scope first**: always define vocabulary, entities, folder structure, and constraints.  
- **Prediction second**: ask for very specific outputs (one file, one refactor, one schema tweak).  
- **Verification third**: smoke + my own reading.

If you treat a prediction engine like a wise partner, it will disappoint you.  
If you treat it like a very fast autocomplete with rules, it will quietly ship software for you.

Calling it a “prediction engine” is not an insult.  
It’s a **safety rail**.

---

## 15) The Exponential Expandability Principle

One of the quiet design rules of this project:

> Every piece should survive future depth without having to be ripped out.

In practice that meant:

- DB schema designed so that adding new tables or fields doesn’t require a rewrite  
- UI built so sections can grow from “basic list” to “full management screen” without throwing it away  
- Folder structure that can handle more apps, more modules, more agents  
- SoT designed so new sections can be bolted on, not woven in with surgery

I never assumed:

- “This is the final version”  
- “This has to be perfectly designed now”  

Instead, the rule was:

> “Do a quick, clean pass that will survive the next 10 passes.”

This is what I mean by **exponentially expandable**:

- You can go 1 level deep and it still works.  
- You can go 10 levels deep and nothing snaps, because nothing was over-fitted to version 1.

This is why I wasn’t constantly rebuilding from scratch.  
Everything was **additive and incremental**, not destructive.

---

## 16) The Emotional Engine of the Method

This isn’t “grindset” talk. It’s logistics.

The method only worked because of a specific emotional posture:

- **Stubbornness over motivation**  
  - Smoke is red → fix it.  
  - Too tired → do a smaller iteration, but don’t vanish.  
- **No ego about “being a real dev”**  
  - I never needed to prove I was doing it the “proper” way.  
- **Comfort with not understanding the internals**  
  - I let the tests and behaviour tell me if it worked, not my ego about code literacy.  
- **Willingness to argue with the models**  
  - “No, you are wrong.” was a normal part of the loop, not a crisis.

Green smoke became the reward. Not likes, not retweets, not other people’s opinions.

If someone tries to copy this method but quits whenever:

- the model hallucinates  
- the test fails  
- Git yells  
- or they “don’t feel smart enough that day”

…then the loop breaks.  
Emotionally, the method is:

> “Be just too dumb to stop, but smart enough to keep the rails tight.”

---

## 17) Repeatability Across Projects

This method is **not BUS-Core-specific**.

Key claim:

> “I can restart on ANY project now with the same results, without a roadmap or a plan, just putting it together as I go.”

Because the core loop and controls are stack-agnostic:

- New domain? → Update SoT with new vocabulary and entities.  
- New language / framework? → Have the model scaffold it, but keep smoke and SoT.  
- New product idea? → Same loop: design → SoT → small change → smoke → commit.

What changes:

- The SoT contents  
- The smoke details  
- The repo and assets

What does **not** change:

- SoT-first rule  
- “AI as junior dev, not architect”  
- Prediction-engine mindset  
- Incremental, additive passes  
- Emotional engine (stubbornness + low ego)

So this document is not just “how BUS Core was built”.  
It is the **portable method SoT** for future builds.

---

## 18) AI as Team Compression, Not Replacement

This is one of the most important realities:

> “If you gave me a team of experts instead of GPT, the end result would have been the same.  
> GPT didn’t make me a coder — it made the cost of having a team effectively zero.”

The method assumes:

- In a traditional dev shop, I’d be the weird non-dev product owner / director.  
- I’d be telling a backend, a frontend, a DBA, and a DevOps person what I wanted.  
- I’d still be enforcing rules, naming, and behaviour.  
- It would still be SoT + tickets + tests + reviews.

LLMs compressed that team into:

- One interface  
- Many “personas”  
- Lots of cheap, fast iterations

They did **not** replace thinking.  
They replaced:

- boilerplate  
- typing  
- copying patterns  
- repetitive refactors  
- applying the same change across 10 files

So this method is not:

> “AI did it for me.”

It’s:

> “I ran a full-stack software team in my browser, for the cost of two pro subscriptions.”

---

## 19) What This Method is NOT

To avoid confusion, this method is **not**:

- A clever prompt template  
- A “secret sauce” for getting models to do magic  
- A guarantee that the code is perfect  
- A marketing funnel for a course  
- A productivity hack you can use once and forget  
- A way to avoid thinking

It explicitly **does not** rely on:

- One particular model  
- One stack or framework  
- Me being secretly trained as a dev

If someone tries to turn this into:

- “Just paste this prompt and get rich”  
- “Here’s the exact spell to cast on GPT”

…they’ve missed the point.

The method is:

- A **discipline**  
- A **loop**  
- A **set of rails**  
- A willingness to turn that handle way past the point normal people get bored

Nothing here is mystical.  
It’s just consistent.

---

## 20) Why This Method Actually Works (Meta Summary)

This is the “why” in one place:

The method works because:

- **SoT removes drift**  
  - The model is always working from one shared brain, not 100 detached prompts.
- **Smoke removes delusion**  
  - Feelings don’t matter; if the app can’t boot and do basic flows, it’s broken.
- **LLMs are treated as tools, not oracles**  
  - They predict under constraint instead of hallucinating under ambiguity.
- **Everything is additive**  
  - No big rewrites, just layers. Each pass is survivable by the next one.
- **The architecture is behaviour-driven**  
  - If it passes smoke and matches SoT, it’s good enough for that iteration.
- **The emotional loop is stable**  
  - Stubbornness + green-smoke dopamine beats self-doubt + perfectionism.
- **The cost is low enough to be sustainable**  
  - Two pro subs and spare time, not a $50k bootcamp or a dev salary.
- **The process is model-agnostic**  
  - Any capable LLM can plug in if it respects SoT and passes smoke.

The point is not that this is “the best” way to build software.  
The point is that this is a **proven, repeatable way for a non-dev to build real, maintainable software** in 2025.

---

## 21) The Hierarchy of Truth (Code → SoT → AI → Me)

This section captures how I actually think about “what’s real” in the project.

> “Code is fact. SoT describes code. Anything not proven in the code is speculation at best.  
> If it doesn’t fit those categories, it’s a planned future / idea.”

The hierarchy:

1. **Code (Ground Truth)**  
   - Whatever is in the repo and passes smoke is **canonical reality**.  
   - If the SoT disagrees with the code, **the SoT is wrong** and must be updated.  
   - If AI disagrees with the code, **AI is wrong**.  
   - If I *feel* like it should be different, it’s still wrong until I change the code and get green smoke.

2. **SoT (Description of Truth)**  
   - SoT exists to **describe** the current and intended system.  
   - It must be **100% aligned** with the code for anything that already exists.  
   - SoT can also contain:  
     - **Planned future**: clearly marked as not implemented yet  
     - **Open questions**: clearly labelled as undecided  
   - If something is in SoT but not in code, it is **design**, not reality.

3. **AI (Executor / Assistant)**  
   - AI is **never** a source of truth.  
   - It reads the SoT and code, then proposes changes.  
   - Its output is only accepted if:  
     - It fits the SoT  
     - It compiles/runs  
     - It passes smoke  
   - If I suspect drift, I sometimes make AI quote actual code or DB schema back to me as part of the “truth chain” before we move.

4. **Me (Judgment / Feeling / Direction)**  
   - I am the **source of decisions**, values, UX choices, and constraints.  
   - My feelings (this is ugly / this is nice / I don’t trust this) are inputs to **future design**, not a replacement for tests.  
   - When I make a design decision, it should land in the SoT.  
   - Once it is in SoT and implemented in code, it becomes reality.

This hierarchy is how I avoid “AI slop” and hallucinated systems.

I trust, in order:

> **Code → SoT → AI → Me (for feelings, direction, and values).**

This is also why I never needed a “500 Prompt Mega Bundle”. For most of the build:

- I used **3–4 core prompt structures**, recycled and refined.  
- When I thought there was drift, I brought the **actual code and SoT back into context**, not a fresh “clever prompt”.

The method is not a library of spells.  
It is a **tight feedback loop between code, SoT, AI, and my judgment**.

### 21.1 How the First SoT Was Forged (Reverse-Mapping the Repo)

The SoT did not start as a grand plan.  
It started as a **panic response to drift**.

At one point:

- I could no longer tell which behaviours came from which files.  
- Different LLM sessions had pulled the design in slightly different directions.  
- I had “unknown damage” — changes I couldn’t fully trace or explain.  
- I genuinely didn’t know **what was true** anymore.

So I did the only sane thing left:

1. **Used Codex to explain every part of the codebase back to me.**  
   - File structure: which folders exist, what lives where.  
   - For each file: what it does, which entities it touches.  
   - Endpoints: what URLs exist, what handlers they map to, what they depend on.  
   - DB pieces: which models are where, how they relate.

2. **Built a modular, “exploded view” of the repo.**  
   - Not prose.  
   - Not vibes.  
   - Just short, factual bullets of:
     - “This file does X.”  
     - “This endpoint calls Y.”  
     - “This model contains fields A, B, C.”

3. **Promoted those facts into the first SoT.**  
   - The initial SoT was **not** “what I wanted BUS Core to be”.  
   - It was a compact, technical list of **what BUS Core already was** according to the code.

4. **Only after that did I start adding “what I want”.**  
   - Once the “what IS” side was stable, I could layer “what SHOULD BE” on top.  
   - The loop became:
     - Fact: from code → SoT  
     - Desire: from me → SoT as planned change  
     - Implementation: AI edits code → smoke verifies → SoT updated again.

5. **Used the SoT map to clean house.**  
   - I spent roughly a week doing almost nothing but:
     - removing redundant / drifted code paths  
     - stripping out dead experiments  
     - deleting files that no longer matched any SoT-described behaviour  
   - Because I had a **map**, I could:
     - see which files were never referenced  
     - confidently remove garbage without fear of mysterious breakage  
     - bring the repo back into alignment with itself.

That was the moment BUS Core stopped being “accumulated AI output” and became **an engineered system with a map**.

Practical takeaway for future projects:

> If you ever reach the “unknown damage” stage again,  
> **start by exploding the repo into a factual SoT from the code outward**,  
> then re-layer your design and let the loop resume from there.

---

## 22) Changelog (Method SoT Versions)

> **Rule:** Every change to this document requires a new entry here.  
> If there is no Changelog entry for a change, that change is not legitimate.

- **v0.2.2 – 2025-11-23**  
  - Bumped **Z** from `1` to `2` (0.2.1 → 0.2.2) to record a substantive addition to the method description without changing overall section structure.  
  - Added §21.1 **How the First SoT Was Forged (Reverse-Mapping the Repo)** to capture the origin story of the SoT:  
    - hitting severe drift and “unknown damage”,  
    - using Codex to incrementally explain every file, endpoint, and structure,  
    - building an “exploded view” factual map of the repo,  
    - promoting that into a SoT that first described **what IS** before layering **what I WANT**,  
    - then using that map to run a focused “de-slop” period removing redundant and dead code safely.  
  - Clarified in §21 that this reverse-mapping process is the practical way to recover from drift: reconstruct SoT from code → then resume the normal loop.  

- **v0.2.1 – 2025-11-23**  
  - Bumped **Z** from `0` to `1` (0.2.0 → 0.2.1) to reflect added scope and narrative without changing the core structural layout.  
  - Added §0.3 **Why This Document Exists (Author’s Intent)** to explicitly state that this is my method “bible”, personal wiki, portfolio backbone, and future teaching reference — not marketing.  
  - Added §21 **The Hierarchy of Truth (Code → SoT → AI → Me)** to capture the “code is fact / SoT describes code / AI is executor / I am direction” model, including the idea that anything not in code is speculation or future plan and that I mainly used 3–4 core prompts, not a giant “prompt bundle”.  
  - Wove in additional phrasing from recent conversations around:
    - Feeling silly or pompous writing this, but choosing to document anyway.  
    - The goal that someone else might be able to use this method to improve their own problem-solving and workflow.  
    - The repeated point that this is **not** a collection of hacks, but a repeatable loop and hierarchy of trust.  
  - Left all technical content in §§1–20 untouched structurally, only referencing new sections where relevant in my own mindset.  

- **v0.2.0 – 2025-11-23**  
  - Bumped **Y** from `1` to `2` (0.1.6 → 0.2.0) to reflect a structural expansion of the method description.  
  - Kept §§1–12 content from v0.1.6 structurally intact as the “core loop + original framing”.  
  - Added §13 **The Orchestration Principle** clarifying that the method is about me as architect and the LLM as an interchangeable execution engine.  
  - Added §14 **LLMs as Prediction Engines (Not “AI”)** to formalize the “prediction machine” mindset and explain why slop appears when scope is vague.  
  - Added §15 **The Exponential Expandability Principle** describing the design rule that every pass must survive deeper future passes without full rewrites.  
  - Added §16 **The Emotional Engine of the Method** capturing stubbornness, low ego, and green-smoke-as-dopamine as first-class parts of the system.  
  - Added §17 **Repeatability Across Projects** to state explicitly that this method is portable to any new project/domain, not BUS Core-specific.  
  - Added §18 **AI as Team Compression, Not Replacement** to capture the “this is what a dev team would have done, just slower and more expensive” insight.  
  - Added §19 **What This Method is NOT** to clearly differentiate it from prompt tricks, hype, or course-funnel nonsense.  
  - Added §20 **Why This Method Actually Works (Meta Summary)** as a single consolidated explanation of the causal factors behind the success of the loop.  
  - Updated §0.1 and §0.2 to reflect the new version number and to point the Changelog reference to §22.  
  - Left all TODOs in §8 unchanged and still **not specified** until filled in with concrete stories and dates.  

- **v0.1.6 – 2025-11-23**  
  - Switched the Method SoT to the new **X.Y.Z versioning scheme** (release track, major version, patch).  
  - Defined `X`, `Y`, `Z` semantics in §0.1 and added concrete bump rules in §0.2.  
  - Declared this file to be on track **0.1.\*** (internal method, first stable structure) and set this iteration to **0.1.6**.  
  - Retroactively mapped old flat `v0.4 / v0.5 / v0.6` numbers into `0.1.3+` in this Changelog.  

- **v0.1.5 – 2025-11-23**  _(previously labelled v0.6)_  
  - Updated §7 **Verified Public Receipts** with hard numbers from GitHub UI:  
    - 0 open / 336 closed PRs in `truegoodcraft/TGC-BUS-Core` (filter `is:pr is:closed`).  
    - Profile header “1,047 contributions in the last year”.  
    - November 2025 entry “Created 239 commits in 1 repository”.  
  - Clarified that those 336 closed PRs are the canonical count of Codex/GitHub loop iterations from workflow inception to the first public MVP.  

- **v0.1.4 – 2025-11-23**  _(previously labelled v0.5)_  
  - Added explicit **versioning rules** (pre-X.Y.Z) requiring a version bump + changelog entry for *any* modification.  
  - Introduced the **Changelog** section and rules about never editing old versions in place.  
  - Specified that the highest version number is canonical when multiple copies exist.  

- **v0.1.3 – 2025-11-23**  _(previously labelled v0.4)_  
  - First consolidated Method / Process SoT capturing:  
    - The core loop  
    - The five controls  
    - Zero-training advantages  
    - Roadblocks and “non-problems”  
    - Initial public receipts, cost, and real quotes about how I talk to the models.

