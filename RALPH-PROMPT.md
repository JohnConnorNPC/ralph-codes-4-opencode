Study RALPH-DESIGN.md (requirements).
Study RALPH-PLAN.md (your checklist).
Study RALPH-PROGRESS.md (what's been done).
Study RALPH-SPECS.md if it exists (lookup table - find existing patterns, don't invent).

Pick the SINGLE most important unchecked item from RALPH-PLAN.md.
Implement ONLY that ONE thing.

After implementation of ONE THING:
1. Run tests. Fix any failures.
2. Update RALPH-PLAN.md: mark item [x] done, cite files changed.
3. Append to RALPH-PROGRESS.md: what you did, files changed, test result.
4. Create RALPH-CHECKPOINT.md with a one-line summary.
5. VERIFY: Read all 3 files back to confirm your changes were saved.
6. STOP IMMEDIATELY after verification.

## CHECKPOINT FILE FORMATS (use exactly):

### RALPH-PLAN.md - mark done like this:
- [x] <task> — files: `file1.py`, `file2.py`

### RALPH-PROGRESS.md - append this format:
---
## Iteration N - <title>
**Task**: <description>
**Files Changed**: `file1.py`, `file2.py`
**Test Result**: <pass/fail>

### RALPH-CHECKPOINT.md - single line:
Completed: <brief summary>

## WARNING - FAILURE MODE:
If you do NOT write all 3 checkpoint files before stopping:
- Loop restarts with fresh context
- Your work is invisible to next iteration
- Same work repeats forever
ALWAYS update RALPH-PLAN.md + RALPH-PROGRESS.md + RALPH-CHECKPOINT.md before stopping.

CRITICAL STOP RULE:
- You must STOP after completing ONE item.
- When Stopping you must update plan/progress/checkpoint
- Do NOT continue to the next item.
- The loop will restart you with fresh context.
- This prevents context rot.

TERMINAL STATES:
- RALPH-CHECKPOINT.md = one item done, STOP (loop continues)
- RALPH-COMPLETE.md = ALL requirements met AND all items done AND tests pass, STOP (loop exits success)
- RALPH-BLOCKED.md = stuck (missing info, ambiguous, external dep), STOP (loop exits blocked)

Never delete RALPH-PROGRESS.md history.
Never declare done without running tests.
Use search tool to find existing code before inventing.

Start now.
