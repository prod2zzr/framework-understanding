# Sub-Agent Prompt Templates (fw-universal)

Phase 2 launches parallel sub-agents using the prompts below.
Replace `{SCAN_CONTEXT}` in each prompt with the actual Scan Context from Phase 1.

Launch all agents in parallel:
- On Claude Code: use `Agent()` with `run_in_background: true`, optionally `model: "sonnet"`
- On Codex CLI: use native subagent dispatch or sequential fallback

---

## Agent A: Project Instructions Generator

```
You are a project instructions file generator. Your task is to create TWO
project instruction files — CLAUDE.md (for Claude Code) and AGENTS.md
(for OpenAI Codex CLI) — with shared core content and platform-specific
final sections.

## Input: Scan Context

{SCAN_CONTEXT}

## Task

### Step 1: Generate Shared Content

Draft the following sections (these will appear identically in BOTH files):

1. **Project Overview** — one paragraph describing the project purpose and scope
2. **Directory Structure** — list main directories and their purposes (match Scan Context)
3. **Key Terms** — project-specific terminology and definitions
4. **Work Preferences** — language, number format, date format, table style, citation rules
5. **Output Standards** — file naming rules, format requirements
6. **Prohibited Actions** — files/directories not to modify, operations not to perform

### Step 2: Write CLAUDE.md

Write the shared sections above, then append a Claude Code-specific final section:

```markdown
## Compact Instructions
When compressing context, preserve:
- User goal summary (primary purpose, typical scenario, core pain point)
- Current task plan and progress state
- Complete list of modified files
- Key points from each file in context/ directory
```

### Step 3: Write AGENTS.md

Write the same shared sections, then append a Codex CLI-specific final section:

```markdown
## Agent Guidelines
- Maintain awareness of project structure when working across files
- Reference context/ directory files for domain knowledge and standards
- Follow the output standards and naming conventions defined above
- Check prohibited actions before making changes to any file
```

## Constraints

- Write ALL content in the language specified by PRIMARY_LANGUAGE in Scan Context
- Target 2000-5000 characters per file, **never exceed 10,000 characters**
- After writing each file, verify size with: `wc -c CLAUDE.md AGENTS.md`
- If a CLAUDE.md already exists, read it first and merge new content (do not discard existing information)
- If an AGENTS.md already exists, read it first and merge similarly
- Sections 1-6 MUST be identical in both files — generate content once, write twice
- Emphasis depends on user goals:
  - User cares about formatting → detail Work Preferences and Output Standards
  - User cares about safety → detail Prohibited Actions
  - User cares about efficiency → detail Directory Structure and Key Terms

## Output

Report:
- Both file paths
- Character count for each
- Main section list
- Whether existing files were merged
```

---

## Agent B: Ignore Files Generator

```
You are a .gitignore / .claudeignore generation expert.

## Input: Scan Context

{SCAN_CONTEXT}

## Task

### 1. Generate .claudeignore

Exclude the following (only add entries that **actually exist** or are **reasonably expected**):

**Large files and directories**
- Files >1MB listed in Scan Context
- Directories >5MB

**Archive areas**
- Directories the user marked as archive in Scan Context

**Build artifacts** (only if the project actually uses these tools)
- node_modules/, dist/, build/, __pycache__/, .venv/, target/

**Sensitive files**
- .env, .env.*
- *.key, *.pem
- *credentials*, *secret*

**Binary media**
- *.zip, *.tar.gz, *.rar
- *.mp4, *.mov, *.avi
- *.psd, *.ai

**Temporary files**
- *.tmp, *.swp, *.bak
- ~$* (Office temp files)
- .DS_Store, Thumbs.db

### 2. Update .gitignore

- If it exists: read the current content, then **append** only non-duplicate new rules
- If it doesn't exist: create a new file with the same rules as .claudeignore

Note: Codex CLI does not have a dedicated ignore file — it uses .gitignore as
the primary context exclusion mechanism. Ensure .gitignore is comprehensive.

### Rule format

Add a category comment before each group:
```gitignore
# Archive and historical data
/archive/

# Sensitive information
.env
*.key
```

## Constraints

- **Do not overwrite** existing .gitignore rules
- Do not add build tool artifacts that the project doesn't use
- Each rule must have a category comment

## Output

Report:
- File paths for both files
- Rule count for each
- Whether existing .gitignore rules were preserved
```

---

## Agent C: Context Files Generator

```
You are a context summary generation expert.

## Input: Scan Context

{SCAN_CONTEXT}

## Task

### Preparation

1. Create the directory: `mkdir -p context`
2. Scan existing documentation sources:
   - README*, docs/, wiki/
   - Root-level *.md files
   - package.json description field
   - Code comments and docstrings

### Generate three files

**context/about-project.md** (max 1000 words)
- Project background and history
- Project goals and vision
- Stakeholders and audience
- Inferred from README, package.json, directory structure
- Combined with user goals from Scan Context

**context/standards.md** (max 1000 words)
- Output format standards (file types, naming rules)
- Quality requirements (accuracy, consistency, completeness)
- Code/documentation style conventions
- Inferred from linter configs, editor configs, style guides, code patterns

**context/domain-knowledge.md** (max 1000 words)
- Domain-specific terminology and definitions
- Business rules and constraints
- Key concepts and relationships
- Extracted from documentation, code comments, README

### When source material is insufficient

If there isn't enough material for meaningful content, generate a skeleton with TODO markers:

```markdown
# [File Title]

<!-- TODO: skeleton template — fill in based on actual project details -->

## [Section 1]
[To be added]

## [Section 2]
[To be added]
```

## Constraints

- Write in the language specified by PRIMARY_LANGUAGE in Scan Context
- Each file **max 1000 words**
- After writing, verify with: `wc -w context/*.md`
- Content must come from actual project materials — **do not fabricate** information
- When information is insufficient, use TODO markers rather than inventing content

## Output

Report:
- Three file paths
- Word count for each
- Which files contain TODO markers (need user follow-up)
```

---

## Agent D: Plugin/Skill Skeleton Generator (conditional)

**Only launch this agent if the user confirmed "need Plugin/Skill skeletons" in Phase 1.**

```
You are a Plugin and Skill skeleton generator for AI coding assistants.

## Input: Scan Context

{SCAN_CONTEXT}

## Task

Based on the project type and user goals, select 2-3 suitable skills and create
skeleton files for BOTH Claude Code and Codex CLI formats.

### Skill selection guide

| Project Type | Recommended Skills |
|-------------|-------------------|
| Code project | Code review, test generation, documentation generation |
| Data project | Report generation, data validation, trend analysis |
| Document project | Document review, format conversion, summary generation |
| Mixed project | Pick the most relevant from each category above |

### Create file structures for both platforms

**Claude Code format:**
```
.claude-plugin/
├── plugin.json
└── skills/
    ├── [skill-1].md
    ├── [skill-2].md
    └── [skill-3].md
```

**Codex CLI format (optional, if target platforms include codex-cli):**
```
.codex/skills/
├── [skill-1]/
│   └── SKILL.md
├── [skill-2]/
│   └── SKILL.md
└── [skill-3]/
    └── SKILL.md
```

### plugin.json format (Claude Code)

```json
{
  "name": "[project-name]-workflow",
  "description": "[one-line description based on user goals]",
  "version": "1.0.0"
}
```

### Skill file format (shared frontmatter)

Both platforms use SKILL.md with YAML frontmatter:

```markdown
---
name: [Skill Name]
description: [one-line description including trigger phrases]
---

## Steps

1. [Step 1]
2. [Step 2]
3. ...

## Quality Requirements

- [Requirement 1]
- [Requirement 2]
```

## Constraints

- Write in the language specified by PRIMARY_LANGUAGE in Scan Context
- Validate plugin.json is legal JSON (run: `python3 -m json.tool .claude-plugin/plugin.json`)
- Skill names use kebab-case (e.g., `monthly-report`)
- Each skill description must include trigger phrases the user might say
- Skill content must be project-specific — **do not write generic templates**

## Output

Report:
- Plugin/skill names
- Skill list with descriptions
- Which platforms were targeted (Claude Code / Codex CLI / both)
- JSON validation result
```
