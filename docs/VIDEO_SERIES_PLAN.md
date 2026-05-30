# ADK 2.0 Video Series — 4 Episodes, Frame-Accurate Plan

This doc plans a **4-episode series** for the ADK 2.0 marathon demo. Each episode targets **7-8 minutes**, **demo-first cold open**, **substantial code/comparison content**.

Distinct from `VIDEO_SCRIPT.md` (which is a single 20-min conference talk covering all three pillars in one go). The series breaks that talk into four standalone videos optimized for YouTube depth + retention.

---

## Series at a glance

| Ep | Title | Length | Live demo | Core unique-to-2.0 angle |
|---|---|---|---|---|
| 1 | Graph Workflows — One LLM Call Instead of Four | 8 min | Mode 1 (Hot Boston) | Function nodes + agent nodes as peers; deterministic Python router |
| 2 | Collaborative Agents — Same UI, Different Outcomes | 7 min | Mode 2 (3 questions) | LLM coordinator picks dynamic subset, runs in parallel |
| 3 | Dynamic Workflows — When the LLM Decides the Shape | 8 min | Mode 3 (Boston preset) | Recursive parallel fan-out with topology decided at runtime |
| 4 | ADK 1.x vs 2.0 — Three Problems That Needed Solving | 7 min | None (code split-screens) | Concrete before/after for each pillar |
| | **Total** | **~30 min** | | |

---

## Universal production specs (apply to all 4 episodes)

### Structural formula

Every episode follows the same pedagogical flow. Talking-head presenter intro → demo → explain demo → structured theory → recap.

```
0:00 – 0:15   PRESENTER INTRO + LEARNING PROMISE
              [Camera on Annie]
              "Hi, I'm Annie. By the end of this video, you'll learn [X]."

0:15 – 0:25   TITLE CARD: episode #, big bold title

0:25 – 3:30   DEMO with live narration (~3 min)
              [Show the visual, narrate what's happening, NO theory yet]

3:30 – 5:00   EXPLAIN THE DEMO (~1.5 min)
              [Code reveal — "here's what made that happen"
               Show one snippet, highlight 1-2 key lines]

5:00 – 7:00   STRUCTURED THEORY (~2 min)
              [Numbered bullets, each with its own card on screen]
              "Three things to take away:"
              "1. <first concept> — including what 1.x couldn't do here"
              "2. <second concept> — including when to reach for it"
              "3. <third concept>"
              [Closing card: "When to use [Pillar]"]

7:00 – 7:30   RECAP + TEASE next episode
```

### Why this structure (vs cold-open)

- **Personal intro builds trust immediately** — viewers know who's teaching them
- **Learning promise converts curiosity to commitment** — they know what they'll get if they watch
- **Demo runs uninterrupted by theory** — visual story is allowed to land
- **Theory in numbered bullets** — viewers can pause, write notes, skim later
- **More approachable than cinematic cold-open** — feels like a tutorial, not a music video

### Production tricks for cool-factor (apply universally)

- **No "umm" or "let me explain"** — cut every dead-air second in editing
- **Jump cuts every 3-4 seconds** during exposition (modern attention span)
- **Hold steady** during demos so viewers can absorb the visual
- **Soft sound effects** for state transitions — pulse, complete, route-fire (add in post)
- **Slow-mo critical moments** — 0.5× speed for the parallel pulse / the tree growing
- **Smash-cut transitions** between sections — not crossfades
- **Big bold numbers** as graphic overlays when narrated (*"1 LLM call"* in 80pt text on screen)
- **Code on screen**: highlight one line at a time with a colored box; never show >20 lines
- **Open with the END STATE** for 5 seconds before rewinding — modern attention needs the payoff teased
- **VS Code dark theme** that pops on camera (Tokyo Night or One Dark Pro)

### Pre-record checklist (every episode)

- [ ] Server running: `uv run python server.py`
- [ ] Browser at `http://127.0.0.1:8000/`
- [ ] Pre-warm Mode 1 once (unlocks chat panel)
- [ ] Clear browser cache, hide bookmarks bar, full-screen the browser
- [ ] IDE open to the specific file:line for this episode's code reveal
- [ ] Slack/email muted, do-not-disturb on
- [ ] Test microphone level
- [ ] `GOOGLE_API_KEY` confirmed in `.env`

---

# Episode 1 — Graph Workflows: "One LLM Call Instead of Four" (~8 min)

## Presenter intro + promise (0:00 – 0:15)

```
[CAMERA ON ANNIE — clean background, brand frame]
[Friendly energy, eye contact with camera]
```

*"Hi, I'm Annie. By the end of this video, you'll learn how ADK 2.0's graph workflows let you express a complete multi-step agent in eight lines of code — and you'll know exactly when this pattern saves you 4× on LLM costs versus a single agent."*

## Title card (0:15 – 0:25)

```
[FULL SCREEN]

  ADK 2.0 — Episode 1
  
  Graph Workflows
  "One LLM Call Instead of Four"

[Hold 2-3 seconds, then smash-cut to the demo]
```

## Demo with narration (0:25 – 3:30)

```
[SHOW: browser at http://127.0.0.1:8000/ — Mode 1 panel visible]
```

*"This is the marathon race day strategy planner. A runner asks: plan my race day.*
*Three things need to happen — fetch the weather, analyze the course profile, pull recent training data — then we pick a pacing strategy."*

```
[CLICK: Hot · Boston in the header — point at it]
[CLICK: Run]
```

*"I clicked Run. Now watch what happens."*

```
[STAY ON the visualization for 5+ seconds, narrate in real-time]
```

*"Three nodes lit up simultaneously. Cyan. Pulsing. Each has a live timer ticking up — one second, one-and-a-half, two seconds. These are three Python functions running in parallel. Zero LLM calls happening here. Just async functions hitting fake APIs."*

```
[Pull-fitness completes first, turns mint]
```

*"Fitness completed first — that one was the fastest fetch."*

```
[Other two complete; JoinNode flashes]
```

*"All three done. The JoinNode just fired — that's the diamond shape. It bundled all three outputs into a typed payload. Now the router runs."*

```
[Router completes; one strategy node activates]
```

*"Router fired. It looked at the temperature — 78 degrees — and routed to the hot-weather strategy. The router is a four-line Python function. An `if` statement. No LLM judgment. It cannot be wrong."*

```
[Strategy agent runs — 5-7 seconds]
[CUT to strategy output panel]
```

*"And here's the strategy. Target finish: three thirty-five. Pacing: 'Slow your 7:30 pace to 8:12 per mile to account for 78-degree heat and the 4.5% grade at mile 20.' Notice that — it referenced the actual runner data. The actual weather. The actual course profile. That's the structured output schema doing real work."*

```
[CUT: scroll to stats card. Hold on it.]
[OVERLAY: big bold "1 LLM CALL" graphic]
```

*"Total time: seven seconds. **One LLM call.** Fetch phase ran in 2 seconds in parallel — would have taken 4.5 seconds if we'd done them one at a time."*

## Explain the demo — code reveal (3:30 – 5:00)

```
[CUT to IDE — workflows/strategy_graph.py line 187]
[Just the edges=[...] block visible]
```

```python
root_agent = Workflow(
    name="marathon_strategy",
    edges=[
        (START, fetch_weather, join_inputs),
        (START, analyze_course, join_inputs),
        (START, pull_fitness, join_inputs),
        (join_inputs, route_by_weather),
        (route_by_weather, {
            "HOT":    hot_strategy,
            "NORMAL": normal_strategy,
            "COLD":   cold_strategy,
        }),
    ],
)
```

*"This is the entire orchestration. Eight lines.*
*The first three rows fan out from START into the JoinNode — that's the parallel part.*
*The fourth row runs the router after the join completes.*
*The fifth row picks one of three branches based on the router's emitted route.*
*That's it. The framework handles parallelism, scheduling, and the typed handoff."*

## Structured theory (5:00 – 7:00)

```
[SLIDE FORMAT: clean background, large numbered bullets appear one at a time
 Or: split screen — webcam on left, bullet card on right]
```

*"OK. Here's what to take away from graph workflows. Three things."*

```
[BULLET 1 APPEARS]

  1. FUNCTIONS AND AGENTS AS PEERS
```

*"In ADK 2.0, function nodes — that's plain Python — and Agent nodes — that's LLMs — coexist as equals in the same `edges` array. You don't have to wrap a Python function in an LlmAgent just to call it.*

*ADK 1.x's ParallelAgent only orchestrates agents — so fetching data required wrapping every fetch in an agent, adding three extra LLM calls for work that didn't need any reasoning. That's the 4× cost difference."*

```
[BULLET 2 APPEARS]

  2. ROUTING IS DETERMINISTIC
```

*"Branching on data is a four-line Python `if` statement. In 1.x, you'd write a coordinator agent with a prose instruction telling the LLM to transfer to the right handler. Mostly worked, occasionally didn't. In 2.0, the routing decision is code. It cannot be wrong."*

```
[BULLET 3 APPEARS]

  3. TYPED HANDOFF VIA JOINNODE
```

*"When parallel branches converge, JoinNode bundles their outputs into a typed Pydantic payload. The next node receives structured data, not untyped session-state strings. The framework validates the shape before the downstream agent ever sees it."*

```
[CARD: "When to use Pillar 1"]
```

*"Reach for graph workflows when the structure of the work is known — you can draw the diagram before you write code, and the routing decisions can be expressed as rules instead of LLM judgment."*

```
[OVERLAY large comparison graphic]
  LLM CALLS:         4  →  1
  LINES OF CODE:    ~80  →  8
  ROUTING:           prompt-based  →  Python `if`
```

## Recap + tease (7:00 – 7:30)

```
[CAMERA BACK ON ANNIE]
```

*"That's graph workflows. The one thing to remember: when the structure of your workflow is known, draw the diagram, write the edges array, let the framework run it. Eight lines instead of eighty.*

*Next episode: collaborative agents. We're going to type the same question into a chat box twice and watch a different number of specialists fire each time — in parallel. Subscribe so you don't miss it."*

```
[END CARD: subscribe button + repo link]
```

---

# Episode 2 — Collaborative Agents: "Same UI, Different Outcomes" (~7 min)

## Presenter intro + promise (0:00 – 0:15)

```
[CAMERA ON ANNIE]
```

*"Hi, I'm Annie. By the end of this video, you'll learn when to reach for ADK 2.0's collaborative agents instead of the older ParallelAgent — and you'll understand the one specific feature that makes them impossible to build in ADK 1.x."*

## Title card (0:15 – 0:25)

```
  ADK 2.0 — Episode 2
  
  Collaborative Agents
  "Same UI, Different Outcomes"
```

## Demo with narration (0:25 – 3:30)

```
[SHOW: browser scrolled to Mode 2 chat panel — 6 specialist pills visible]
```

*"This is Mode 2 — the race concierge. After we generated a strategy, the runner has follow-up questions. Six specialists are available — medical, weather, pacing, gear, nutrition, mental.*

*A coordinator agent decides which ones to call for each question. Watch."*

```
[CLICK suggestion pill: "What about my fueling plan?"]
[WAIT ~8s, narrating during the wait]
```

*"I just asked about fueling. Watch the specialist row.*

*Only nutrition lights up. The other five stay dim. The coordinator looked at the question, decided only nutrition was relevant, and called just that one."*

```
[Response renders in chat history]
```

*"Done. One LLM call to the coordinator, one to the nutrition specialist, one to synthesize. Three calls total — only one specialist actually fired."*

```
[CLICK suggestion pill: "Should I race today?"]
[WAIT ~12s, narrating during the wait]
```

*"Now I'm asking 'should I race today?' — that's a broad question. Watch what happens this time."*

```
[Three pills light cyan simultaneously: medical + weather + pacing]
```

*"Three specialists lit up at the same time. The coordinator decided medical, weather, and pacing are all relevant for a question about whether to race. And it didn't call them one at a time — it called all three in parallel."*

```
[All three complete, response synthesizes]
```

*"All three responded in parallel. Total wall time for the three: roughly the time of one LLM call. The coordinator synthesized their answers into one cohesive response: 'You should only race if you commit to a slower pace...'*"

## Explain the demo — code reveal (3:30 – 5:00)

```
[CUT TO IDE — workflows/concierge.py line 75]
```

```python
race_concierge = Agent(
    name="race_concierge",
    model="gemini-flash-latest",
    sub_agents=[
        medical_specialist,
        weather_specialist,
        pacing_specialist,
        gear_specialist,
        nutrition_specialist,
        mental_specialist,
    ],
    instruction="Pick relevant specialists and invoke in parallel...",
)
```

*"That's the coordinator. Six sub_agents — that's the list of specialists. The instruction tells the coordinator to pick relevant ones and invoke them in parallel by emitting multiple function calls in one turn.*

*The framework auto-injects a delegation tool per subagent. The coordinator's LLM just calls them — one, two, or all six — depending on the question. That's the entire mechanism."*

## Body — segment 3: the 1.x comparison (5:00 – 6:30)

```
[CUT to examples/adk_1x_equivalent/mode2_collab_equivalent.py, scroll through]
```

*"Here's how this looked in 1.x. There are two options. Both are bad.*

*Option 1: ParallelAgent with all six specialists. Works. But it ALWAYS runs all six. For the fueling question, you'd run all six specialists every time. Five of those calls are wasted."*

```
[OVERLAY: "Approach #1: 7 LLM calls per question, always"]
```

*"Option 2: a coordinator with sub_agents and transfer_to_agent. Better — only relevant specialists run. But transfer_to_agent is SERIAL. One specialist at a time. For a question that needs three specialists, wall time scales linearly."*

```
[OVERLAY: "Approach #2: serial, ~3× wall time"]
```

*"Neither option gives you 'LLM picks a subset, runs in parallel.' That's the gap 2.0's collab agents fill. It's the only thing that does."*

```
[OVERLAY: big comparison]
  1.x Approach #1: 7 calls always
  1.x Approach #2: serial execution
  2.0:             dynamic subset + parallel
```

## Recap + tease (6:30 – 7:00)

*"Collaborative agents in one sentence: LLM-driven dynamic delegation with parallel execution.*

*Use them when the routing decision itself benefits from LLM reasoning. Use the older Sequential or Parallel agents when the routing is deterministic.*

*Next episode: dynamic workflows. We're going to ask an open research question and watch the LLM decide — at runtime — how many sub-questions to spawn, and recursively spawn more from inside its own parallel branches. Subscribe."*

---

# Episode 3 — Dynamic Workflows: "When the LLM Decides the Shape" (~8 min)

## Presenter intro + promise (0:00 – 0:15)

```
[CAMERA ON ANNIE]
```

*"Hi, I'm Annie. By the end of this video, you'll learn when dynamic workflows are worth the added complexity, when they're overkill, and the one decorator that makes recursive parallel work possible inside the ADK framework without dropping out to raw asyncio."*

## Title card (0:15 – 0:25)

```
  ADK 2.0 — Episode 3
  
  Dynamic Workflows
  "When the LLM Decides the Shape"
```

## Demo with narration (0:25 – 4:00)

```
[SHOW: browser scrolled to Mode 3 — Deep Research panel]
```

*"This is Mode 3 — deep research. Same marathon theme, but a different question — 'tell me everything I should know about racing Boston.'*

*This isn't a chat question. It's not a structured planning question. It's an open research question. You don't know how many sub-questions it'll need. You don't know how deep the research will go. The shape of the work depends entirely on the question."*

```
[CLICK "Deep-dive: Boston Marathon" preset button]
[WATCH for 25+ seconds, narrate the tree growing]
```

*"I just clicked Boston. Watch the tree form."*

```
[Decomposer pulses]
```

*"The decomposer agent just fired. It's reading the question and deciding what sub-questions to research."*

```
[6-8 sub-question cards appear in cyan]
```

*"Six sub-questions decomposed. Course profile. Weather history. Common pitfalls. Pacing strategies. Gear norms. Famous hills. All researching in parallel."*

```
[Some complete, then deeper children appear under them]
```

*"And — here. See that branch growing? One of the research agents decided its finding warranted a deeper investigation. It just spawned three child questions of its own. Those are now researching in parallel under their parent.*

*The tree is growing in shape determined by what the LLM finds. Not by anything I wrote in code."*

```
[Wait for synthesis]
```

*"Synthesizer firing. It's aggregating findings from the whole tree."*

```
[Final briefing card renders]
```

*"And here's the briefing. Headline, sections, key warnings. 17 LLM calls completed in 30 seconds of wall time. If those calls had run serially, that would have been roughly two minutes."*

## Explain the demo — code reveal (4:00 – 5:15)

```
[CUT to IDE — workflows/deep_research.py around line 84]
```

```python
@node(parallel_worker=True, rerun_on_resume=True)
async def research_subquestion(ctx, node_input):
    question = node_input
    finding = await research_agent.run(question)
    
    # The killer line — recursive parallel fan-out
    if finding.needs_deeper:
        children = await ctx.run_node(
            research_subquestion,
            node_input=finding.deeper_questions,
        )
        finding.children = children
    
    yield Event(output=finding)
```

*"This is the dynamic node. The decorator — parallel_worker=True — tells the framework: when this node receives a list, spawn one parallel task per item.*

*The killer line is in the middle. `ctx.run_node(research_subquestion, deeper_questions)` — the node is calling ITSELF recursively, with a new list. That list might have one item or five. Each one becomes a parallel task. Each of those might recurse again.*

*The tree shape is the data structure. The code just says 'recurse if needed.'"*

## Structured theory (5:15 – 7:00)

```
[BULLET 1 APPEARS]

  1. RUNTIME-SHAPED TOPOLOGY
```

*"The number of parallel branches AND the depth of the tree are determined at runtime, by data. The LLM decided here that some sub-questions warranted deeper research, others didn't. The code doesn't hardcode the shape — only the per-node behavior."*

```
[BULLET 2 APPEARS]

  2. RECURSIVE FAN-OUT INSIDE THE FRAMEWORK
```

*"`@node(parallel_worker=True)` plus recursive `ctx.run_node` lets a parallel branch spawn more parallel branches. ADK 1.x literally couldn't do this with framework primitives — you'd either cram everything into one mega-LlmAgent that hallucinates, or drop out to raw asyncio and lose framework tracing, checkpointing, and resumability."*

```
[BULLET 3 APPEARS]

  3. FRAMEWORK BENEFITS STAY INTACT
```

*"Because the recursion is inside the framework, you keep everything — per-node event tracing, automatic checkpointing, resumable execution. If research task 7 of 11 fails, you can retry just that one. With raw asyncio, you'd restart all 11."*

```
[CARD: "When to use Pillar 3"]
```

*"Reach for dynamic workflows when the topology depends on data — loops, recursion, runtime-sized fan-out. When the static graph of Pillar 1 isn't expressive enough."*

```
[OVERLAY large comparison]
  Recursive parallel fan-out:
  
  1.x mega-agent:      hallucinates, no parallelism
  1.x raw asyncio:     works but OUTSIDE framework
  2.0 dynamic:         native, recursive, all framework benefits
```

## Recap + tease (7:00 – 7:30)

```
[CAMERA BACK ON ANNIE]
```

*"Dynamic workflows: runtime-shaped, recursive parallel fan-out, with all framework benefits intact. Use them when the topology depends on data the code doesn't have.*

*Last episode: ADK 1.x versus 2.0 — three problems, three side-by-side comparisons. The one episode that pulls everything together. Subscribe."*

---

# Episode 4 — ADK 1.x vs 2.0: "Three Problems That Needed Solving" (~7 min)

This is the synthesis episode. It IS the decision tree — but framed as before/after instead of "here's a flowchart."

## Presenter intro + promise (0:00 – 0:15)

```
[CAMERA ON ANNIE]
```

*"Hi, I'm Annie. By the end of this video, you'll have a complete mental decision tree for picking the right ADK 2.0 pillar for any agent problem — and you'll see exactly what ADK 1.x couldn't do in three side-by-side code comparisons."*

## Title card (0:15 – 0:25)

```
  ADK 2.0 — Episode 4
  
  ADK 1.x vs 2.0
  "Three Problems That Needed Solving"
```

## Segment 1 — Graph Workflows (0:45 – 2:30)

```
[SLIDE: "Problem: structured planning workflow with parallel data + deterministic routing"]
[Hold 5 seconds]
```

*"Problem number one. You have three pieces of data to fetch in parallel. A bundling step. A routing decision based on the data. Then one structured LLM call. Marathon strategy planning is the example, but this shape applies to invoice processing, PR review, ticket triage — anything you can DRAW before you build."*

```
[SPLIT SCREEN]
[LEFT: examples/adk_1x_equivalent/mode1_graph_equivalent.py — highlight the painful parts]
[RIGHT: workflows/strategy_graph.py edges block]
```

*"On the left — 1.x. Three LlmAgent definitions just to fetch data. A SequentialAgent. A ParallelAgent. The strategist's instruction with 200 tokens of routing logic.*

*On the right — 2.0. Eight lines. Function nodes as peers with agent nodes. Routing is a four-line Python function."*

```
[OVERLAY: big numbers]
  LLM CALLS:         4  →  1
  LINES OF CODE:    ~80 →  8
  ROUTING:           prompt judgment  →  Python `if`
```

*"That's Pillar 1. Graph workflows. Use them when the structure is known."*

## Segment 2 — Collaborative Agents (2:30 – 4:15)

```
[SLIDE: "Problem: coordinator delegates to N specialists, dynamically, in parallel"]
```

*"Problem number two. You have a coordinator and a team of specialists. The user asks a question. The coordinator needs to decide which specialists are relevant — could be one, could be all six — and run them in parallel."*

```
[SPLIT SCREEN]
[LEFT: examples/adk_1x_equivalent/mode2_collab_equivalent.py — show both 1.x options]
[RIGHT: workflows/concierge.py — coordinator with sub_agents]
```

*"On the left — 1.x. Two options, both bad.*
*ParallelAgent always runs all six specialists. Wasteful.*
*Or coordinator with transfer_to_agent — serial, one specialist at a time. Slow.*

*On the right — 2.0. The coordinator picks a dynamic subset based on the question, and runs them in parallel in a single turn."*

```
[OVERLAY]
  For "What about fueling?" question:
  1.x always-all:       7 LLM calls
  1.x serial transfer:  3 LLM calls, ~12s
  2.0:                  2 LLM calls, ~10s
  
  For "Should I race today?" question:
  1.x always-all:       7 LLM calls
  1.x serial transfer:  5 LLM calls, ~30s
  2.0:                  4 LLM calls, ~13s (PARALLEL)
```

*"That's Pillar 2. Collaborative agents. Use them when an LLM should be picking who handles each request."*

## Segment 3 — Dynamic Workflows (4:15 – 6:00)

```
[SLIDE: "Problem: tree-shaped recursive work where the LLM decides the topology"]
```

*"Problem number three. You're doing deep research. The LLM decomposes a question into sub-questions. Each sub-question might spawn more sub-questions based on what's found. The tree shape — width and depth — is decided at runtime."*

```
[SPLIT SCREEN]
[LEFT: examples/adk_1x_equivalent/mode3_dynamic_equivalent.py — show the raw asyncio]
[RIGHT: workflows/deep_research.py — the parallel_worker decorator]
```

*"On the left — 1.x. You have two options. Either cram everything into one mega-LlmAgent — quality fails, no parallelism. Or drop OUT of the framework and write raw asyncio orchestration. Now you lose tracing, checkpointing, resumability — every framework benefit.*

*On the right — 2.0. One decorator. parallel_worker=True. Recursive ctx.run_node from inside the node. Everything stays inside the framework with full observability."*

```
[OVERLAY]
  1.x mega-agent:        quality fails, no parallelism
  1.x raw asyncio:       works but OUTSIDE the framework
  2.0:                   recursive + parallel + inside framework
```

*"That's Pillar 3. Dynamic workflows. Use them when the topology depends on data."*

## Closer (6:00 – 7:00)

```
[CUT TO: clean slide with three pillar logos side by side]
[ADK 2.0 brand color]
```

*"Three problems. Three solutions.*

*Graph workflows: known structure.*
*Collaborative agents: LLM-driven delegation.*
*Dynamic workflows: runtime topology.*

*You can mix them. Production apps usually do. A graph workflow can contain a collab coordinator. A dynamic worker can invoke a graph workflow per item.*

*If you've used ADK 1.x, you know which of these problems made you write the most painful code. That's the pillar you should reach for first.*

*The full demo, all the docs, the 1.x reference snippets — link in the description. Subscribe for the tutorial series that'll teach you to build this from scratch."*

```
[END CARD: repo link + "Tutorial series coming soon"]
```

---

## Release schedule

Two viable cadences:

### Aggressive (2 weeks total)

| Day | Episode |
|---|---|
| Day 0 | Ep 1 release + announce |
| Day 3 | Ep 2 |
| Day 7 | Ep 3 |
| Day 14 | Ep 4 |

Front-loads attention. Best if you want to capture audience momentum from one launch moment.

### Sustainable (4-8 weeks total)

| Week | Episode |
|---|---|
| Week 1 | Ep 1 |
| Week 3 | Ep 2 |
| Week 5 | Ep 3 |
| Week 7 | Ep 4 |

Slower build but each episode gets more time to find its audience before the next drops.

## Per-episode production cost

| Episode | Recording | Editing | Total |
|---|---|---|---|
| Ep 1 | 1.5 hr | 4 hr | ~5.5 hr |
| Ep 2 | 1 hr | 3.5 hr | ~4.5 hr |
| Ep 3 | 1.5 hr | 4.5 hr | ~6 hr |
| Ep 4 | 1 hr | 5 hr (more graphic overlays) | ~6 hr |
| **Total** | **~5 hr** | **~17 hr** | **~22 hours** |

About **3 focused days** of production work for the full series.

## What's NOT in this plan (intentional)

- Detailed talking-head segments (you'll write those in your own voice during recording)
- Music selection (varies by your channel's brand)
- Specific transitions / effect choices (varies by your editing software)
- Sponsor reads / CTAs (depends on your distribution strategy)

This plan is the *structural* skeleton. Your voice, edits, and brand fill it out.

## Reuse map: assets already in this repo

| Asset | Used in |
|---|---|
| Marathon Mode 1 (live demo) | Ep 1 + cold open of Ep 4 |
| Marathon Mode 2 (live demo) | Ep 2 |
| Marathon Mode 3 (live demo) | Ep 3 + clips for cold opens |
| `workflows/strategy_graph.py` (code on screen) | Ep 1 + Ep 4 |
| `workflows/concierge.py` (code on screen) | Ep 2 + Ep 4 |
| `workflows/deep_research.py` (code on screen) | Ep 3 + Ep 4 |
| `examples/adk_1x_equivalent/mode1_*.py` | Ep 1 (comparison segment) + Ep 4 |
| `examples/adk_1x_equivalent/mode2_*.py` | Ep 2 (comparison segment) + Ep 4 |
| `examples/adk_1x_equivalent/mode3_*.py` | Ep 3 (comparison segment) + Ep 4 |
| `VIDEO_SCRIPT.md` (existing 20-min talk) | Reference for narration phrasing |
| `docs/ADK_2_GUIDE.md` | Reference for accuracy + per-pillar deep dives |
| `docs/ADK_2_PILLARS_DECISION_TREE.md` | Source for Ep 4 closer |

All four episodes reuse existing artifacts. The only new content is the narration script itself, which can be drafted from this plan.

---

## Next steps

1. **You review this plan** — flag anything you'd structure differently
2. **You record Ep 1** — start with the hardest, use it to calibrate the format
3. **Iterate based on Ep 1 reception** — adjust pacing, voice, transitions for Eps 2-4
4. **Release on chosen cadence**

If you want, I can draft a **verbatim word-for-word script** for any single episode (Ep 1 most likely candidate, since it sets the format). Each episode script would be ~1200-1500 spoken words, with frame-accurate stage directions. ~3 hours of writing per episode on my side.
