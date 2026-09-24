# Phase 0 — How to test (quick guide)

The short, copy-paste version. For every test case in detail, see
[phase-0-test-plan.md](phase-0-test-plan.md).

**Where to run:** the VS Code terminal (`` Ctrl+` ``). VS Code is connected to WSL, so that terminal is
Ubuntu. Start in the project folder:

```bash
cd ~/code/orderflow
```

---

## 1. Automated checks (about 1 minute)

```bash
make test
```
**Pass:** the last line reads `65 passed`.

```bash
make lint
```
**Pass:** `All checks passed!` and `Success: no issues found`.

---

## 2. The full demo (about 2 minutes)

```bash
make clean && make up && make demo-0
```
**Pass:** four green ✔ lines, then `Phase 0 demo passed.`

What each step shows:

| Step | What happens | Expected |
|---|---|---|
| 1 | Alice orders a keyboard | `SHIPPED`; stock and wallet both go down |
| 2 | Zoe (wallet 0) orders a keyboard | `REJECTED`, "insufficient funds"; **stock unchanged** |
| 3 | **Break it:** 10 people buy the last lamp at once, naive stock check | `shipped: 10`: oversold |
| 4 | **Fix it:** the same race with the atomic stock update | `shipped: 1   rejected: 9` |

The demo is safe to re-run: it resets the lamp's stock itself.

Steps 1 and 2 of this guide are enough to prove Phase 0 works.

---

## 3. Try it yourself (optional)

The stack is still running from step 2. Paste these one at a time.

**See the products:**
```bash
curl -s localhost:8000/products | python3 -m json.tool
```

**Alice buys a keyboard.** Expected: `"status": "SHIPPED"`.
```bash
curl -s -X POST localhost:8000/orders -H 'content-type: application/json' \
  -d '{"customer_id":"20000000-0000-4000-8000-000000000001","lines":[{"product_id":"10000000-0000-4000-8000-000000000001","quantity":1}]}' \
  | python3 -m json.tool
```

**Zoe, who has no money, tries the same.** Expected: `"status": "REJECTED"`, `"insufficient funds"`.
```bash
curl -s -X POST localhost:8000/orders -H 'content-type: application/json' \
  -d '{"customer_id":"20000000-0000-4000-8000-000000000005","lines":[{"product_id":"10000000-0000-4000-8000-000000000001","quantity":1}]}' \
  | python3 -m json.tool
```

**Check the keyboard stock.** Alice's order took 1; Zoe's failed order took nothing.
```bash
curl -s localhost:8000/products/10000000-0000-4000-8000-000000000001 | python3 -m json.tool
```

**Clickable alternative:** open `http/orders.http`, `http/products.http` or `http/admin.http` in VS Code
and click the grey **Send Request** link above each request (needs the REST Client extension from the
recommended extensions). Each request's comment says what to expect.

---

## 4. When you're done

```bash
make down
```

---

## If something fails

| You see | Do this |
|---|---|
| `Cannot connect to the Docker daemon` | Start Docker Desktop, wait until it says "running", then retry |
| `port is already allocated` | Something else uses port 8000 or 5432. Run `make down` and retry |
| Demo step 4 crashes with `JSONDecodeError: Extra data` | Your copy of the demo script predates the fix below. Run `git pull` or check that `scripts/demo/phase-0.sh` writes one file per request (`curl … -o "$dir/{}.json"`) |
| Anything else | Copy the last ~20 lines of output into the Claude Code chat |

---

## Known issue (fixed 2026-09-24): demo step 4 crashed with `JSONDecodeError`

**What happened:** the oversell fix itself worked, but the demo **script** crashed while reading the results.

**Why:** the script sends 10 `curl` requests at once. They all wrote to one shared output, and each wrote its
response and then a newline in two separate writes. Sometimes another request's response landed between
the two, so two responses ended up on one line, and Python couldn't parse that line. Whether it happens
depends on timing, so it failed on some runs and machines and not others. It's the same kind of bug
Phase 0 is about: several processes sharing one resource without coordination.

**Fix:** in the `race()` function of `scripts/demo/phase-0.sh`, each request now writes its own file
(`curl … -o "$dir/{}.json"`) and Python reads the files afterwards. After the fix the demo passed 6 runs in
a row.

**Steps taken after the fix:**
```bash
make demo-0                                   # should end with "Phase 0 demo passed."
git add scripts/demo/phase-0.sh
git commit -m "fix(demo-0): stop parallel curl output from interleaving"
git tag -f phase-0-done                       # move the tag to the fixed commit (fine: not pushed)
```
