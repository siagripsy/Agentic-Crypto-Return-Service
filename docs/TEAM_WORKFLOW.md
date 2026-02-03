# Team Workflow Guide (GitHub + Trello)
Project: Agentic Crypto Return Service  
Branches: main (release), dev (integration)

This guide is written for teammates who are new to GitHub and team projects.

---

## 1) Big picture
We will use this simple flow:

1. Pick a task in Trello.
2. Create a new feature branch from `dev`.
3. Do your work on your laptop.
4. Commit changes (save a snapshot).
5. Push your branch to GitHub.
6. Open a Pull Request (PR) into `dev`.
7. Reviewer checks it, then merges into `dev`.
8. When we reach a milestone or weekly checkpoint, we merge `dev` into `main`.

Key idea:
- `dev` is where we combine work from everyone.
- `main` is the clean version we present to the professor or use for a release.

---

## 2) Trello rules
We use these lists :
- Week 5, Week 6, etc (tasks to do)
- Doing (someone is actively working)
- PR Ready (Needs Review) 
- Changes Requested (Fix Needed) (review asked for changes)
- Done (merged)

When you start a task:
- Move the card from Week list to Doing.
- Assign yourself.
- Add the GitHub branch name in the card title or description.

When you open a PR:
- Move the card to PR Ready (Needs Review).
- Paste the PR link into the Trello card.

When PR is merged:
- Move the card to Done.

---

## 3) One time setup on your laptop (first day only)

### 3.1 Install tools
- Install Git for Windows (includes Git Bash).
- Install VS Code (optional but helpful).

### 3.2 Clone the repository
```bash
cd /c/Users/<YOUR_WINDOWS_USERNAME>/Desktop
git clone https://github.com/<ORG_OR_OWNER>/<REPO_NAME>.git
cd <REPO_NAME>
```

### 3.3 Configure your name and email
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

---

## 4) Daily workflow (every task)

### Step A: Sync with dev
```bash
git checkout dev
git pull
```

### Step B: Create feature branch
```bash
git checkout -b feature/<short-task-name>
```

### Step C: Work and check status
```bash
git status
```

### Step D: Commit
```bash
git add .
git commit -m "feat: short description"
```

### Step E: Push
```bash
git push -u origin feature/<short-task-name>
```

### Step F: Open PR into dev
- Base: dev
- Compare: your feature branch
- Link Trello card

---

## 5) Keep branch updated
```bash
git checkout dev
git pull
git checkout feature/<short-task-name>
git merge dev
```

---

## 6) Merge conflicts
1. Open conflicted files.
2. Resolve markers.
3. Save.
4.
```bash
git add .
git commit -m "fix: resolve conflict"
git push
```

---

## 7) Rules
- PRs go to dev.
- Only lead merges dev to main.
- Main updated at milestones.

---

## 8) Cleanup after merge
```bash
git checkout dev
git pull
git branch -d feature/<short-task-name>
```

---

## 9) Cheat sheet
```bash
git checkout dev
git pull
git checkout -b feature/<name>
git status
git add .
git commit -m "feat: message"
git push -u origin feature/<name>
```

---

## 10) Definition of Done
- PR merged into dev
- Trello updated
- Docs updated if needed
