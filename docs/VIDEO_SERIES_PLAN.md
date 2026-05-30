# ADK 2.0 Video Series — 4 Episodes, Frame-Accurate Plan

This doc plans a **4-episode series** for the ADK 2.0 marathon demo. Each episode targets **7-8 minutes**, **demo-first cold open**, **substantial code/comparison content**.

Distinct from `VIDEO_SCRIPT.md` (which is a single 20-min conference talk covering all three pillars in one go). The series breaks that talk into four standalone videos optimized for YouTube depth + retention.

---

## Series at a glance

| Ep | Title | Length | Live demo | Core unique-to-2.0 angle |
|---|---|---|---|---|
| 1 | Graph Workflows — One LLM Call Instead of Four | **6 min** | Mode 1 (Hot Boston, ~75s) | Function nodes + agent nodes as peers; deterministic Python router |
| 2 | Collaborative Agents — Same UI, Different Outcomes | **7 min** | Mode 2 (3 contrasting questions, ~2:30) | LLM coordinator picks dynamic subset, runs in parallel |
| 3 | Dynamic Workflows — When the LLM Decides the Shape | **6 min** | Mode 3 (Boston preset, ~90s) | Recursive parallel fan-out with topology decided at runtime |
| 4 | ADK 1.x vs 2.0 — Three Problems That Needed Solving | **6-7 min** | None (code split-screens) | Concrete before/after for each pillar |
| | **Total** | **~25-26 min** | | |

**Why tighter than the original 30-min plan?** Three episode demos are short live runs (7-30s of actual execution). Stretching them to 3 minutes was padding. Tighter demos + more time spent on concrete real-world examples in the theory bullets = better retention AND better learning.

---

## Universal production specs (apply to all 4 episodes)

### Structural formula

Every episode follows the same pedagogical flow. Talking-head presenter intro → demo → explain demo → structured theory with concrete examples → recap.

```
0:00 – 0:15   PRESENTER INTRO + LEARNING PROMISE
              [Camera on Annie]
              "Hi, I'm Annie. By the end of this video, you'll learn [X]."

0:15 – 0:25   TITLE CARD: episode #, big bold title

0:25 – 1:40   DEMO with live narration (~75s for Eps 1/3, ~2:30 for Ep 2)
              [Show the visual, narrate what's happening, NO theory yet]
              Demos are SHORT because the actual execution is short.
              Don't pad — let the visual breathe, then move on.

1:40 – 2:50   EXPLAIN THE DEMO (~1:10)
              [Code reveal — "here's what made that happen"
               Show one snippet, highlight 1-2 key lines]

2:50 – 5:15   STRUCTURED THEORY WITH EXAMPLES (~2:25)
              [Numbered bullets, each with its own card on screen]
              "Three things to take away:"
              
              "1. <FIRST CONCEPT>"
                 ◆ Concrete example from the marathon demo
                 ◆ Concrete example from a different domain
                    (PR review / customer support / document processing / etc.)
                 ◆ What ADK 1.x couldn't do here
              
              "2. <SECOND CONCEPT>"  [same pattern: marathon + non-marathon + 1.x]
              "3. <THIRD CONCEPT>"   [same pattern]
              
              [Closing card: "When to use [Pillar]"]

5:15 – 5:30   "TRY IT YOURSELF" CTA (~15s)
              "Full repo + companion Colab linked in the description.
               Clone it, modify it, break it — that's how this clicks."

5:30 – 6:00   RECAP + TEASE next episode
              [Camera back on Annie]
```

### Why the per-bullet examples matter

Abstract bullets ("functions and agents as peers") don't stick.
Concrete examples make them sticky. Pattern: 1 marathon example + 1-2
non-marathon examples per bullet, so non-runner viewers have a bridge
to their own work.

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

# Episode 1 — Graph Workflows: "One LLM Call Instead of Four" (~6 min)

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

## Demo with narration (0:25 – 1:40, ~75 seconds)

The actual workflow runs in 7 seconds. Don't pad — let the visual breathe.

```
[SHOW: browser at http://127.0.0.1:8000/ — Mode 1 panel visible]
```

*"Mode 1 of the marathon app. A runner wants a race-day strategy. The graph on the left will fetch weather, course, and fitness data in parallel, bundle them, route based on temperature, and call one LLM to write the plan."*

```
[CLICK: Hot · Boston in header]
[CLICK: Run]
[STAY ON the visualization through the full run]
```

*"Watch the three nodes. Pulsing in parallel. Each has a live timer. These are plain Python functions — no LLM calls happening here."*

```
[Pull-fitness completes first → JoinNode flashes after the last fetch → router fires]
```

*"All three done. JoinNode bundled them. Router looked at the temperature — 78 degrees — and picked the hot-weather branch. That router is a four-line `if` statement. Not LLM judgment. Just Python."*

```
[Strategy agent runs ~5s → strategy card renders]
```

*"And the strategy. Target: 3:35. Pacing references the runner's actual 7:30 pace, the 78-degree heat, and the 4.5 percent grade at mile 20."*

```
[CUT to stats card. OVERLAY: "1 LLM CALL"]
```

*"Seven seconds total. **One LLM call.** Fan-out saved 2.5 seconds on the fetch phase. The model only ran for the part that genuinely needed reasoning."*

## Explain the demo — code reveal (1:40 – 2:50, ~70 seconds)

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

## Structured theory with examples (2:50 – 5:15, ~2:25)

```
[SLIDE FORMAT: clean background, large numbered bullets appear one at a time
 Each bullet stays on screen while the examples are narrated]
```

*"Three things to take away from graph workflows."*

```
[BULLET 1 APPEARS]

  1. FUNCTIONS AND AGENTS AS PEERS
```

*"Function nodes and Agent nodes sit as equals in the same `edges` array. Three concrete examples:*

*In our marathon demo, `fetch_weather` is async Python calling an API. No reasoning needed. It's a function node alongside the strategy agent.*

*In a code-review bot, your `run_tests` and `parse_lint_output` are function nodes. The LLM agent that writes the human PR comment is the only LLM call.*

*In a document processor, your `extract_pdf_text` is a function node. The LLM agent that summarizes is the only LLM call.*

*In ADK 1.x, you'd have to wrap each function in an LlmAgent just to call it. Three useless LLM calls per fetch. That's the 4× cost difference."*

```
[BULLET 2 APPEARS]

  2. ROUTING IS DETERMINISTIC
```

*"Branching on data is a Python `if` statement, not a prompt. Three examples:*

*Our marathon router: `if temp >= 70 return HOT, elif temp <= 40 return COLD, else NORMAL`. Four lines.*

*A customer-support triage app: `if ticket.amount > 10000 return ENTERPRISE, elif ticket.urgency == 'critical' return PRIORITY, else return STANDARD`. Same pattern.*

*A research workflow: `if confidence < 0.7 return NEEDS_DEEPER_RESEARCH, else return READY_TO_SYNTHESIZE`. Same pattern.*

*In 1.x, this lived in a coordinator agent's prompt. Sometimes right, occasionally wrong on edge cases. In 2.0, it's code. It cannot be wrong."*

```
[BULLET 3 APPEARS]

  3. TYPED HANDOFF VIA JOINNODE
```

*"When parallel branches converge, JoinNode bundles their outputs into a typed Pydantic payload. Examples:*

*Marathon: three fetch outputs become a `BundledRunData` object the strategy agent reads as typed input.*

*Customer support: a parallel fetch of `customer_history + recent_orders + open_tickets` converges into one `CustomerContext` payload for the routing agent.*

*Document processing: parallel calls to extract `text + tables + images` converge into one `ParsedDoc` payload for the summarizer.*

*Compare 1.x's `ParallelAgent`: each sub-agent writes to shared session state by key. The downstream agent reads strings and hopes the keys match. No typed validation."*

```
[CARD: "When to use Pillar 1"]
```

*"Reach for graph workflows when the structure of the work is known — you can draw the diagram before you write code, and routing decisions can be rules instead of LLM judgment."*

```
[OVERLAY large comparison graphic]
  LLM CALLS:         4  →  1
  LINES OF CODE:    ~80  →  8
  ROUTING:           prompt-based  →  Python `if`
```

## "Try it yourself" CTA (5:15 – 5:30, ~15s)

```
[CAMERA BACK ON ANNIE — quick energy shift]
```

*"Full repo plus a companion Colab notebook linked in the description. Clone the repo, paste your API key, run it locally — that's how this clicks."*

## Recap + tease (5:30 – 6:00, ~30s)

```
[CAMERA ON ANNIE]
```

*"Graph workflows in one sentence: when the structure of your work is known, draw the diagram in code and let the framework run it.*

*Next episode: collaborative agents. Same chat box, different inputs, different specialists firing in parallel — and one specific feature that's impossible to build in ADK 1.x. Subscribe so you don't miss it."*

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

## Demo with narration (0:25 – 2:55, ~2:30)

The whole point of this episode is the dispatch variability — you need at least 2 contrasting questions to make the point. Third question is the "and now all 6" reveal.

```
[SHOW: browser scrolled to Mode 2 chat panel — 6 specialist pills visible]
```

*"Mode 2: the concierge. Six specialists — medical, weather, pacing, gear, nutrition, mental. A coordinator agent picks which to invoke per question. Watch three contrasting questions."*

```
[CLICK pill: "About fueling"]
[WAIT ~10s, narrate]
```

*"Asked about fueling. Only nutrition lit up. The other five stay dim. Coordinator decided only one specialist was relevant."*

```
[Response renders]
[CLICK pill: "Should I race today?"]
[WAIT ~13s, narrate]
```

*"Now: 'should I race today?' Three pills just lit up — medical + weather + pacing. All three at the same time. The coordinator picked three specialists for this question and invoked them in parallel."*

```
[Three responses complete in parallel]
[CLICK pill: "Full review"]
[WAIT ~15s, narrate]
```

*"One more: 'anything I should worry about overall?' All six pills light up. Coordinator decided this needs every specialist. Six LLM calls — all running concurrently."*

```
[Six responses complete; final synthesized response renders]
[OVERLAY: tally — 1 then 3 then 6 specialists invoked]
```

*"Same UI. Same code. Three different dispatch patterns: one, three, six. The coordinator's LLM picked each subset based on the question — at runtime."*

## Explain the demo — code reveal (2:55 – 3:45, ~50s)

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

## Structured theory with examples (3:45 – 6:15, ~2:30)

```
[BULLET 1 APPEARS]

  1. THE COORDINATOR PICKS A DYNAMIC SUBSET
```

*"The coordinator's LLM decides per-request which subagents to invoke. Three examples:*

*Our marathon concierge: 'fueling?' → 1 specialist. 'should I race?' → 3. 'full review' → 6. Same code path, different subsets.*

*A customer support coordinator: 'billing question' → 1 specialist. 'my account is locked AND I was double-charged' → 2 (security + billing). 'general angry rant' → triage everyone.*

*A code-review bot: a docs-only PR → 1 specialist (style). A new API endpoint → 3 (security + docs + tests). A schema migration → all 5 plus a database reviewer."*

```
[BULLET 2 APPEARS]

  2. SELECTED SUBAGENTS RUN IN PARALLEL
```

*"Once the coordinator picks the subset, they all fire in one turn — concurrently.*

*Marathon: 3 specialists for 'should I race?' run in ~13 seconds total, not 30.*

*Customer support: 'security + billing' run together, response comes back in one LLM call's worth of time.*

*Code review: 5 specialists analyzing a PR finish in parallel — the bot comments roughly when the slowest one completes, not the sum.*

*This is the genuinely new feature. In ADK 1.x, `ParallelAgent` always ran every sub-agent — no dynamic subset. `transfer_to_agent` ran specialists serially. Neither could do 'LLM picks N, runs them in parallel.'"*

```
[BULLET 3 APPEARS]

  3. SUBAGENT MODES CONTROL RETURN BEHAVIOR
```

*"Each subagent has a `mode`. Three options:*

*`single_turn` — pure transform, runs in parallel. What our specialists use. What you use when the subagent has one job per request.*

*`task` — bounded work that might ask clarifying questions. Auto-returns when done. Useful for things like 'gather missing info from the user before booking.'*

*`chat` — full conversation with the user. Manual handoff. Useful for long onboarding flows.*

*Only single_turn supports parallel execution. The other two are sequential by design."*

```
[CARD: "When to use Pillar 2"]
```

*"Reach for collaborative agents when the routing decision itself benefits from LLM reasoning — and when you want parallel execution of a dynamic subset of specialists."*

```
[OVERLAY large comparison]
  For 1-specialist question (e.g. "About fueling"):
    1.x ParallelAgent always:  7 LLM calls
    1.x transfer_to_agent:     3 calls, serial
    2.0 collab:                2 calls, parallel
  
  For 3-specialist question (e.g. "Should I race today?"):
    1.x ParallelAgent always:  7 LLM calls
    1.x transfer_to_agent:     5 calls, ~30s serial
    2.0 collab:                4 calls, ~13s parallel
```

## "Try it yourself" CTA (6:15 – 6:30, ~15s)

```
[CAMERA BACK ON ANNIE]
```

*"Full repo plus Colab in the description. Try modifying the coordinator's instruction — see how it changes which specialists fire."*

## Recap + tease (6:30 – 7:00, ~30s)

```
[CAMERA ON ANNIE]
```

*"Collaborative agents: LLM-driven dynamic delegation, parallel execution. Use them when the routing decision benefits from LLM reasoning.*

*Next episode: dynamic workflows. We'll ask an open research question and watch the LLM decide — at runtime — how many sub-questions to spawn AND recursively spawn more. Subscribe."*

---

# Episode 3 — Dynamic Workflows: "When the LLM Decides the Shape" (~6 min)

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

## Demo with narration (0:25 – 1:55, ~90 seconds)

The Boston preset takes ~25-30s of actual execution. Don't pad. Let the tree grow on screen.

```
[SHOW: browser scrolled to Mode 3 — Deep Research panel]
```

*"Mode 3: deep research. An open question — 'tell me everything I should know about racing Boston.' You don't know how many sub-questions this needs. You don't know how deep the research will go. The shape of the work depends on the question."*

```
[CLICK "Deep-dive: Boston Marathon" preset button]
[Watch silently for the first 3-4 seconds while decomposer fires]
```

*"Decomposer just fired. Six sub-questions appeared — course profile, weather history, common pitfalls, pacing, gear, hills. All researching in parallel."*

```
[After ~10s: some research nodes complete; children appear under some parents]
```

*"There. Two of those branches just spawned children. The research agents decided their findings warranted deeper investigation — and recursively kicked off new parallel research. The tree is growing in shape determined by the LLM, not by code I wrote."*

```
[Final briefing card renders]
[OVERLAY: "17 LLM calls · 30 seconds wall time · serial would be ~2 minutes"]
```

*"And there's the briefing. Seventeen LLM calls. Thirty seconds wall time. If those had run serially: about two minutes."*

## Explain the demo — code reveal (1:55 – 3:00, ~65s)

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

## Structured theory with examples (3:00 – 5:15, ~2:15)

```
[BULLET 1 APPEARS]

  1. RUNTIME-SHAPED TOPOLOGY
```

*"Both the width and the depth of the parallel work are decided at runtime by data. Three examples:*

*Marathon deep research: the LLM decomposes the question into N sub-questions (could be 4, could be 8) and some of those spawn deeper children based on findings.*

*Document processing pipeline: user uploads a folder with an unknown number of PDFs. The workflow spawns one parallel branch per PDF — count from the upload, not from the code.*

*GitHub PR triage agent: 'review all open PRs in this repo' — could be 3 PRs, could be 50. The framework fans out per-PR, scaling with the data."*

```
[BULLET 2 APPEARS]

  2. RECURSIVE FAN-OUT INSIDE THE FRAMEWORK
```

*"A parallel branch can spawn MORE parallel branches by calling `ctx.run_node` on itself with a new list. Examples:*

*Marathon research: one finding leads to three deeper questions. Those research in parallel under their parent.*

*Multi-level org chart query: 'summarize each VP's team' → for each VP, fan out per direct report → for each director, fan out per IC.*

*Recursive web crawling: 'crawl this page' → discover N links → fan out to crawl each → some discover more links → continue until depth limit.*

*In ADK 1.x, you literally cannot do this with framework primitives. You'd either cram it into one mega-LlmAgent (quality fails) or drop OUT of the framework to raw asyncio and lose tracing, checkpointing, and resumability."*

```
[BULLET 3 APPEARS]

  3. FRAMEWORK BENEFITS STAY INTACT
```

*"Because the recursion is inside the framework, every per-node feature works:*

*Per-node event tracing — every research call shows up in your OpenTelemetry traces.*

*Automatic checkpointing — if research task 7 of 11 fails, you retry just that one. The framework knows which are done.*

*Resumability — kill the process mid-research, restart, framework skips completed branches.*

*In the raw-asyncio version of this, you'd write all of that yourself."*

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

## "Try it yourself" CTA (5:15 – 5:30, ~15s)

```
[CAMERA BACK ON ANNIE]
```

*"Full repo and Colab in the description. Try changing the decomposer's instruction — see how the tree shape changes."*

## Recap + tease (5:30 – 6:00, ~30s)

```
[CAMERA ON ANNIE]
```

*"Dynamic workflows: runtime-shaped, recursive parallel fan-out, with all framework benefits intact. Use them when the topology depends on data the code doesn't have.*

*Last episode: ADK 1.x versus 2.0 — three problems, three side-by-side comparisons. The episode that pulls everything together. Subscribe."*

---

# Episode 4 — ADK 1.x vs 2.0: "Three Problems That Needed Solving" (~6-7 min)

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

## Closer + try-it-yourself CTA (6:00 – 6:45, ~45s)

```
[CUT TO: clean slide with three pillar logos side by side]
[ADK 2.0 brand color]
```

*"Three problems. Three solutions.*

*Graph workflows: known structure.*
*Collaborative agents: LLM-driven delegation.*
*Dynamic workflows: runtime topology.*

*You can mix them. Production apps usually do — a graph workflow can contain a collab coordinator; a dynamic worker can invoke a graph workflow per item.*

*If you've used ADK 1.x, you know which of these problems made you write the most painful code. That's the pillar you should reach for first."*

```
[CAMERA BACK ON ANNIE]
```

*"Full repo with all three pillars, the 1.x reference snippets we compared, and companion Colabs — all linked in the description. Clone it, try it, break it.*

*Subscribe for the tutorial series next, where we build each pillar from scratch."*

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

(Revised lower now that demos are tighter.)

| Episode | Length | Recording | Editing | Total |
|---|---|---|---|---|
| Ep 1 | ~6 min | 1 hr | 3 hr | ~4 hr |
| Ep 2 | ~7 min | 1 hr | 3.5 hr | ~4.5 hr |
| Ep 3 | ~6 min | 1 hr | 3 hr | ~4 hr |
| Ep 4 | ~6-7 min | 0.5 hr | 4 hr (more graphic overlays, no live demo) | ~4.5 hr |
| **Total** | **~25-26 min** | **~3.5 hr** | **~13.5 hr** | **~17 hours** |

About **2-2.5 focused days** of production work for the full series. (Down from the ~22 hours estimate in the longer version — tighter demos = less footage to edit.)

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
