# LabCim Manager — repository state audit (M0.1)

Audit date: 2026-08-11 (`America/Fortaleza`)

Scope: read-only Git provenance and canonical-state analysis before M1. No branch was checked out, merged, rebased, deleted, or pulled. No application code, database, deployment target, or infrastructure was changed.

## 1. Decision

**Canonical current version: YES — `main` at `1ffe702ff3753c95ac12c78f8b20547b04b3f84d`.**

The checked-out `main`, local `main`, fetched `origin/main`, and `origin/HEAD` all resolve to the same commit. The remote declares `main` as its HEAD branch. The repository contains the prior feature sprints in `main` ancestry, including PostgreSQL, R2/object storage, bookings, equipment, maintenance, supply lots, reports, authentication hardening, attachments, and QR/documentation work.

This conclusion is about **source-of-truth provenance**, not deployment readiness:

- `origin/main@1ffe702` is the most likely current product/code baseline and the correct starting point for M1.
- It is **not yet an approved production deployment baseline**. The M0 `NO-GO` blockers remain.
- The `v1.0.0` tag is a historical release marker at `1551381`, 44 commits behind `main`; it is not the latest product state.

Three branch tips contain one commit each that is absent from `main`. They are narrow UI changes, not missing domain sprints. Two are superseded mobile-navigation alternatives. The third is an unresolved multiselect-contrast tweak that should be accepted or rejected explicitly before M1, without merging its old branch wholesale.

## 2. Important correction about “initial commit”

`1ffe702` is **not** the repository's root or initial commit. It is the commit at which M0 began and the current tip of `main`.

The M0 report itself labels it `Commit inicial do M0`, which is accurate when read as “the initial M0 snapshot.” If it was summarized elsewhere as “the repository's initial commit,” that summary is incorrect.

The root commit reachable from all refs is:

| Role | Commit | Date | Subject |
|---|---|---|---|
| Repository root/imported baseline | `54f81cd` | 2026-06-19 | `Beta LabCim Manager v8.6` |
| M0 snapshot and current `main` | `1ffe702` | 2026-08-03 | Merge PR #55, sprint 12y |

Because the first Git commit is already a v8.6 application snapshot, Git cannot reconstruct development before v8.6. It can reconstruct the subsequent sprint history.

## 3. Commands and remote refresh

The audit inspected:

```text
git status
git remote -v
git branch -vv
git branch -a
git log --oneline --decorate --graph --all
git for-each-ref ...
git rev-list --left-right --count main...<ref>
git merge-base --is-ancestor <ref> main
git log --all --not main
git cherry main <unmerged-ref>
git fsck --full --no-reflogs --unreachable
```

`git fetch --all --prune --verbose` was run safely. The first attempt reached GitHub but the Windows Schannel provider returned `SEC_E_NO_CREDENTIALS`. A command-local retry used Git's OpenSSL backend with interactive credentials disabled and succeeded. It reported every advertised branch **up to date**; no remote ref was added, advanced, rewound, or pruned.

No `pull`, merge, rebase, checkout, reset, push, or ref deletion was performed.

## 4. Current checked-out and origin state

| Item | State after fetch |
|---|---|
| Repository | `labcim-manager-beta` |
| Remote | `origin` → `https://github.com/edgarmoraesufrn/labcim-manager-beta.git` |
| Remote default branch | `main` |
| Checked-out branch | `main` |
| `HEAD` | `1ffe702ff3753c95ac12c78f8b20547b04b3f84d` |
| Local `main` | `1ffe702ff3753c95ac12c78f8b20547b04b3f84d` |
| `origin/main` | `1ffe702ff3753c95ac12c78f8b20547b04b3f84d` |
| `origin/HEAD` | `origin/main` |
| Local/remote divergence | `+0 / -0` |
| Local branches | 67 |
| Remote branches under `origin` | 55, excluding symbolic `origin/HEAD` |
| Tags | One: `v1.0.0` at `1551381` |
| `v1.0.0` vs `main` | 0 tag-only commits; 44 `main`-only commits |
| Describe | `v1.0.0-44-g1ffe702` |

### Uncommitted work

The worktree is intentionally not clean because it contains the uncommitted M0 audit deliverables:

- modified: `README.md`;
- modified: `docs/production_runbook.md`;
- untracked: `docs/DATABASE_MIGRATION_PLAN.md`;
- untracked: `docs/FILE_STORAGE_MIGRATION_PLAN.md`;
- untracked: `docs/PRODUCTION_ENV_TEMPLATE.md`;
- untracked: `docs/PRODUCTION_READINESS.md`;
- untracked: `docs/UFRN_DEPLOYMENT_PLAN.md`;
- untracked: `scripts/production_preflight.py`;
- untracked by this audit: `docs/REPOSITORY_STATE_AUDIT.md`.

There are no staged changes. Before creating this report, `git diff --name-only` listed only `README.md` and `docs/production_runbook.md`; an application-path-specific diff was empty. Therefore no uncommitted application code was mixed into the audited `1ffe702` product snapshot.

These M0 files must be preserved and reviewed. They should be committed separately from future M1 application changes so that the M1 baseline is reproducible.

## 5. Branch graph summary

The first-parent history is a deliberate sequence of merged pull requests:

```text
54f81cd  imported v8.6 baseline
  │
  ├─ OTP hotfixes
  ├─ PR #1  PostgreSQL persistence
  ├─ PR #2  R2 file/object storage
  ├─ PRs #3–#30  attachments, bookings, equipment, maintenance,
  │              projects, supply lots, reports, governance,
  │              authentication, production polish and audit work
  ├─ 1551381  tag v1.0.0 (PR #31)
  ├─ PRs #32–#36  branding/navigation/performance/mobile work
  │    ├─ 2ce7100  sprint-12g alternative, not merged
  │    └─ 5a18336  sprint-12i alternative, not merged
  ├─ PR #38 and PRs #40–#55  chosen mobile/PWA/UI line
  └─ 1ffe702  main = origin/main = origin/HEAD

0f6efd9  merged spare-part form simplification (PR #7)
  └─ da58c82  later contrast tweak, not merged
```

PR numbers #37 and #39 do not appear in `main`'s merge history. The branch topology shows that the two corresponding-era mobile alternatives were not selected; later merged branches implement the chosen navigation line.

### Why `main` is canonical even though other commits exist

Canonicality is supported by combined evidence, rather than commit date alone:

1. `origin` declares `main` as its default branch.
2. A fresh fetch confirms local `main` and `origin/main` are identical.
3. The first-parent history is a continuous series of accepted pull-request merges through PR #55.
4. Every major product-domain sprint tip is an ancestor of `main`.
5. The only non-ancestor tips are three isolated UI commits; none contains PostgreSQL, storage, reservation, equipment, maintenance, inventory, reporting, authentication, attachment, or QR/POP domain work absent from `main`.
6. Later merged sprint-12 branches supersede the two non-merged mobile-navigation experiments.

## 6. Exhaustive branch classification

For the tables below, “main-only” and “branch-only” are the two values from `git rev-list --left-right --count main...<branch>`. An ancestor branch has zero branch-only commits. Each remote-tracked local branch exactly matches its same-named `origin/*` ref after fetch.

### Foundational through sprint 11, plus hotfixes

| Branch (`local` = `origin/*`) | Tip | Main-only | Branch-only | Classification / purpose |
|---|---:|---:|---:|---|
| `main` | `1ffe702` | 0 | 0 | Canonical current branch |
| `hotfix-attachment-download-ui` | `61ad0fc` | 100 | 0 | Completed/merged attachment download UI |
| `hotfix-spare-part-form-ux` | `da58c82` | 93 | 1 | **Unmerged tail:** multiselect chip contrast; base form fix was merged |
| `hotfix-supply-lot-migration-order` | `ecc3e61` | 83 | 0 | Completed/merged migration-order fix |
| `sprint-0-postgres-persistence` | `0b3330f` | 105 | 0 | Completed/merged PostgreSQL backend |
| `sprint-0-5-file-storage-r2` | `d0f4e12` | 103 | 0 | Completed/merged R2 backend |
| `sprint-1-bookings-ux` | `657fe84` | 97 | 0 | Completed/merged bookings UX |
| `sprint-2-equipment-spare-parts` | `0948362` | 95 | 0 | Completed/merged equipment–spare-part links |
| `sprint-3-maintenance-workflow` | `ca1d105` | 91 | 0 | Completed/merged maintenance history |
| `sprint-3-5-performance-diagnostics` | `1c0f8b5` | 89 | 0 | Completed/merged database performance work |
| `sprint-4-projects-services` | `9ac0b86` | 87 | 0 | Completed/merged project services tracking |
| `sprint-5-supplies-inventory` | `c968d26` | 85 | 0 | Completed/merged supply lot tracking |
| `sprint-5b-supply-reports-alerts` | `b4f3e7d` | 81 | 0 | Completed/merged supply reports and alerts |
| `sprint-5c-supply-reports-polish` | `7fad78f` | 79 | 0 | Completed/merged report UI polish |
| `sprint-6b-operational-hardening` | `833fc2c` | 77 | 0 | Completed/merged import and stock hardening |
| `sprint-6c-performance-optimizations` | `ab701dc` | 75 | 0 | Completed/merged report and QR optimization |
| `sprint-6d-reporting-optimization` | `d6b6b4d` | 73 | 0 | Completed/merged on-demand Excel generation |
| `sprint-6e-professional-excel-report` | `c64b2c3` | 71 | 0 | Completed/merged branded Excel reports |
| `sprint-7b-reservation-hardening` | `99e8d21` | 69 | 0 | Completed/merged reservation hardening |
| `sprint-7d-booking-status-history` | `55592c6` | 67 | 0 | Completed/merged booking audit trail |
| `sprint-7f-equipment-governance-hardening` | `2467e08` | 65 | 0 | Completed/merged equipment governance |
| `sprint-8b-equipment-documents-r2` | `5bee765` | 63 | 0 | Completed/merged equipment attachments |
| `sprint-8d-equipment-documentation-qr` | `cbde939` | 61 | 0 | Completed/merged equipment documentation QR |
| `sprint-9b-maintenance-permissions-qr-polish` | `c354d54` | 59 | 0 | Completed/merged maintenance permissions/QR |
| `sprint-9c-maintenance-member-ux-polish` | `6eabddf` | 57 | 0 | Completed/merged member maintenance UX |
| `sprint-10b-auth-role-hardening` | `f36c674` | 55 | 0 | Completed/merged authentication/role hardening |
| `sprint-10d-sensitive-access-hardening` | `fc748c1` | 53 | 0 | Completed/merged reports/inventory access hardening |
| `sprint-10e-inventory-member-ux-audit` | `8e665aa` | 51 | 0 | Completed/merged inventory member UX/audit |
| `sprint-11b-beta-production-polish-runbook` | `f64d334` | 49 | 0 | Completed/merged production polish/runbook |
| `sprint-11c-v1-audit-demo-package` | `f5f86f7` | 47 | 0 | Completed/merged v1 audit/demo package |
| `sprint-11d-repository-hygiene-v1` | `bf6eb6a` | 45 | 0 | Completed/merged v1 repository hygiene |

### Sprint 12 remote-tracked branches

| Branch (`local` = `origin/*`) | Tip | Main-only | Branch-only | Classification / purpose |
|---|---:|---:|---:|---|
| `sprint-12b-public-branding-cleanup` | `4a9cc9f` | 43 | 0 | Completed/merged branding cleanup |
| `sprint-12c-professional-sidebar-navigation` | `260d8e9` | 43 | 0 | Completed/merged sidebar redesign |
| `sprint-12d-optimize-heavy-page-sections` | `f3adb46` | 39 | 0 | Completed/merged rendering optimization |
| `sprint-12e-mobile-navigation-polish` | `44f3f44` | 37 | 0 | Completed/merged quick mobile navigation |
| `sprint-12f-mobile-sidebar-behavior-polish` | `15670d4` | 35 | 0 | Completed/merged mobile sidebar behavior |
| `sprint-12g-hide-sidebar-on-mobile` | `2ce7100` | 34 | 1 | **Not merged; likely abandoned/superseded alternative** |
| `sprint-12h-mobile-sidebar-controlled-polish` | `d75f9a5` | 33 | 0 | Completed/merged controlled mobile navigation |
| `sprint-12i-robust-mobile-menu-navigation` | `5a18336` | 34 | 1 | **Not merged; likely abandoned/superseded alternative** |
| `sprint-12j-replace-autocollapse-with-mobile-menu` | `8c0baf1` | 31 | 0 | Completed/merged chosen robust menu line |
| `sprint-12k-single-mobile-navigation` | `a2291a7` | 29 | 0 | Completed/merged single mobile navigation |
| `sprint-12l-front-polish` | `27050c0` | 27 | 0 | Completed/merged frontend polish |
| `sprint-12m-fix-desktop-navigation` | `64a6495` | 25 | 0 | Completed/merged desktop navigation fix |
| `sprint-12n-robust-scroll-top` | `9a54bd5` | 23 | 0 | Completed/merged scroll behavior |
| `sprint-12o-hide-cloud-attribution` | `2b19454` | 21 | 0 | Completed/merged cloud attribution UI change |
| `sprint-12p-hide-floating-cloud-badge` | `626ee3a` | 19 | 0 | Completed/merged badge UI change |
| `sprint-12q-remove-aggressive-badge-js` | `27947e8` | 17 | 0 | Completed/merged cleanup of badge script |
| `sprint-12r-tablet-navigation-breakpoint` | `f8fd45d` | 15 | 0 | Completed/merged tablet navigation |
| `sprint-12s-app-icon` | `3d713e9` | 13 | 0 | Completed/merged app icon |
| `sprint-12t-pwa-launcher-icon` | `917c0c0` | 11 | 0 | Completed/merged PWA metadata |
| `sprint-12u-remove-mobile-menu-tooltip` | `90677a1` | 9 | 0 | Completed/merged mobile tooltip cleanup |
| `sprint-12v-mobile-install-guidance` | `cce8a3f` | 7 | 0 | Completed/merged install guidance |
| `sprint-12w-restore-desktop-sidebar-toggle` | `a501b3d` | 5 | 0 | Completed/merged desktop toggle restoration |
| `sprint-12x-open-desktop-sidebar-by-default` | `f84aeb5` | 3 | 0 | Completed/merged desktop default state |
| `sprint-12y-restore-sidebar-toggle-toolbar` | `aecfb43` | 1 | 0 | Completed/merged toolbar shell; last feature tip |

### Local-only diagnostic pointers

These 12 local branches have no remote counterpart. All point to commits already in `main`; they contain no unique work and are best understood as historical diagnostic checkpoints.

| Local branch | Tip | Main-only | Branch-only |
|---|---:|---:|---:|
| `sprint-6a-technical-audit` | `4f257a6` | 78 | 0 |
| `sprint-6c-performance-diagnostics` | `6dd1e59` | 76 | 0 |
| `sprint-6d-reporting-diagnostics` | `e5935a8` | 74 | 0 |
| `sprint-7a-reservations-equipment-diagnostics` | `1965946` | 70 | 0 |
| `sprint-7c-booking-status-history-diagnostics` | `e2413e3` | 68 | 0 |
| `sprint-7e-equipment-governance-diagnostics` | `2505c8d` | 66 | 0 |
| `sprint-8a-equipment-documents-r2-diagnostics` | `7847667` | 64 | 0 |
| `sprint-8c-equipment-documentation-qr-diagnostics` | `5bee765` | 63 | 0 |
| `sprint-9a-operational-stability-diagnostics` | `0956d43` | 60 | 0 |
| `sprint-10a-auth-permissions-diagnostics` | `469f9f7` | 56 | 0 |
| `sprint-10c-permissions-exposure-diagnostics` | `afe74f0` | 54 | 0 |
| `sprint-11a-production-readiness-diagnostics` | `7ee69d4` | 50 | 0 |

No branch deletion is needed to begin M1. Branch cleanup can be a later, separately approved repository-hygiene operation.

## 7. Work present outside `main`

`git log --all --not main` returns exactly three named branch commits:

### 7.1 `da58c82` — multiselect chip contrast

- Branch: `hotfix-spare-part-form-ux` locally and on origin.
- Divergence: 93 `main`-only / 1 branch-only.
- Parent: `0f6efd9`, the spare-part form simplification already merged by PR #7.
- Change: 12 added CSS lines in `app.py` that make BaseWeb multiselect tags LabCim blue with white text/icons.
- Patch identity: `git cherry main hotfix-spare-part-form-ux` reports `+`; the exact patch is not present in `main`.
- Current-state comparison: current `main` retains generic multiselect styling but not the branch's tag-specific blue/white selectors.
- M0.2 disposition: **ACCEPT**. This is not a missing equipment or spare-parts feature sprint; it is an isolated visual readability/accessibility correction. The patch was applied separately as `bd57350` after classification and validation. The old branch was not merged.

### 7.2 `2ce7100` — hide sidebar on mobile

- Branch: `sprint-12g-hide-sidebar-on-mobile` locally and on origin.
- Divergence: 34 `main`-only / 1 branch-only.
- Parent/merge base: `6494300` (merged sprint 12f).
- Change: 29-line `app.py` patch hiding sidebar/collapsed control at 768 px and adding a logout column to quick navigation.
- Patch identity: unique relative to `main`.
- Assessment: **likely abandoned/superseded alternative**. `main` instead merged sprint 12h and then 12j–12y, including a chosen responsive menu, single mobile navigation, a 1100 px breakpoint, desktop sidebar behavior, PWA metadata, and install guidance.

### 7.3 `5a18336` — robust mobile menu experiment

- Branch: `sprint-12i-robust-mobile-menu-navigation` locally and on origin.
- Divergence: 34 `main`-only / 1 branch-only.
- Parent/merge base: `6494300` (merged sprint 12f).
- Change: replaces the earlier quick-navigation selectbox with a button-based expander menu.
- Patch identity: unique relative to `main`.
- Assessment: **likely abandoned/superseded alternative**. The later merged `8c0baf1` implements the chosen robust mobile menu line, and later merged commits refine it. Current line attribution confirms the live mobile navigation originates in merged commits `8c0baf1`, `a2291a7`, `27050c0`, `64a6495`, and `cce8a3f`, not in `5a18336`.

### 7.4 Dangling local objects

`git fsck --full --no-reflogs --unreachable` found six unreachable commits. Their subjects and two-parent shape identify them as old Git stash working/index snapshots, not deleted sprint branches:

| Dangling pair | Meaning | Committed equivalent | Tree comparison |
|---|---|---|---|
| `754cfc7` / `6ecd761` | Attachment-download worktree/index stash | `8d043f4` / base `d0f4e12` | Exact same trees |
| `d849177` / `9171b5a` | Spare-part UX worktree/index stash | `0f6efd9` / base `0948362` | Exact same trees |
| `a923c25` / `f32ec96` | Booking UX worktree/index stash | `657fe84` / base `61ad0fc` | Exact same trees |

There is no current `git stash` ref. The worktree trees in all three dangling pairs exactly match reachable commits already in `main`, so they do not represent lost functionality or an alternative canonical baseline.

## 8. Major feature provenance

The root v8.6 snapshot already contains equipment, reservations, maintenance, supplies, reports, authentication/login, POP seeding, and QR generation. Later commits add or harden the features below. Every listed commit is an ancestor of `main`.

| Requested area | Principal reachable history | Present in `main` |
|---|---|---|
| PostgreSQL persistence | `0b3330f` — PostgreSQL persistence backend; merged by PR #1 | Yes |
| File/object storage | `d0f4e12` — R2 backend; merged by PR #2 | Yes |
| Equipment | v8.6 root; `0948362` spare-parts links; `2467e08` governance; `5bee765` documents | Yes |
| Reservations/bookings | v8.6 root; `657fe84` UX; `99e8d21` hardening; `55592c6` status history | Yes |
| Maintenance | v8.6 root; `ca1d105` workflow history; `c354d54` permissions/QR; `6eabddf` member UX | Yes |
| Inventory/supplies | v8.6 root; `833fc2c` stock movement/import hardening; `8e665aa` member UX/audit | Yes |
| Supply lot tracking | `c968d26` lot tracking; `ecc3e61` migration order fix | Yes |
| Reports | v8.6 root; `b4f3e7d` supply reports/alerts; `7fad78f` polish; `ab701dc` performance; `d6b6b4d` on-demand generation; `c64b2c3` branded Excel | Yes |
| Authentication | v8.6 root; `4a2edc9`/`ae4967d` OTP hotfixes; `f36c674` roles; `fc748c1` sensitive access | Yes |
| Attachments | `8d043f4` attachment download UI; `61ad0fc` supply document UI; `5bee765` equipment documents | Yes |
| QR/POP support | v8.6 root includes `qrcode`, `seed_default_pops`, equipment/supply QR pages; `ab701dc` QR optimization; `cbde939` equipment documentation QR | Yes |

No named branch outside `main` contains missing work in any of those major areas. The only non-main changes are the three UI commits described in section 7.

## 9. Is `main` suitable as the production baseline?

Two meanings must be separated:

| Question | Answer |
|---|---|
| Is `main@1ffe702` the canonical current source state and correct M1 base? | **Yes** |
| Is `main@1ffe702` ready to deploy to UFRN production now? | **No** |

The recommended canonical baseline is:

```text
origin/main
1ffe702ff3753c95ac12c78f8b20547b04b3f84d
Merge pull request #55 from edgarmoraesufrn/sprint-12y-restore-sidebar-toggle-toolbar
```

The recommendation is not based solely on it being chronologically newest. It is based on remote default-branch intent, fetched ref equality, accepted merge ancestry, feature containment, and analysis of all non-main tips.

## 10. Effect on the M0 audit

**M0 remains substantively valid.** It audited the exact recommended canonical commit, `1ffe702`, and there are no uncommitted application-code changes layered over that commit.

As a consistency check during M0.1, `scripts/production_preflight.py` was rerun with the bundled Python runtime and bytecode writes disabled. It again exited `2` with **36 blockers, 3 warnings, and 5 passes**, exactly matching the M0 Section 8 summary. The missing production environment and dependency findings are expected in this audit workspace; the important result is that the code/release blockers remain reproducible on the canonical snapshot.

### Sections that remain valid without repetition

- Section 1, “Snapshot auditado”: branch and hash are correct. Add only the clarification that `Commit inicial do M0` means the start of the audit, not the repository root, plus the successful post-fetch verification.
- Sections 2–7: architecture, area status, blockers, important findings, optional findings, and `/manager/` test matrix were derived from the same canonical application tree.
- Section 8: the validation results continue to describe that tree.
- Section 9: the M0 `NO-GO` and recommendation to harden before production remain unchanged.

### Findings not invalidated by non-main work

The three unmerged UI commits do not provide versioned database migrations, a migration rehearsal, institutional filesystem support, `/manager/` end-to-end validation, authentication abuse controls, upload hardening, a reproducible runtime, or tested backup/restore. They therefore do not remove or materially alter M0-B01 through M0-B08.

### When repetition would become necessary

No M0 section needs to be repeated solely because of this provenance check. If any application patch is integrated before M1 begins:

1. repeat M0 Section 8 validation on the new hash;
2. update Section 1 to the new immutable hash;
3. for mobile-navigation changes, repeat the Section 7 `/manager/` desktop/mobile matrix and relevant M0-B04 checks;
4. for the contrast tweak, perform targeted multiselect accessibility/visual regression checks;
5. re-run the production preflight and `git diff --check`.

## 11. Safe future integration and repository hygiene

No historical branch should be merged into `main` merely because it has a unique commit.

Recommended strategy:

1. Freeze and record `origin/main@1ffe702` as the M1 starting candidate after human approval.
2. Review `da58c82` as a standalone product/accessibility decision. If accepted, create a fresh branch from the then-current `origin/main`, port only the intended CSS, test it against current Streamlit/BaseWeb markup, and use a normal reviewed PR.
3. Mark `sprint-12g` and `sprint-12i` as superseded in repository/PR metadata after confirming with the owner. Do not merge or cherry-pick them into the chosen 12j–12y navigation line.
4. Review and commit the M0/M0.1 documentation and preflight work separately from application changes. Begin M1 only from a clean, named, reviewable state.
5. If a baseline tag is desired, create it only after approval and after deciding whether the M0 documentation belongs in that baseline. Do not move `v1.0.0`.
6. Keep old refs until branch disposition is documented. Branch deletion is unnecessary for M1 and was not performed here.
7. For any future integration, compare ancestry and patch content, use a fresh branch from canonical `main`, run targeted and full preflight validation, and merge only through the normal review process.

## 12. Required action before M1

Before M1 starts:

- formally approve `origin/main@1ffe702` as the canonical source baseline;
- explicitly accept or reject the small `da58c82` contrast patch;
- document `sprint-12g` and `sprint-12i` as superseded, unless an owner provides contrary intent;
- preserve and review the current M0/M0.1 uncommitted documentation, then put it in a separate clean commit/PR;
- record the final starting hash and re-run the M0 preflight on that exact clean state.

Do not deploy from `main` until the existing M0 blockers are resolved and validated in staging. This audit does not authorize M1 implementation or deployment.

## 13. M0.2 canonical baseline freeze

M0.2 completed the repository freeze without starting M1 implementation.

### Canonical and frozen hashes

| Item | Hash / state |
|---|---|
| Canonical application snapshot (audited original product state) | `1ffe702ff3753c95ac12c78f8b20547b04b3f84d` |
| Accepted isolated contrast commit | `bd57350931f8a4ebcde930dc482a7554f271a1ef` (`Improve multiselect chip contrast`) |
| M0/M0.1 audit artifact commit | `164a3605827291062955c6e7e34462fae22f9b5f` |
| M1 branch creation point | `164a3605827291062955c6e7e34462fae22f9b5f` |
| M1 branch | `m1-ufrn-production-hardening` |
| Exact M1 branch creation parent | `164a3605827291062955c6e7e34462fae22f9b5f` |
| Fetched `origin/main` | `1ffe702ff3753c95ac12c78f8b20547b04b3f84d` |
| Push status | Required to publish the two approved local commits; not performed |

The repository-state documentation commit that records this table is documentation-only and occurs on the new M1 branch after its creation. It does not change the frozen application baseline or count as M1 implementation.

### Terminology normalized in M0.3

- **Canonical application snapshot** means the audited original product state before M0 documentation and hardening work: `1ffe702ff3753c95ac12c78f8b20547b04b3f84d`.
- **M1 implementation baseline** means the final clean tip of `m1-ufrn-production-hardening` after all approved M0 bookkeeping commits and immediately before the first functional M1 change. It includes the accepted visual fix and approved M0/M0.1/M0.2 documentation ancestry.

The exact M1 implementation-baseline hash is the commit containing this M0.3 terminology normalization. A Git commit cannot embed its own final object ID without changing that ID; therefore the immutable hash is recorded by the branch ref, the Git log, and the M0.3 final provenance report after this documentation-only commit is created.

### `da58c82` disposition

Decision: **ACCEPT**.

- Files changed: only `app.py`.
- Size: 12 inserted CSS lines; no deletions.
- Behavior: selected Streamlit/BaseWeb multiselect chips use `LAB_BLUE` (`#0033A0`) for background/border and white for label, icon, and remove-button foreground.
- Scope: purely visual; no Python control flow, data, authentication, persistence, storage, navigation, or infrastructure behavior changes.
- Accessibility/readability: white on LabCim blue measures approximately `10.60:1`, exceeding WCAG AA and AAA normal-text contrast thresholds. The explicit foreground/background pair removes dependence on BaseWeb's default tag colors.
- Equivalent behavior in canonical `main`: absent. The existing generic multiselect rule forced dark foreground colors but did not set a tag-specific background/foreground pair.
- Regression risk: low but non-zero. The selectors depend on Streamlit/BaseWeb internal `data-testid`/`data-baseweb` markup, and the rule affects every multiselect chip. Risk is limited to theming/selector compatibility; it does not affect application logic.
- Integration: the patch applied cleanly and was committed separately as `bd57350`; `python -m compileall -q app.py` passed.

### Superseded alternatives

- `2ce7100` remains classified as a superseded mobile-sidebar alternative.
- `5a18336` remains classified as a superseded mobile-menu alternative.

Neither commit was merged, cherry-picked, deleted, or otherwise changed. The later merged sprint 12 navigation line remains authoritative.

### M0/M0.1 worktree review and commit

Before the audit artifact commit, the worktree contained only:

- production-readiness and migration documentation;
- README and historical runbook warnings/links;
- the offline, read-only `scripts/production_preflight.py` checker;
- this repository-state audit.

The preflight tool reads repository files and optional environment metadata, performs no network/database/write operation, and withholds secret values. No unintended application file was staged with the audit artifacts. The nine approved files were committed separately as `164a360` with message `docs: add UFRN production readiness audits`.

### Freeze conclusion

The M1 branch was created from a clean `164a360` worktree. At branch creation, local `main` was two commits ahead of `origin/main`: the accepted isolated contrast commit and the M0/M0.1 audit artifact commit. A push is required to publish those commits and the new branch, but no push was performed during M0.2.

M1 implementation was **not started**.
