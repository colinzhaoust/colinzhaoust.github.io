# System Map: 4blue2brown Research Landscape

Snapshot date: 2026-07-01.

这张图把目前讨论的几类东西放在一起：3b1b public data、现有 papers/repos、agentic codegen pipeline、model backbone roles、evaluation/memory，以及最终 gap。

## Big Picture

```mermaid
flowchart LR
    subgraph PublicData["Public data / corpora"]
        A["3b1b/manim<br/>renderer + API"]
        B["3b1b/videos<br/>scene code corpus"]
        C["3Blue1Brown.com<br/>lesson metadata + article text"]
        D["captions / caption_ops<br/>transcripts + timing"]
        E["External benchmarks<br/>TheoremExplainBench, ManimBench"]
    end

    subgraph PriorWork["Existing systems / papers"]
        F["TheoremExplainAgent<br/>long-form theorem videos"]
        G["ManimTrainer<br/>SFT + GRPO + RITL-DOC"]
        H["LLM2Manim<br/>pedagogy + HITL"]
        I["ManimAgent / Paper2Manim<br/>episodic memory"]
        J["ALGOGEN<br/>trace-first algorithm visualization"]
        K["Paper2Video / PaperTalker<br/>multi-channel presentation videos"]
        L["Prototype repos<br/>manim-generator, Math-To-Manim, ManimCat"]
    end

    subgraph Pipeline["4blue2brown proposed pipeline"]
        M["Input<br/>topic / paper / theorem / lesson"]
        N["Reader + planner<br/>outline, prerequisites"]
        O["Scene-plan IR<br/>beats, objects, formulas, timing"]
        P["Symbol ledger<br/>notation, colors, objects"]
        Q["Scene codegen agent<br/>Manim Python"]
        R["Renderer harness<br/>logs, video, frames"]
        S{"Render ok?"}
        T["Log repair agent<br/>traceback -> code fix"]
        U["VLM reviewer<br/>layout + semantic checks"]
        V{"Visual ok?"}
        W["Revision agent<br/>structured critique -> patch"]
        X["Concat + narration<br/>subtitles, audio, final artifact"]
        Y["Memory bank<br/>success examples + failure pitfalls"]
    end

    subgraph Outputs["Outputs / eval"]
        Z["Generated video<br/>code + logs + frames"]
        AA["Quality tiers<br/>T0 rendered -> T5 polished"]
        AB["Metrics<br/>render success, layout, semantics, quiz"]
    end

    A --> Q
    B --> Q
    B --> Y
    C --> N
    C --> O
    D --> O
    D --> X
    E --> AB

    F --> N
    F --> R
    G --> Q
    G --> T
    H --> O
    H --> P
    I --> Y
    J --> O
    K --> X
    K --> AB
    L --> Q
    L --> R

    M --> N --> O --> P --> Q --> R --> S
    S -- "No" --> T --> Q
    S -- "Yes" --> U --> V
    V -- "No" --> W --> Q
    V -- "Yes" --> X --> Z
    U --> Y
    T --> Y
    Y --> N
    Y --> Q

    Z --> AA
    Z --> AB
```

## Model Roles

```mermaid
flowchart TB
    A["Planner model<br/>reasoning + pedagogy"] --> B["Scene-plan IR"]
    B --> C["Code model<br/>Python + Manim API"]
    C --> D["Renderer<br/>deterministic executor"]
    D --> E["Log fixer model<br/>tracebacks + API repair"]
    D --> F["VLM reviewer<br/>frames/video critique"]
    F --> G["Revision model<br/>visual critique -> code change"]
    E --> C
    G --> C

    H["Trace generator<br/>algorithm state simulation"] --> I["Verified trace JSON"]
    I --> J["Deterministic trace renderer"]
    J --> D

    K["Narration model<br/>clear explanation + pacing"] --> L["Captions / SRT / TTS"]
    L --> M["Final video assembly"]
    D --> M

    N["Memory / retrieval<br/>docs + examples + failures"] --> A
    N --> C
    N --> E
    F --> N
    E --> N
```

## Current Gaps

```mermaid
flowchart LR
    A["Current systems<br/>T1-T3 rough explainers"] --> B["Gap: layout<br/>overlap, sizing, offscreen"]
    A --> C["Gap: correctness<br/>pretty but wrong"]
    A --> D["Gap: long-horizon coherence<br/>notation drift"]
    A --> E["Gap: timing<br/>visuals not aligned to narration"]
    A --> F["Gap: evaluation<br/>render success is too weak"]
    A --> G["Gap: polish<br/>taste, pacing, editing"]

    B --> H["Deterministic layout primitives<br/>safe areas + screenshot checks"]
    C --> I["Symbolic validators<br/>trace checks + human review"]
    D --> J["Symbol ledger<br/>scene contracts + global reviewer"]
    E --> K["Caption/timing-aware IR<br/>beats as first-class data"]
    F --> L["Multi-layer eval<br/>render, layout, semantics, viewer quiz"]
    G --> M["Human-in-loop editing<br/>style recipes + curated examples"]
```

## Read This Diagram As A Strategy

The relationship between the pieces is:

1. `3b1b/videos` and Manim give us the code substrate.
2. `3Blue1Brown.com` and captions give us lesson/narration/timing structure.
3. TheoremExplainAgent proves long-form Manim agents are possible.
4. ManimTrainer tells us renderer-in-the-loop and code-specialized backbones matter.
5. LLM2Manim tells us pedagogy constraints and symbol ledgers are necessary.
6. ALGOGEN tells us to decouple state simulation from rendering whenever possible.
7. ManimAgent/Paper2Manim tells us memory should be split into successes and known pitfalls.
8. Our pipeline should turn all of this into a measurable loop before trying fine-tuning.
