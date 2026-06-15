# Skill: Independent DAG-based Git Commits

This repeatable skill provides a structured methodology for organizing modified and untracked files into independent, logical, DAG-compliant commits, ensuring the build is green at every commit.

---

## Steps for DAG-based Commits

### Step 1: Analyze Changes & Dependencies
1. Check changed and untracked files using `git status` and `git diff`.
2. Group files into independent functional categories (e.g., bugfixes, core definitions, adapters, helpers, docs).
3. Determine compilation dependencies. For example, the contract definition must be committed before the client adapter that imports it.

### Step 2: Create a Feature Branch
Create a descriptive feature branch from the clean base branch:
```bash
git checkout -b feature/<branch-name>
```

### Step 3: Stage and Commit Sequentially (Build the DAG)
For each logical component in the dependency hierarchy:
1. Stage the files explicitly using `git add <file1> <file2>`. Do not use `git add .` or `git add -A` unless all changes are part of the target commit.
2. If a file contains changes for multiple commits, use selective staging (`git add -p <file>`) to stage only specific hunks.
3. Verify compilation and run tests to ensure the commit remains functional:
   ```bash
   python -m py_compile <changed_files>
   # Run tests (e.g., python main.py)
   ```
4. Commit with a Conventional Commits formatted message:
   ```bash
   git commit -m "<type>(<scope>): <short summary>"
   ```

### Step 4: Final Validation
Run `git log --oneline --graph` to verify the commits form a clean, linear, or structured graph, and confirm the final build is green.
