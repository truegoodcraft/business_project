Method SoT Version: v0.2.5

# BUS Core – Method / Process SoT (Offshoot)  
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

### 0.1 Version number format (X.Y.Z) – for all TGC docs

All long-lived TGC documentation (Method SoTs, technical SoTs, specs, prompts that act like SoTs, protocols) **must** use this format:

- **X – Release track** - 0 = pre–“official teaching release” (internal, in flux)  
  - 1 = first formal, public/teaching release  
  - 2+ = later eras (big rewrites, new architecture, etc.)

- **Y – Document / product major version** - Increment when structure or meaning changes in a way that could confuse someone on an old version.
  - Triggers include:
    - Sections added/removed/moved  
    - Core definitions changed  
    - Rules rewritten or reversed

- **Z – Iteration / patch** - Increment for **every change**, no matter how small:
    - Typos  
    - Wording tweaks  
    - Reordering  
    - New TODOs  
    - Minor clarifications  
  - Z is effectively unbounded (0, 1, 2, …).

This file is currently **v0.2.5**:

- `0` = internal method track (not yet a polished public product)  
- `2` = second major structure of the method (includes orchestration, generalization, and personal/teaching intent)  
- `5` = fifth patch on that structure (added The Runtime Protocol: standard prompts and high-frequency update loop)

### 0.2 Versioning rules (non-optional, global)

These rules apply to **all** versioned TGC documents (Method SoT, App SoT, DB SoT, UI SoT, etc.):

- **Any modification** to a document — including typo fixes, formatting, word changes, reordering, or added TODOs — **MUST**:
  - bump the **Z** component at minimum (e.g., `0.2.4 → 0.2.5`), and  
  - append a new, dated entry in that document’s **Changelog** describing what changed.
- If you make a structural or conceptual change that would confuse someone reading an older version:
  - bump **Y** and reset Z to 0 (e.g., `0.2.9 → 0.3.0`), and log it.
- Only change **X** when you intentionally declare a new release track:
  - e.g., “internal method” → “public teaching method” → “method v2 on new architecture”.
- **Never edit an old version in place.** - When updating, copy forward the latest version, bump `X.Y.Z` as needed, and log changes.
- If multiple copies of a doc exist:
  - The **highest version number** (by X, then Y, then Z) is the current canonical version.
- Older versions are **archives only** and must not be edited.
- The **Changelog** for every versioned doc must always be the **final section at the bottom**.
- If there is no Changelog entry for a change, that change is **not legitimate**.

This is not polished marketing.
This is the working record of *how the thing really got built*.

### 0.3 Why This Document Exists (Author’s Intent)

This Method SoT is not here to impress anyone.
It exists for three reasons:

1. **Future Me** This is my **personal bible** for the method — how I think, how I build, and what actually worked when BUS Core went from nothing to a real, running system.
   It’s my memory backup: a logbook, a proto-wiki, and the place I can come back to when I forget how I pulled this off the first time.

2. **Future Builders** If someone who doesn’t know how to code wants to build something real using LLMs without getting lost in hype, gatekeeping, and “AI prompt bundles”, this document should give them enough **facts, patterns, and scars** to stand on my shoulders instead of starting from zero.
   Not because I think I’m special — just because I’ve already paid the cost in time, frustration, and late nights.

3. **Future Teaching / Portfolio** If I ever use this work to teach, consult, or get a job or funding, this is the **canonical record** of what actually happened.
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
| **Living Source of Truth (SoT)** | Single markdown/core doc that must be patched before code lands | “Too much paperwork”, “I’ll remember”                   | Kills drift, naming wars, and schema hallucinations     |
| **Update-SoT-First rule** | LLM is literally not allowed to output code until SoT is updated| People rarely think to *handcuff* the model            | Forces models to read their own prior work              |
| **Smoke that restarts the server** | Full end-to-end validation after each change                    | “Too slow”, “I’ll just click around”                    | Makes regressions visible immediately                   |
| **One-letter branch switch (`p branch`)** | Instant checkout + fetch of any branch                        | Many people re-clone or click UIs every time           | Removes setup/teardown friction completely              |
| **“Too dumb to stop” as a feature** | No ego protection, no “real engineers don’t do it this way”     | Trained devs defend their schooling & patterns         | Ignores 20 years of cargo-cult rules that slow others   |

The method is not “be clever”.
The method is: **lock in these controls and keep turning the crank.**

---

## 3) What Zero Training Gave Me (the actual unfair advantages)

| Problem most trained devs have          | I never had it because…                                 | Result                                          |
|-----------------------------------------|---------------------------------------------------------|-------------------------------------------------|
| Architecture astronauts                 | Didn’t know big design up front was “mandatory”        | Shipped instead of debating for months          |
| Framework religion                      | Had zero opinion on React vs Vue vs htmx               | Picked whatever worked fastest *that day* |
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
3. Shipping a real local-first product *while learning the stack live* 4. Maintaining a living, enforceable SoT that gets patched before the code does  
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
- A clearer **SoT structure strategy**:  
  - Right now the Method SoT is a single, very large file that I open in Notepad++ and scroll endlessly.
  - I need to decide whether to:  
    - split it into multiple SoTs (Method, App, UI, DB) with an index,  
    - move it into a tool with headings and outline (Notion / Docs),  
    - or keep it as one file with a stricter internal table of contents.
- A more formal **AI Sonar log**:  
  - Today, I mostly run sonar intuitively in my head.
  - At some point it may be worth logging the recurring “control questions” and the model’s answers so I can see how advice changes over time.
- A path to **scaling the Method beyond me**:  
  - The Method is tuned to my brain and workflow.
  - I still need to figure out what it would take for someone else — without my background — to pick up the SoT protocol and actually use it successfully.

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
> ***Edit files in D:\BUSCore-Test (you’re on feature/short-name).**** >   
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

### 15.1 Screenshot-First UI & 4–6 Screen Rule (BUS Core Example)

For BUS Core, I deliberately focused early on a **small set of very clean screens** instead of trying to design the entire UI at once.

Working rule:

> **Ship 4–6 clean screens that can both run the shop and act as reusable screenshots.**

The target set:

- Home / Dashboard  
- Vendors  
- Items  
- Manufacturing Runs  
- Settings / System Info  
- (Optional) Journals / Logs  

These screens serve a dual purpose:

- They are the **minimum usable surface** for a one-person shop.
- They produce **high-quality visual assets** (screenshots / short clips) for:
  - README  
  - Notion one-pager  
  - buscore.ca  
  - Community posts and answers  

Larger marketing work (full site, pricing grid, etc.) is explicitly delayed until these 4–6 screens are **real, stable, and screenshot-worthy**.

### 15.2 Nested Complexity UI for Makers

The UI philosophy for BUS Core matches the Method:

> **Start soft and shallow, then let complexity unfold only when the user asks for it.**

For makers:

- They are often literally **covered in dust, resin, or metal shavings** when they touch the UI.
- They need a **soft touch**:
  - clear buttons,  
  - obvious next steps,  
  - no modal maze.

UI rules:

- **Shallow-first** - A user should be able to stay in the “top layer” and still complete basic flows:  
    - log a run,  
    - update stock,  
    - check a key stat.
- **Nested complexity** - Detailed pieces (recipes, costing breakdowns, alias tables, analytics dimensions) live **one or two clicks deeper**, never forced on the casual pass.
- **Organic flow** - Each step should feel like it naturally nudges them toward finishing what they started, not like switching to a different system.

This mirrors the Method itself:  
simple, repeatable surface; deep structure available when needed;
no forced “big brain mode” just to get through the day.

---

## 16) The Emotional Engine of the Method

This isn’t “grindset” talk. It’s logistics.
The method only worked because of a specific emotional posture:

- **Stubbornness over motivation** - Smoke is red → fix it.
  - Too tired → do a smaller iteration, but don’t vanish.
- **No ego about “being a real dev”** - I never needed to prove I was doing it the “proper” way.
- **Comfort with not understanding the internals** - I let the tests and behaviour tell me if it worked, not my ego about code literacy.
- **Willingness to argue with the models** - “No, you are wrong.” was a normal part of the loop, not a crisis.
- **Design empathy rule** - If it only takes one person to run the shop, it should only take one person to manage the system.
  - This keeps scope honest: no feature is worth it if it turns BUS Core into a second full-time job.
- **Permanent-fix bias** - When a problem shows up, my instinct is not “how do I get past this once,” but  
    **“how do I structure this so I never see this problem again?”** - That’s why I keep choosing harder refactors earlier instead of stacking quick hacks.
- **“Don’t screw next-tomorrow” rule** - I try not to push complexity onto future-me.
  - I’d rather pay the cost once, with a structural change, than live with a recurring annoyance that keeps stealing nights and weekends.

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

In that sense, BUS Core is just the **first case study**.
The real asset is the Method itself: a human-in-the-loop discipline layer on top of LLMs that fights drift, hallucinated architecture, and “vibe-coded” spaghetti — something enterprises and solo builders both struggle with.

### 17.1 Core vs Pro Pattern (Data-First, Automation Later)

In BUS Core, the method produced a reusable pattern for splitting a product into **Core** and **Pro** without betraying users:

- **Core (free, forever, local-first)** - Items, vendors, recipes, manufacturing runs, and stock changes.
  - Local analytics events and “Shop Insights” based only on local data.
  - Journaling, recent activity, and file attachments (receipts, SOPs, product docs).
  - Canonical names + alias tables for vendors and items.
  - Principle: **your data and your admin brain work forever, even if Pro is never purchased.**

- **Pro (paid, automation)** - Etsy/Shopify/other sales-channel sync.
  - Scheduled jobs and background automations.  
  - Advanced analytics dashboards.
  - LLM-powered helpers (name normalization suggestions, SOP Q&A, file parsing, etc.).  
  - Potential multi-user / multi-machine features and automated backups.

Rule that emerged:

> **Core = data + admin brain. Pro = robots and integrations.**

This split is portable: any future project using this Method can ask the same question—  
“What must be free and local for this to be honest?”
vs. “What can I charge for as automation?”

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

### 18.1 AI Sonar: Using Models as Drift Detectors

I don’t just use LLMs as code generators — I use them as **sonar**.
Pattern:

- I ask the **same control questions** at different stages of the project, for example:  
  - “Is this architecture too complex for what I’m doing?”
  - “What are the main risks of this approach?”  
  - “Is there a simpler pattern for this part of the system?”
- I watch how the **answers change over time** instead of trusting any single reply.
- Early on, the model might say “This is fine for now.”
- Months later, the *same* question might come back with warnings like  
    “If you keep this pattern, migrations and testing are going to be painful.”

Because these models are probabilistic, I treat them like an **early-warning sensor**:

- One weird response = noise.
- Ten answers across different sessions all pointing at the same concern = **signal**.

Most of this sonar is still **in my head** — I feel that the pattern of answers has shifted.
If I needed to, I could formalize it by logging each control question and answer, but the core Method is:

> Keep pinging the system with the same questions over time and treat the **delta in AI’s answers** as a hint that invisible complexity has crept in.

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

- A **discipline** - A **loop** - A **set of rails** - A willingness to turn that handle way past the point normal people get bored

Nothing here is mystical.
It’s just consistent.

---

## 20) Why This Method Actually Works (Meta Summary)

This is the “why” in one place:

The method works because:

- **SoT removes drift** - The model is always working from one shared brain, not 100 detached prompts.
- **Smoke removes delusion** - Feelings don’t matter; if the app can’t boot and do basic flows, it’s broken.
- **LLMs are treated as tools, not oracles** - They predict under constraint instead of hallucinating under ambiguity.
- **Everything is additive** - No big rewrites, just layers. Each pass is survivable by the next one.
- **The architecture is behaviour-driven** - If it passes smoke and matches SoT, it’s good enough for that iteration.
- **The emotional loop is stable** - Stubbornness + green-smoke dopamine beats self-doubt + perfectionism.
- **The cost is low enough to be sustainable** - Two pro subs and spare time, not a $50k bootcamp or a dev salary.
- **The process is model-agnostic** - Any capable LLM can plug in if it respects SoT and passes smoke.

The point is not that this is “the best” way to build software.
The point is that this is a **proven, repeatable way for a non-dev to build real, maintainable software** in 2025.

### 20.1 Local Analytics & Anonymous Push Pattern

BUS Core uses the Method to enforce a specific analytics ethic:

- **All analytics are derived from local events**, not remote telemetry.
- Events like `item_sold`, `run_completed`, `vendor_created`, `item_created/archived` are stored as structured rows with `timestamp`, `event_type`, `entity_type`, `entity_id`, `qty`, `value`, and `meta`.
- Home stats, Recent Activity, and future Insights views read from this event log.
- Any **cloud reporting is push-only and optional**:  
  - The app never pulls hidden telemetry.
  - A user can opt-in to push **aggregated stats** (not raw business data).
  - A random, stable **license hash** (e.g. 24-character ID) is used only to:  
    - Deduplicate submissions from the same install.
    - Group anonymous metrics by source without knowing who the person is.

This pattern keeps the Method aligned with the privacy ethic:  
**Trust comes first; any data leaving the box must be obvious, optional, and minimal.**

### 20.2 Distribution & Community Guardrails

The Method now treats **distribution** as part of the system, not an afterthought:

- Don’t push hard until:  
  - Home UI is decent and matches the SoT.
  - buscore.ca has a minimal landing page with:  
    - a ~10-second demo (materials → run → inventory updated),  
    - one download button,  
    - 2–3 bullets explaining what it does.
- Focus channels where makers actually live:  
  - Laser/CNC/3D printing Discords.
  - Maker and military Facebook groups I already inhabit.  
  - Selected subreddits, only in “helpful answer with example tool” mode, not sales.
- Treat Reddit’s hostility and X’s low engagement as **environmental facts**, not verdicts on the product.

Guardrail:  
**Marketing should follow working flows and honest screenshots, not precede them.** Distribution is another loop on top of the Method, not a replacement for it.

---

## 21) The Hierarchy of Truth (Code → SoT → AI → Me)

This section captures how I actually think about “what’s real” in the project.

> “Code is fact. SoT describes code. Anything not proven in the code is speculation at best.  
> If it doesn’t fit those categories, it’s a planned future / idea.”

The hierarchy:

1. **Code (Ground Truth)** - Whatever is in the repo and passes smoke is **canonical reality**.
   - If the SoT disagrees with the code, **the SoT is wrong** and must be updated.
   - If AI disagrees with the code, **AI is wrong**.
   - If I *feel* like it should be different, it’s still wrong until I change the code and get green smoke.

2. **SoT (Description of Truth)** - SoT exists to **describe** the current and intended system.
   - It must be **100% aligned** with the code for anything that already exists.
   - SoT can also contain:  
     - **Planned future**: clearly marked as not implemented yet  
     - **Open questions**: clearly labelled as undecided  
   - If something is in SoT but not in code, it is **design**, not reality.

3. **AI (Executor / Assistant)** - AI is **never** a source of truth.
   - It reads the SoT and code, then proposes changes.
   - Its output is only accepted if:  
     - It fits the SoT  
     - It compiles/runs  
     - It passes smoke  
   - If I suspect drift, I sometimes make AI quote actual code or DB schema back to me as part of the “truth chain” before we move.

4. **Me (Judgment / Feeling / Direction)** - I am the **source of decisions**, values, UX choices, and constraints.
   - My feelings (this is ugly / this is nice / I don’t trust this) are inputs to **future design**, not a replacement for tests.
   - When I make a design decision, it should land in the SoT.
   - Once it is in SoT and implemented in code, it becomes reality.

This hierarchy is how I avoid “AI slop” and hallucinated systems.
I trust, in order:

> **Code → SoT → AI → Me (for feelings, direction, and values).**

This is also why I never needed a “500 Prompt Mega Bundle”.
For most of the build:

- I used **3–4 core prompt structures**, recycled and refined.
- When I thought there was drift, I brought the **actual code and SoT back into context**, not a fresh “clever prompt”.

The Method is not a library of spells.  
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

1. **Used Codex to explain every part of the codebase back to me.** - File structure: which folders exist, what lives where.
   - For each file: what it does, which entities it touches.
   - Endpoints: what URLs exist, what handlers they map to, what they depend on.
   - DB pieces: which models are where, how they relate.

2. **Built a modular, “exploded view” of the repo.** - Not prose.  
   - Not vibes.
   - Just short, factual bullets of:
     - “This file does X.”  
     - “This endpoint calls Y.”
     - “This model contains fields A, B, C.”

3. **Promoted those facts into the first SoT.** - The initial SoT was **not** “what I wanted BUS Core to be”.
   - It was a compact, technical list of **what BUS Core already was** according to the code.

4. **Only after that did I start adding “what I want”.** - Once the “what IS” side was stable, I could layer “what SHOULD BE” on top.
   - The loop became:
     - Fact: from code → SoT  
     - Desire: from me → SoT as planned change  
     - Implementation: AI edits code → smoke verifies → SoT updated again.

5. **Used the SoT map to clean house.** - I spent roughly a week doing almost nothing but:
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

### 21.2 Origin Story: From GPT Document Manager to BUS Core + Method

The Method didn’t start as “I will build an ERP.”
It started as **“Can GPT manage all my documents and chaos for me?”**

Rough sequence:

1. **GPT as document manager** - The original idea was to have ChatGPT manage and organize my documents, SOPs, and notes.
   - I wanted a kind of “AI archivist” that could keep everything straight for me.

2. **Script-attempt phase** - I tried to fake this with clever shell/Python scripts glued to GPT prompts.
   - The scripts worked in tiny bursts but quickly became **convoluted and silly** — not a foundation I trusted for a real shop.

3. **Decision to build a real app** - Using AI as a research assistant, I compared options and landed on:  
     - a **Python app** with  
       - FastAPI-style HTTP surface,  
       - SQLite,  
       - a local-first philosophy.
   - BUS Core was born as the thing that would do what the scripts were failing to do.

4. **The “loose hose” stage** - As the UI and logic evolved, GPT started spraying:  
     - invented structures,  
     - dead endpoints,  
     - partial rewrites that didn’t match the rest.
   - It felt like a **loose hose** whipping through the codebase, throwing hallucinations everywhere.

5. **SoT and Method co-evolution** - The response to that chaos was the first SoT pass (see §21.1).
   - BUS Core and the Method **co-evolved**:  
     - each new problem in BUS Core forced a clearer rule in the Method,  
     - each new rule in the Method pushed BUS Core into a more coherent shape.

So BUS Core is the **proof artifact**, and the SoT + Method protocol is the **actual invention**.
One didn’t magically create the other; they shaped each other in a tight loop.

### 21.3 SoT as Deterministic Mirror (Mirror vs Painting)

The Source of Truth is not a dream board.
It is a **deterministic mirror file**.

Rules:

- The SoT describes **what the system is right now**, not what I hope it will become.
- Only **truth** is allowed in:
  - Observed behaviour  
  - Confirmed decisions  
  - Real structures (tables, endpoints, flows) that exist in code or DB
- “Maybe someday” ideas belong in clearly marked **future / TODO** sections, not mixed into the factual core.

I think of it as:

> **SoT is a mirror, not a painting.**

If the SoT ever drifts into painting territory, the whole Method starts to rot, because the models and I are now optimizing against a lie.

---

## 23) The Runtime Protocol (Standard Prompts)

The SoT is the hard drive; these prompts are the operating system.
Without these specific instructions, the LLM is just a generic chatbot. **With** these instructions, it becomes a stateless, verifiable engine for the Method.

### 23.1 The Work Session Prompt (Stateless Clean Room)

**Purpose:**
- Forces **Statelessness**: Prevents "hallucination accumulation" by treating every chat as a fresh start.
- Enforces **Strict Consistency**: Establishes that I am the "Leader Node" and the AI is a replica; if SoT and Code conflict, I decide.
- **Tone Control**: Explicitly bans "fanboying" and forces a "Red Team" engineering posture.

**The Prompt:**
> **TGC BUS CORE – WORK SESSION PROMPT**
> You are my development assistant for the project TGC BUS Core (Business Utility System Core) owned by True Good Craft.
> Treat every conversation as stateless. You know nothing about previous chats unless I paste text here.
>
> **1. Source of Truth rules**
> I will paste a Source of Truth (SoT) document or relevant excerpts for this session.
> - SoT is canonical.
> - Do not contradict it.
> - Do not “fix” or “improve” it unless I explicitly say we are updating SoT.
> - If something is not in the SoT, say: “Not specified in the SoT you’ve given me,” and then, if useful, you may offer clearly-marked options or patterns (but not assert them as fact).
>
> **2. No hidden assumptions**
> Do not assume features, flows, tiers, or architecture that are not explicitly present in:
> - The SoT I paste, or
> - The code / text I give you in this session.
> Generic programming knowledge is allowed (Python, HTTP, JS, etc.), but project-specific facts must come from SoT or my words.
>
> **3. Interaction style**
> - Be direct, technical, and concise.
> - No fanboying, no pep talk, no praise, no “this is awesome”.
> - Focus on: What is true, What is broken, What is missing, What the options/tradeoffs are.
> - Use bullets and short sections when it improves clarity.
>
> **4. What to do with my requests**
> When I give you code, logs, or design questions:
> - If I ask “what’s going on / what do we have?”: Summarize only what’s present in the provided code/SoT. Don’t infer modules or flows that aren’t shown.
> - If I ask for changes or new code: Respect the SoT and the existing architecture. Show concrete snippets or patches. Explain briefly why you chose a given approach (constraints, tradeoffs), but keep it short.
> - If there’s a conflict between SoT and code, or two pieces of text I gave you, Explicitly call it out: “Conflict: SoT says X, code says Y.” I decide which wins. You don’t silently choose.
>
> **5. Handling uncertainty**
> If you are missing information:
> - Say exactly what you’re missing.
> - Offer options labeled as such (e.g., “Option A / B / C”), not as facts.
>
> Acknowledge these rules in one or two sentences, then wait for me to paste the current SoT (or the relevant sections) before doing any project-specific reasoning.

### 23.2 The Delta Prompt (Human-in-the-Loop Commit)

**Purpose:**
- Prevents **Documentation Drift**.
- Instead of asking the AI to "rewrite the whole doc" (which causes data loss), it forces a **Git-style commit message** logic.
- It buckets changes into "Facts," "Changes," and "Questions," making the review process instant.

**The Prompt:**
> **END-OF-SESSION SoT DELTA PROMPT**
> At the end of this work session, do the following based only on this conversation and the SoT text I provided at the start:
>
> Do not rewrite the full SoT.
> Your job is to produce a delta log I can use to manually update the SoT.
> No new ideas, no speculation, no guessing what I “probably meant.”
> Compare this session to the SoT and output four sections:
>
> **(1) NEW FACTS / DECISIONS**
> Bullet list of things that are clearly new and should be added to the SoT.
> Each bullet should be:
> - As short and precise as possible.
> - Written as a SoT-style statement (fact/decision, not suggestion).
>
> **(2) CHANGES TO EXISTING FACTS**
> Bullet list of items where the SoT and this session disagree, and this session clearly replaced the old decision.
> For each, use this format:
> - Old (SoT): …
> - New (session): …
> Only list items where the change is explicit, not implied.
>
> **(3) CLARIFICATIONS / TIGHTENING**
> Cases where the SoT was vague and this session narrowed or clarified it.
> Example format: SoT vague on X → clarified as: "<new clarified rule>"
>
> **(4) OPEN QUESTIONS / UNRESOLVED CONFLICTS**
> Any contradictions, ambiguities, or design questions that we did not fully resolve.
> Phrase them as direct questions I need to answer before SoT can be updated.
>
> **Constraints**
> - If a detail is not clearly stated in this session, do not include it.
> - If you’re unsure whether something is “new” or just a restatement, put it in section (4) as “uncertain / needs confirmation.”
> - Be concise and structured. No commentary, no praise, no marketing language.
>
> Respond only with those four sections, ready for me to copy/paste into my SoT editing workflow.

### 23.3 The High-Frequency Update Loop

The prompts above only work because of the **cadence**.
I do not wait for a "major release" to update the SoT. I update it **per session**.

**The Loop:**
1. **Initialize:** Paste *Work Session Prompt* + Current SoT.
2. **Work:** Iterate on code/design for 1–2 hours.
3. **Commit:** Paste *Delta Prompt*.
4. **Patch:** Manually apply the Delta output to the SoT text file.
5. **Close:** Close the chat window (destroying the state).

This ensures the SoT is always **ahead** of the code, never chasing it.

---

## 24) Changelog (Method SoT Versions)

> **Rule:** Every change to this document requires a new entry here.
> If there is no Changelog entry for a change, that change is not legitimate.

- **v0.2.5 – 2025-11-26**
  - Bumped **Z** from `4` to `5` (0.2.4 → 0.2.5).
  - Added §23 **The Runtime Protocol (Standard Prompts)** containing the literal text of the "Work Session Prompt" and "Delta Prompt".
  - Documented the logic behind them: **Statelessness** (Clean Room), **Strict Consistency** (Leader Node), and **Delta Logging** (Commit Messages).
  - Explicitly documented the **High-Frequency Update Loop** in §23.3 to explain that SoT updates happen per-session, not per-project.
- **v0.2.4 – 2025-11-25** - Bumped **Z** from `3` to `4` (0.2.3 → 0.2.4) to reflect new Method clarifications from the 2025-11-25 Method/SoT evolution session.
  - Extended §16 **The Emotional Engine of the Method** with a permanent-fix bias and “don’t screw next-tomorrow” rule, capturing the way I prefer structural fixes over band-aids.
  - Added §18.1 **AI Sonar: Using Models as Drift Detectors** to document how I reuse control questions over time and read changes in AI’s answers as an early-warning system for hidden complexity.
  - Added §21.2 **Origin Story: From GPT Document Manager to BUS Core + Method** to lock in the real sequence: GPT as document manager → script attempts → Python app → “loose hose” stage → SoT and Method co-evolution.
  - Added §21.3 **SoT as Deterministic Mirror (Mirror vs Painting)** to formalize the rule that only verified truth enters the SoT, and that it must describe current reality, not wishlists.
  - Added §15.2 **Nested Complexity UI for Makers** to capture the shallow-first, drill-down-later UI philosophy tuned for real makers in the shop.
  - Expanded §8 **Missing Pieces I Still Need to Write** with open questions about SoT structure, formalizing AI Sonar logs, and scaling the Method so someone else can use it.
  - Clarified in §17 that BUS Core is the first case study and the Method/SoT protocol is the real reusable asset.
  - Promoted the X.Y.Z scheme in §0.1–0.2 to a **global rule for all TGC documentation** and made explicit that each doc’s Changelog must live at the bottom.
- **v0.2.3 – 2025-11-24** - Bumped **Z** from `2` to `3` (0.2.2 → 0.2.3) to capture new Method patterns from the 2025-11-24 product/strategy session.
  - Added §15.1 **Screenshot-First UI & 4–6 Screen Rule (BUS Core Example)** to record the tactic of focusing on a tiny set of clean, screenshot-ready screens that both run the shop and serve as marketing assets.
  - Extended §16 with a **design empathy rule**: if it only takes one person to run the shop, it should only take one person to manage the system.
  - Added §17.1 **Core vs Pro Pattern (Data-First, Automation Later)** to generalize the Core/Pro split into a reusable template: Core = data + admin brain, Pro = robots and integrations.
  - Added §20.1 **Local Analytics & Anonymous Push Pattern** to formalize the event-log + opt-in push telemetry design that keeps analytics aligned with the local-first ethic.
  - Added §20.2 **Distribution & Community Guardrails** to document when and where to promote BUS Core (and future tools), emphasizing screenshots + working flows before heavy marketing.
- **v0.2.2 – 2025-11-23** - Bumped **Z** from `1` to `2` (0.2.1 → 0.2.2) to record a substantive addition to the method description without changing overall section structure.
  - Added §21.1 **How the First SoT Was Forged (Reverse-Mapping the Repo)** to capture the origin story of the SoT:  
    - hitting severe drift and “unknown damage”,  
    - using Codex to incrementally explain every file, endpoint, and structure,  
    - building an “exploded view” factual map of the repo,  
    - promoting that into a SoT that first described **what IS** before layering **what I WANT**,  
    - then using that map to run a focused “de-slop” period removing redundant and dead code safely.  
  - Clarified in §21 that this reverse-mapping process is the practical way to recover from drift: reconstruct SoT from code → then resume the normal loop.
- **v0.2.1 – 2025-11-23** - Bumped **Z** from `0` to `1` (0.2.0 → 0.2.1) to reflect added scope and narrative without changing the core structural layout.
  - Added §0.3 **Why This Document Exists (Author’s Intent)** to explicitly state that this is my method “bible”, personal wiki, portfolio backbone, and future teaching reference — not marketing.
  - Added §21 **The Hierarchy of Truth (Code → SoT → AI → Me)** to capture the “code is fact / SoT describes code / AI is executor / I am direction” model, including the idea that anything not in code is speculation or future plan and that I mainly used 3–4 core prompts, not a giant “prompt bundle”.
  - Wove in additional phrasing from recent conversations around:
    - Feeling silly or pompous writing this, but choosing to document anyway.
    - The goal that someone else might be able to use this Method to improve their own problem-solving and workflow.
    - The repeated point that this is **not** a collection of hacks, but a repeatable loop and hierarchy of trust.
  - Left all technical content in §§1–20 untouched structurally, only referencing new sections where relevant in my own mindset.
- **v0.2.0 – 2025-11-23** - Bumped **Y** from `1` to `2` (0.1.6 → 0.2.0) to reflect a structural expansion of the Method description.
  - Kept §§1–12 content from v0.1.6 structurally intact as the “core loop + original framing”.
  - Added §13 **The Orchestration Principle** clarifying that the Method is about me as architect and the LLM as an interchangeable execution engine.
  - Added §14 **LLMs as Prediction Engines (Not “AI”)** to formalize the “prediction machine” mindset and explain why slop appears when scope is vague.
  - Added §15 **The Exponential Expandability Principle** describing the design rule that every pass must survive deeper future passes without full rewrites.
  - Added §16 **The Emotional Engine of the Method** capturing stubbornness, low ego, and green-smoke-as-dopamine as first-class parts of the system.
  - Added §17 **Repeatability Across Projects** to state explicitly that this Method is portable to any new project/domain, not BUS Core-specific.
  - Added §18 **AI as Team Compression, Not Replacement** to capture the “this is what a dev team would have done, just slower and more expensive” insight.
  - Added §19 **What This Method is NOT** to clearly differentiate it from prompt tricks, hype, or course-funnel nonsense.
  - Added §20 **Why This Method Actually Works (Meta Summary)** as a single consolidated explanation of the causal factors behind the success of the loop.
  - Updated §0.1 and §0.2 to reflect the new version number and to point the Changelog reference to §22.
  - Left all TODOs in §8 unchanged and still **not specified** until filled in with concrete stories and dates.
- **v0.1.6 – 2025-11-23** - Switched the Method SoT to the new **X.Y.Z versioning scheme** (release track, major version, patch).
  - Defined `X`, `Y`, `Z` semantics in §0.1 and added concrete bump rules in §0.2.
  - Declared this file to be on track **0.1.\*** (internal Method, first stable structure) and set this iteration to **0.1.6**.
  - Retroactively mapped old flat `v0.4 / v0.5 / v0.6` numbers into `0.1.3+` in this Changelog.
- **v0.1.5 – 2025-11-23** _(previously labelled v0.6)_  
  - Updated §7 **Verified Public Receipts** with hard numbers from GitHub UI:  
    - 0 open / 336 closed PRs in `truegoodcraft/TGC-BUS-Core` (filter `is:pr is:closed`).
    - Profile header “1,047 contributions in the last year”.  
    - November 2025 entry “Created 239 commits in 1 repository”.
  - Clarified that those 336 closed PRs are the canonical count of Codex/GitHub loop iterations from workflow inception to the first public MVP.
- **v0.1.4 – 2025-11-23** _(previously labelled v0.5)_  
  - Added explicit **versioning rules** (pre-X.Y.Z) requiring a version bump + Changelog entry for *any* modification.
  - Introduced the **Changelog** section and rules about never editing old versions in place.
  - Specified that the highest version number is canonical when multiple copies exist.
- **v0.1.3 – 2025-11-23** _(previously labelled v0.4)_  
  - First consolidated Method / Process SoT capturing:  
    - The core loop  
    - The five controls  
    - Zero-training advantages  
    - Roadblocks and “non-problems”  
    - Initial public receipts, cost, and real quotes about how I talk to the models.
