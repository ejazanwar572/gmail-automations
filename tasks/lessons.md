# Lessons Learned

## Lesson 1: Scope of Constraints in User Workflows
* **Mistake**: Assumed that a constraint specified within a workflow (e.g. "Do NOT use any local AI models" in `/cashback-tracker`) was a global rule applying to all other independent questions or tasks in the session.
* **Correction**: Workflow constraints are local to that specific workflow. Do not generalize workflow-specific execution constraints (like model restrictions, formatting, or paths) to general chat queries unless the user explicitly makes them global.
* **Pattern**: Always distinguish between workflow-specific rules/instructions and global session instructions. If in doubt, ask for clarification.
