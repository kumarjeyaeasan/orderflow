# Pushing OrderFlow to GitHub

Run every command in the VS Code terminal (WSL), from the project folder:

```bash
cd ~/code/orderflow
```

- **Part A** is a one-time setup (already done for `github.com/kumarjeyaeasan/orderflow`).
- **Part B** is what you do after every step or phase.
- **Part C** covers errors.

---

## Part A — One-time setup

### A1. Tell git who you are
Commits are stamped with this name and email. If the email doesn't match your GitHub account, GitHub
won't link the commits to your profile.

```bash
git config --global user.name "Senthil"
git config --global user.email "YOUR-EMAIL"
```

For `YOUR-EMAIL`, use either:
- the email on your GitHub account, or
- GitHub's private no-reply address, found at https://github.com/settings/emails
  ("Keep my email addresses private"). It looks like `12345678+kumarjeyaeasan@users.noreply.github.com`.

Check:
```bash
git config user.name; git config user.email
```

> Commits made before this step keep the old author (`senth@LAPTOP-….localdomain`). That's harmless.
> Fixing them means rewriting history and force-pushing, which isn't worth it for a learning repo.

### A2. Make sure nothing secret or unfinished gets pushed
```bash
git status -sb                    # everything you want is committed; "nothing to commit" is ideal
git ls-files | grep -E '(^|/)\.env$' && echo "STOP: .env is tracked" || echo "ok: .env not tracked"
```
`.env` is listed in `.gitignore`. Only `.env.example`, which holds dev-only defaults, belongs in git.

If there are uncommitted changes you want to keep:
```bash
git add -A
git commit -m "describe the change"
```

### A3. Create an empty repository on GitHub (browser)
1. Open https://github.com/new
2. **Repository name:** `orderflow`. Choose **Private** or **Public**.
3. **Leave every "Initialize this repository" option unticked** (no README, .gitignore or licence).
   Otherwise the first push is rejected, because GitHub would already have a commit you don't have.
4. Click **Create repository**.

### A4. Create a personal access token
GitHub doesn't accept your account password for git over HTTPS; it needs a token.

1. Open https://github.com/settings/tokens?type=beta, then **Generate new token**.
2. **Expiration:** your choice (e.g. 90 days). You'll repeat A4 when it expires.
3. **Repository access:** **Only select repositories**, then `orderflow`.
4. **Permissions, Repository permissions, Contents:** **Read and write**.
5. **Generate token** and copy it (it starts with `github_pat_`). GitHub shows it only once.

### A5. Connect the local repo and push
```bash
git remote add origin https://github.com/kumarjeyaeasan/orderflow.git
git config --global credential.helper store      # optional: remember the token (see note)
git push -u origin main                           # -u: later, plain `git push` is enough
git push origin --tags                            # tags aren't pushed by default
```
When git asks:
- **Username:** your GitHub username (`kumarjeyaeasan`)
- **Password:** paste the **token**. Nothing appears as you paste; that's normal.

> **Note:** `credential.helper store` saves the token in plain text in `~/.git-credentials`. That's fine on a
> personal laptop. To avoid it, skip that line and paste the token on each push.

### A6. Check it worked
```bash
git remote -v                     # origin -> github.com/kumarjeyaeasan/orderflow.git
git status -sb                    # "## main...origin/main" with no [ahead N]
git ls-remote --tags origin       # lists refs/tags/phase-0-done
```
On GitHub, the commits appear on the main page and the tag appears under **Tags**.

---

## Part B — Every time after that

### After a step (new commits)
```bash
make test && make lint            # keep the build green before sharing it
git add -A
git commit -m "feat(phase-N): what changed"
git push
```

### After a phase (commit + tag)
```bash
git tag phase-N-done
git push
git push origin phase-N-done
```

### If you moved a tag that was already pushed
For example, `git tag -f phase-0-done` after a late fix. The remote still has the old tag, so replace it:
```bash
git push --force origin phase-0-done
```
Force-push **tags** only like this. Never `git push --force` on `main` unless you really mean to rewrite
shared history.

---

## Part C — Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `fatal: No configured push destination` | No remote yet | Do A5 (`git remote add origin …`) |
| `error: remote origin already exists` | A5 was run before | `git remote set-url origin https://github.com/kumarjeyaeasan/orderflow.git` |
| `Authentication failed` / `Invalid username or token` | You typed your password, or the token expired or lacks access | Make a new token (A4) with **Contents: Read and write** on `orderflow`. If you used `credential.helper store`, first remove the old line from `~/.git-credentials` |
| `! [rejected] main -> main (fetch first)` | GitHub has a commit you don't have (e.g. the repo was created with a README) | `git pull --rebase origin main`, then `git push` |
| `! [rejected] phase-0-done (already exists)` | The tag was moved locally after pushing | `git push --force origin phase-0-done` (Part B) |
| `Host key verification failed` | You used an `git@github.com:` (SSH) URL without SSH set up | Use the HTTPS URL from A5, or set up an SSH key: https://docs.github.com/en/authentication/connecting-to-github-with-ssh |
| Commits on GitHub don't show your avatar | The commit email isn't on your GitHub account | Do A1; this affects only new commits |
