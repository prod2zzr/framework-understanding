# Scan Context Template

Standard output format for Phase 1 scan results. The main agent fills this in and embeds
the complete context into every sub-agent prompt.

---

## Scan Context (shared with all sub-agents)

### User Goals
- Primary purpose: {USER_PURPOSE}
- Typical scenario: {USER_SCENARIO}
- Core pain point: {USER_PAIN_POINT}

### Project Type
{PROJECT_TYPE}
<!-- code / data / documentation / mixed -->

### Primary Language
{PRIMARY_LANGUAGE}
<!-- Chinese / English — all generated content must match this language -->

### Target Platforms
{TARGET_PLATFORMS}
<!-- claude-code / codex-cli / both — determines which output files to generate -->

### Directory Structure
```
{DIRECTORY_TREE}
```
<!-- output of: find . -type d -not -path './.git/*' | head -50, annotated with purpose -->

### File Type Distribution
```
{FILE_TYPE_DISTRIBUTION}
```
<!-- output of: find . -type f ... | sed | sort | uniq -c -->

### Large Files (>1MB)
{LARGE_FILES}
<!-- "None" if no large files -->

### Sensitive Files
{SENSITIVE_FILES}
<!-- grep password|secret|key|credential|token results; "None detected" if clean -->

### Existing Configuration
{EXISTING_CONFIG}
<!-- List existing: CLAUDE.md / AGENTS.md / .gitignore / .claudeignore / .mcp.json / .claude/ / .codex/ / .claude-plugin/ -->
<!-- Omit those that don't exist -->

### User Annotations
- Core work areas: {CORE_AREAS}
- Archive areas: {ARCHIVE_AREAS}
- Sensitive areas: {SENSITIVE_AREAS}
- Need Plugin/Skill skeletons: {NEED_PLUGIN}
- Target platforms: {TARGET_PLATFORMS}
<!-- All above come from the Phase 1 approval gate user response -->
