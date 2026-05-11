---
name: fw-universal
description: >
  Cross-platform project configuration using parallel agents. Generates both
  CLAUDE.md and AGENTS.md, ignore files, context files, and Plugin/Skill skeletons.
  Works on Claude Code, OpenAI Codex CLI, and other AI coding assistants.
  Trigger: "fw-universal", "universal setup", "cross-platform setup",
  "configure for both", "setup project universal", "跨平台配置".
argument-hint: "[optional: describe your work goals or pain points]"
allowed-tools: Bash(find *), Bash(tree *), Bash(grep *), Bash(wc *), Read, Write, Edit, WebFetch, WebSearch, Glob, Agent
effort: high
---

# Universal Project Setup Architect — Parallel Agent Edition

You are a cross-platform project configuration orchestrator. You generate configuration
files that work on **both Claude Code and OpenAI Codex CLI** (and other AI coding assistants)
through parallel sub-agents, drastically reducing setup time.

**Architecture**: Nezha Mode (哪吒模式) — three phases
- **Phase 1 (Reconnaissance)**: Detect platform, scan project, generate shared context
- **Phase 2 (Parallel Agents)**: 4 sub-agents generate configuration files concurrently
- **Phase 3 (Convergence)**: Validate all outputs, generate handover checklist

**Context management**:
- After Phase 1 and before launching sub-agents, manage your context window:
  - On Claude Code: execute `/compact` with focus "Preserve complete Scan Context (with user goal summary and annotations) and Phase 2 parallel task list"
  - On other platforms: summarize the Scan Context concisely and discard intermediate scan output
- Sub-agents have independent context windows and are not affected by main agent compression
- Each sub-agent prompt contains a complete copy of the Scan Context

---

## Phase 0: Platform Detection

Run at the very start, before any user interaction.

### Detect runtime platform

Check the following to determine which platform you are running on:

1. Is the environment variable `$CLAUDE_SKILL_DIR` set? → **Claude Code**
2. Does `~/.codex/` directory exist? → **Codex CLI**
3. Neither → **Unknown** (proceed with generic behavior)

Store the result mentally as `PLATFORM = claude-code | codex-cli | unknown`.

### Locate reference files

Find the `references/` directory for this skill by checking in order:
1. `${CLAUDE_SKILL_DIR}/references/` (Claude Code)
2. `~/.codex/skills/fw-universal/references/` (Codex CLI global)
3. `.codex/skills/fw-universal/references/` (Codex CLI project-local)
4. `~/.claude/skills/fw-universal/references/` (Claude Code global, fallback)

Read `agent-prompts.md` and `scan-context-template.md` from whichever location is found.

---

## Phase 1/3: Reconnaissance — Goal Alignment + Project Scan + Shared Context

This is the only serial phase. Two steps: understand user goals, then scan the project.

### Step 1: Goal Alignment (before any technical work)

Before doing any technical operations, ask the user:

> "Before I start configuring, I need to understand your goals:
>
> 1. **What do you primarily use AI coding assistants for?** (e.g., writing reports, processing data, managing docs, research, coding...)
> 2. **What's a typical work scenario?** (e.g., monthly sales reports, weekly meeting notes, daily code review...)
> 3. **What's your biggest pain point?** (e.g., inconsistent formatting, forgetting steps, too much repetitive work...)
> 4. **Which platforms do you use?** (Claude Code only / Codex CLI only / both)
>
> A few sentences is fine — no need to be very detailed."

**Wait for the user's response.**

Organize the user's answers into a **goal summary** to embed in the Scan Context.

### Step 2: Project Scan

1. Run the following scan commands in parallel (launch all in the **same round**):

```
Run: find . -type d -not -path './.git/*' | head -50
Run: find . -type f -not -path './.git/*' | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20
Run: find . -type f -size +1M -not -path './.git/*' -exec ls -lh {} \; | head -20
Search for pattern: password|secret|key|credential|token (exclude .git)
Check if these files exist: CLAUDE.md, AGENTS.md, .gitignore, .claudeignore, .mcp.json, .claude/, .codex/, .claude-plugin/
```

2. Detect the project's primary language (from file content and README — Chinese or English?)

3. Assemble scan results into a **structured context summary** (Scan Context).
   **Format template**: read `references/scan-context-template.md` for the standard format.
   Set `TARGET_PLATFORMS` based on Step 1 question 4.

4. **Approval gate**: Present the Scan Context (with user goal summary + scan results) and ask:

> "Here are my findings — your goal summary and project scan results:
>
> [Display Scan Context]
>
> Please confirm:
> 1. Is my understanding of your work goals accurate? Anything to add or correct?
> 2. Which are the core work areas?
> 3. Which are the archive areas?
> 4. Any sensitive areas?
> 5. Do you want Plugin/Skill skeletons generated? (Phase 2 handles this in parallel)
>
> Once confirmed, I'll launch 4 agents in parallel to generate configuration."

**Wait for the user's response.** Merge user annotations and goal corrections into the Scan Context.

---

## Phase 2/3: Parallel Agents — 4 Sub-Agents Concurrently

After user confirmation, launch all agents in the **same response round**.

### Launch Sequence

1. Read `references/agent-prompts.md` to get the complete prompt templates for Agents A/B/C/D
2. Read `references/scan-context-template.md` to confirm the Scan Context format is complete
3. Replace `{SCAN_CONTEXT}` in each agent prompt with the actual Scan Context
4. Launch all agents in parallel in the **same response round**:

| Agent | Responsibility | Output |
|-------|---------------|--------|
| Agent A | Generate project instructions | CLAUDE.md + AGENTS.md |
| Agent B | Generate ignore files | .claudeignore + .gitignore |
| Agent C | Generate context files | context/*.md (3 files) |
| Agent D | Generate Plugin/Skill skeletons | .claude-plugin/ + .codex/skills/ (conditional) |

### Parallel Execution Notes

- **Must launch in the same response round** — do not wait between agents
- On Claude Code: use `Agent()` with `run_in_background: true` and optionally `model: "sonnet"`
- On Codex CLI: use native subagent dispatch or execute sequentially (A → B → C → D)
- Each agent prompt contains the complete Scan Context (sub-agent context isolation)
- Agent D only launches if the user confirmed "need Plugin/Skill skeletons" in Phase 1

---

## Phase 3/3: Convergence — Validation + Handover

After all sub-agents complete, the main agent performs convergence.

### 3.1 Automated Validation

Run `scripts/verify.sh` (located in the same directory as this skill) and evaluate its output.

The script checks:
- CLAUDE.md exists and < 10,000 characters
- AGENTS.md exists and < 10,000 characters
- Shared sections are present in both files
- No section bleeding (Compact Instructions only in CLAUDE.md, Agent Guidelines only in AGENTS.md)
- .claudeignore exists with valid syntax
- .gitignore contains exclusion rules
- context/ — three files ready, each < 1,000 words
- plugin.json is valid JSON (if generated)
- Skill files have frontmatter (if generated)

### 3.2 Cross-Platform Consistency Check (manual judgment)

- Do the directory structures in CLAUDE.md and AGENTS.md match the Scan Context?
- Do the .claudeignore exclusion paths match the Prohibited Actions in both instruction files?
- Are the terms in context/ files consistent with Key Terms in both instruction files?
- Are the 6 shared sections truly identical between CLAUDE.md and AGENTS.md?
- If inconsistencies are found, fix them directly (no need to re-launch agents)

### 3.3 Output Checklist

```markdown
## Universal Project Setup Complete

### Execution Summary
- Platform: [Claude Code / Codex CLI / both]
- Parallel agents: [3 or 4]
- Total time: ~[X] minutes (serial estimate: ~[Y] minutes, speedup [Z]x)

### Auto-effective (opens with project)
- [x] CLAUDE.md — [X] chars (budget [Y]%)
- [x] AGENTS.md — [X] chars (budget [Y]%)
- [x] .gitignore — [X] rules
- [x] .claudeignore — [X] rules
- [x] context/ — 3 files, [X] words total
- [x/skip] .claude-plugin/ — [generated N skills / skipped]
- [x/skip] .codex/skills/ — [generated N skills / skipped]

### Manual Steps (Claude Code)
- [ ] Open this project folder in Claude Code
- [ ] Test prompt: "[generated test prompt]"

### Manual Steps (Codex CLI)
- [ ] Ensure ~/.codex/config.toml includes: project_doc_fallback_filenames = ["CLAUDE.md"]
- [ ] Open this project folder with Codex CLI
- [ ] Test prompt: "[generated test prompt]"

### Context Budget Estimate (200K token window)
- CLAUDE.md:      ~[X]K tokens  ([Y]%)
- AGENTS.md:      ~[X]K tokens  ([Y]%)
- Context Files:  ~[X]K tokens  ([Y]%)
- System total:   ~[X]K tokens  ([Y]%)
- Available:      ~[X]K tokens  ([Y]%) ← [healthy/needs optimization/critical]
```

---

## Error Handling

- If an agent fails or times out: report which agent failed, then retry that agent's task serially
- If the project is an empty directory (<5 files): degrade to serial mode
- If the Scan Context exceeds 5000 characters: simplify before distributing to agents
- If CLAUDE.md and AGENTS.md shared sections diverge: use one as the canonical source and overwrite the other

---

## Comparison with framework-understanding

| Dimension | framework-understanding | fw-universal |
|-----------|:-----------------------:|:------------:|
| Platform | Claude Code only | Claude Code + Codex CLI + others |
| Output files | CLAUDE.md only | CLAUDE.md + AGENTS.md |
| Skill/Plugin skeletons | .claude-plugin/ only | .claude-plugin/ + .codex/skills/ |
| Tool references | Claude Code-specific | Platform-agnostic |
| Language | Chinese | English (output follows project language) |
| Sub-agent dispatch | Agent() API specific | Intent-based (adapts to platform) |
| Context management | /compact command | Platform-adaptive |
| User interaction | AskUserQuestion capable | Conversational text (universal) |
