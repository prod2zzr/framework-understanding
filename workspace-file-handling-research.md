# How AI Coding Tools Handle Workspace/Codebase Files

Research compiled March 2026. Covers Claude Code, Cursor, Windsurf, Gemini CLI, and Gemini Code Assist.

---

## 1. Claude Code (CLI and VS Code Extension)

### Approach: On-Demand Agentic Search (No Indexing, No Embeddings)

Claude Code **does not scan, index, or vectorize** the workspace. It uses an "agentic search" approach where it discovers code at runtime using built-in tools:

- **Glob** -- file pattern matching (e.g., `**/*auth*`)
- **Grep** -- content search via ripgrep
- **Read** -- reads specific files on demand
- **Subagents** -- delegate broad exploration to a separate context window that reports back a summary

The search is **iterative and adaptive**: the model issues a search, examines results, then refines with a narrower search. This is fundamentally different from single-shot RAG retrieval.

### Why No Indexing?

Boris Cherny (Claude Code creator) stated on the Latent Space podcast (May 2025): *"We tried very early versions of Claude that actually used RAG... Eventually, we landed on just agentic search... One is it outperformed everything. By a lot."*

Key reasons:
- **Precision**: grep finds exact matches; embeddings introduce fuzzy positives
- **Freshness**: no stale index during active editing
- **Simplicity**: zero setup, nothing to build or maintain
- **Privacy**: no data leaves the machine for embedding computation

### VS Code Extension

The VS Code extension wraps the same CLI engine. It provides:
- Awareness of currently open files and selections
- @-mention files with specific line ranges
- Auto Memory (MEMORY.md) that persists patterns/preferences across sessions
- No additional embedding or preprocessing beyond what the CLI does

### Cost Efficiency

Claude Code achieves a 92% prompt prefix reuse rate via Anthropic's prompt caching. The system prompt, tool definitions, and CLAUDE.md contents form a shared prefix across turns, with cache read tokens costing only 0.1x base price.

### Does Claude Code Use RAG?

**No.** Claude Code does not use RAG or embedding-based search internally. However:
- **Claude Projects** (web UI) does use internal RAG when project knowledge exceeds the context window
- Third-party MCP plugins (e.g., `claude-context` by Zilliz, `rag-cli`) can add embedding-based search to Claude Code

---

## 2. Cursor

### Approach: Pre-Indexed Vector Embeddings (RAG)

Cursor **proactively indexes the entire codebase** in the background using a full RAG pipeline:

1. **Chunking**: Files are split into chunks using tree-sitter (AST-aware)
2. **Embedding**: Each chunk is embedded using Cursor's own embedding model
3. **Storage**: Embeddings stored in Turbopuffer (serverless vector database)
4. **Incremental updates**: Merkle tree detects changed files; only changed chunks are re-embedded (checks every 10 minutes)
5. **Team reuse**: Teammates' indexes can be reused (92% codebase similarity within orgs), cutting time-to-first-query from hours to seconds

### Query Flow

1. User query is converted to a vector using the same embedding model
2. Vector similarity search against Turbopuffer returns ranked candidate chunks
3. Only metadata (masked file paths + line ranges) is stored server-side -- actual source code stays local
4. Local client retrieves the actual code using the metadata
5. Retrieved chunks are injected as context alongside the query to the LLM

### Privacy Model

- File path obfuscation (path masking) applied client-side before transmission
- Original source code never stored on Cursor servers or in Turbopuffer
- Only embeddings and metadata persist in the cloud

### Hybrid Search

Cursor also uses traditional grep/ripgrep alongside semantic search. The agent decides which approach to use based on the query type.

---

## 3. Windsurf (formerly Codeium)

### Approach: AST-Based Embedding with Proprietary Retrieval Engine

Windsurf uses a **RAG-based context engine** with several proprietary components:

1. **AST-Based Chunking**: Client generates Abstract Syntax Tree representation, chunks code at function/method/class boundaries
2. **Embedding**: Chunks are sent independently to Windsurf's servers for embedding computation
3. **Local Vector Store**: Computed embeddings are stored locally with pointers (file path, line range)
4. **Incremental Updates**: Background process monitors code changes, recomputes affected AST chunks and embeddings

### Proprietary Technologies

- **Riptide** (formerly Cortex): Specialized LLM trained to evaluate code snippet relevance. Claims 200% improvement in retrieval recall over traditional embedding systems
- **Cascade**: Agentic system that tracks developer "intent" -- automatically pulls in relevant files without manual @-mentions
- **M-Query**: Proprietary retrieval technique for LLM-powered RAG

### Local vs. Remote Indexing

- **Local**: Entire local codebase indexed; retrieval happens as you code
- **Remote** (Teams/Enterprise): Indexes remote repositories, useful for multi-repo organizations

### Privacy

No single request contains entire codebases. Codebase parsing happens on-client; individual snippets are sent for embedding so the server never receives the full codebase at once.

---

## 4. Gemini CLI

### Approach: On-Demand File System Tools (No Indexing)

Gemini CLI **does not index the codebase**. Like Claude Code, it uses runtime file exploration:

- **ListDirectory** -- lists files/subdirectories
- **ReadFile** -- reads specific files
- **FindFiles** (glob) -- finds files matching glob patterns

It uses a ReAct (Reason and Act) loop to iteratively explore the codebase.

### Codebase Indexing: Not Yet Implemented

Full codebase indexing is an **open feature request** (GitHub issues #2065 and #5150) as of mid-2025. The community has proposed:
- Processing the codebase into vector representations
- Running a local vector DB on `gemini-cli start`
- Building a function/class index as a middle ground

### Community Workaround

A "function index" approach (extracting function/class signatures) provides a middle ground between recursive file listing and full codebase ingestion, leading to fewer searches and increased codebase awareness.

---

## 5. Gemini Code Assist (IDE Plugin)

### Approach: Pre-Indexed Embeddings (Similar to Cursor)

Unlike Gemini CLI, Gemini Code Assist **does index the codebase**:

- Indexing starts automatically when you open a project
- **Local codebase awareness**: Searches files in current folder and open tabs
- **Code customization** (Standard/Enterprise): Indexes remote repositories using embeddings
- Re-indexes every 24 hours to keep suggestions fresh
- Embeddings stored in single-tenant environment; code is not used for model training

### Agent Mode

Agent mode has "comprehensive understanding of your entire project" -- analyzes the whole codebase and requests files/folders as needed. Supports MCP for tool integration.

---

## 6. On-Demand Search vs. Pre-Indexed Embeddings: Tradeoffs

| Dimension | On-Demand (Claude Code, Gemini CLI) | Pre-Indexed (Cursor, Windsurf, Gemini Code Assist) |
|---|---|---|
| **Setup time** | Zero | Requires initial indexing |
| **Query precision** | Exact matches, no false positives | Semantic/conceptual matches possible |
| **Freshness** | Always current | Can drift; requires periodic re-indexing |
| **Privacy** | No data leaves machine | Embeddings may be computed/stored in cloud |
| **Semantic search** | Limited to keyword/pattern matching | Finds related code without keyword overlap |
| **Token cost** | Each search dumps results into context | One-time index; compact retrieval at query time |
| **Scale (large repos)** | Repeated scans can be expensive | One-time build, instant search thereafter |
| **Cross-repo discovery** | Difficult | Natural with remote indexing |
| **Transparency** | Can see exactly which searches were issued | Retrieval is opaque |
| **Adaptiveness** | Iterative refinement across multiple turns | Single-shot retrieval per query |

### When On-Demand Search Works Well

- Well-organized codebases with clear naming conventions
- Tasks requiring exact string matches (e.g., finding function callers)
- Privacy-sensitive environments
- Rapidly changing code (no stale index)

### When Pre-Indexed Embeddings Work Better

- Conceptual/semantic queries ("where do we handle authentication failures?")
- Large monorepos where manual navigation is impractical
- Cross-repository search
- Onboarding engineers exploring unfamiliar systems

---

## 7. Claude Code Context Management Strategies

### CLAUDE.md

- Read automatically at the start of every conversation
- Use `/init` to generate a starter file from your project
- Keep under ~300 lines; shorter is better
- Include: bash commands, code style rules, workflow conventions
- **Prefer pointers over copies** -- use `file:line` references, not code snippets
- Don't @-mention large doc files in CLAUDE.md (bloats context every run)

### Hierarchy of CLAUDE.md Files

- Repository root: project-wide instructions
- Subdirectories: scope-specific guidance
- `~/.claude/CLAUDE.md`: personal global defaults

### @-Mentions

- `@filename` provides Claude with immediate file access
- Supports specific line ranges from VS Code selections
- More token-efficient than pasting code into prompts

### Subagents

- Delegate research to a subagent with its own context window
- Main conversation stays clean for implementation
- Triggered by prompts like "use subagents to investigate X"

### Context Hygiene

- Use `/clear` aggressively to reset context
- Run `/context` to monitor token usage (200k window; ~20k baseline in monorepo)
- Customize compaction behavior in CLAUDE.md (e.g., "when compacting, preserve the list of modified files")
- Plan in one session, execute in a fresh session with clean context

### Hooks

- Deterministic actions that run at specific points in Claude's workflow
- Unlike CLAUDE.md instructions (advisory), hooks are guaranteed to execute
- Use for linting, formatting, testing -- not instructions to the model

### .claudeignore

- Prevents Claude from processing excessive context in large repos
- Single most effective fix for performance in large repositories

---

## 8. Summary Comparison Table

| Tool | Indexing? | Embedding/Vector? | Search Method | RAG? |
|---|---|---|---|---|
| **Claude Code (CLI)** | No | No | Grep, Glob, Read (agentic) | No |
| **Claude Code (VS Code)** | No | No | Same as CLI | No |
| **Cursor** | Yes (background) | Yes (Turbopuffer) | Semantic + grep hybrid | Yes |
| **Windsurf** | Yes (AST-based) | Yes (local vector store) | Riptide + M-Query | Yes |
| **Gemini CLI** | No | No | ListDirectory, ReadFile, FindFiles | No |
| **Gemini Code Assist (IDE)** | Yes (auto) | Yes (embeddings) | Semantic + local awareness | Yes |
| **OpenAI Codex CLI** | No | No | Text search, file matching | No |

---

## Sources

- [Claude Code Doesn't Index Your Codebase](https://vadim.blog/claude-code-no-indexing)
- [Claude Code FAQ](https://support.claude.com/en/articles/12386420-claude-code-faq)
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [How Cursor Actually Indexes Your Codebase (Towards Data Science)](https://towardsdatascience.com/how-cursor-actually-indexes-your-codebase/)
- [How Cursor Indexes Codebases Fast (Engineer's Codex)](https://read.engineerscodex.com/p/how-cursor-indexes-codebases-fast)
- [Cursor Secure Codebase Indexing](https://cursor.com/blog/secure-codebase-indexing)
- [Windsurf Context Awareness Overview](https://docs.windsurf.com/context-awareness/overview)
- [Windsurf Security](https://windsurf.com/security)
- [Gemini CLI GitHub](https://github.com/google-gemini/gemini-cli)
- [Gemini CLI Codebase Indexing Request (Issue #2065)](https://github.com/google-gemini/gemini-cli/issues/2065)
- [Gemini Code Assist Overview](https://developers.google.com/gemini-code-assist/docs/overview)
- [Gemini Code Assist Code Customization](https://developers.google.com/gemini-code-assist/docs/code-customization)
- [Claude Context MCP by Zilliz](https://github.com/zilliztech/claude-context)
- [Why Claude Code is Special for Not Doing RAG (Medium)](https://zerofilter.medium.com/why-claude-code-is-special-for-not-doing-rag-vector-search-agent-search-tool-calling-versus-41b9a6c0f4d9)
- [Why I'm Against Claude Code's Grep-Only Retrieval (Milvus Blog)](https://milvus.io/blog/why-im-against-claude-codes-grep-only-retrieval-it-just-burns-too-many-tokens.md)
- [Search and Indexing Strategies (Developer Toolkit)](https://developertoolkit.ai/en/shared-workflows/context-management/codebase-indexing/)
- [From RAG to Context (RAGFlow 2025 Review)](https://ragflow.io/blog/rag-review-2025-from-rag-to-context)
- [A Function Index to Improve Gemini CLI's Code Context](https://wietsevenema.eu/blog/2025/gemini-cli-function-indexing/)
- [Writing a Good CLAUDE.md (HumanLayer)](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
