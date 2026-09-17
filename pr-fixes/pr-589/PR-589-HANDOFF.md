# PR #589 — Codium-ai/pr-agent 0.44.0 → 0.45.0 (dependabot)

> **Estado:** PR **revisado**, causa del CI rojo **reproducida y aislada**, arreglo
> **verificado** sobre la rama real de Dependabot y ensayado el merge contra `main`
> actual. El arreglo **no se pudo pushear desde este entorno**: la cuenta del sandbox
> (`arena-ai-coding-agent[bot]`) tiene acceso de solo lectura a `FacundoSu1986/Sky-Claw`
> (`git push` → `403 Permission to FacundoSu1986/Sky-Claw.git denied`).
> Se entrega listo para aplicar en 1 comando (parche o bundle).

- Repo: `FacundoSu1986/Sky-Claw` · PR [#589](https://github.com/FacundoSu1986/Sky-Claw/pull/589)
- Rama: `dependabot/github_actions/github-actions-minor-patch-2deadffc52` (head: `2bcd2d3`)
- Base: `main` (head al momento de la revisión: `c34cd3d`, PR #588)
- `mergeStateStatus`: **BLOCKED** · `mergeable`: **MERGEABLE** (sin conflictos de git)

---

## 1. Diagnóstico: por qué fallaba el CI

El bump es correcto: `f3b385ea2927247ddcff2fe252472380b9c8f5fc` es exactamente el
commit de `refs/tags/v0.45.0` de `Codium-ai/pr-agent` (verificado vía API de GitHub),
y `action.yaml` es **byte-idéntico** entre 0.44.0 y 0.45.0. El problema no está en el
bump, sino en la **invariante propia del repo** que lo audita.

`tests/test_qodo_workflow_invariant.py` congela el SHA de la Action en una constante
que Dependabot no toca:

```python
PINNED_ACTION_REF_ESPERADA = "ab6ec54bfeb37933ddb74259338752e9272016c6"  # v0.44.0
```

El PR actualiza los 3 pins de los workflows a v0.45.0 y deja la constante en v0.44.0;
`test_pinning_de_accion_qodo_es_exacto` compara ambos y falla de forma determinista:

```
E  AssertionError: Pinning inesperado en qodo-merge-adversarial.yml / auto-review (step 0):
E  'f3b385ea2927247ddcff2fe252472380b9c8f5fc' != 'ab6ec54bfeb37933ddb74259338752e9272016c6'
```

Consecuencia en #589: fallan los dos jobs de la matriz `🧪 Tests` (windows-latest
py3.11 y py3.12), con lo que el required check `🧪 Tests (Pytest)` queda en rojo y el
PR en `BLOCKED` (los jobs `Lint`, `Mypy`, `Security Scan` y `POSIX Core` sí pasan: no
tocan los SHA). Reproducido localmente sobre el head real del PR: `1 failed, 5 passed`.

Es fricción **intencional** del repo (la invariante fuerza un repin humano explícito en
cada bump), y es el mismo patrón que se usó en #542 (0.43.0) y #562 (0.44.0): en ambos
casos el bump se mergeó *junto* con la actualización de la constante.

## 2. El arreglo

Commit `test(ci): repinear invariante de PR-Agent al SHA auditado de 0.45.0`, un solo
archivo, una sola línea:

```diff
--- a/tests/test_qodo_workflow_invariant.py
+++ b/tests/test_qodo_workflow_invariant.py
@@ -26,7 +26,7 @@
-PINNED_ACTION_REF_ESPERADA = "ab6ec54bfeb37933ddb74259338752e9272016c6"
+PINNED_ACTION_REF_ESPERADA = "f3b385ea2927247ddcff2fe252472380b9c8f5fc"
```

Artefactos en esta carpeta:

| Archivo | Para qué |
| --- | --- |
| `pr-589-fix.patch` | `git am` sobre la rama de Dependabot (más simple) |
| `pr-589-fix.bundle` | `git fetch` del commit ya construido (sin aplicar parches) |

### Opción A (recomendada) — pushear a la rama de Dependabot

Hace que **#589 se ponga verde y mergee tal cual**, sin PR extra.

```bash
git clone https://github.com/FacundoSu1986/Sky-Claw.git && cd Sky-Claw
git fetch origin dependabot/github_actions/github-actions-minor-patch-2deadffc52
git checkout -B fix-589 FETCH_HEAD
git am /ruta/a/pr-589-fix.patch
git push origin HEAD:dependabot/github_actions/github-actions-minor-patch-2deadffc52
```

El push es *fast-forward* (el head remoto `2bcd2d3` es ancestro del commit del arreglo).
El workflow `Qodo Merge - Revisor Adversarial` se dispara por `synchronize`; el CI de
Sky-Claw se re-ejecuta solo y `🧪 Tests (Pytest)` pasa.

Con el bundle, equivalente (arrastra también el commit de Dependabot):

```bash
git clone https://github.com/FacundoSu1986/Sky-Claw.git && cd Sky-Claw
git fetch /ruta/a/pr-589-fix.bundle 'refs/heads/fix/pr589-repin-0450:pr589-fix'
git push origin pr589-fix:dependabot/github_actions/github-actions-minor-patch-2deadffc52
```

### Opción B — editar en la web (sin consola)

`https://github.com/FacundoSu1986/Sky-Claw/edit/dependabot/github_actions/github-actions-minor-patch-2deadffc52/tests/test_qodo_workflow_invariant.py`
→ reemplazar el SHA por `f3b385ea2927247ddcff2fe252472380b9c8f5fc` → commit a esa rama.

### Nota / alternativa descartada

Mergar #589 con override de admin y landear el repin después deja `main` en rojo
mientras tanto (los workflows nuevos + la constante vieja fallan en `main`): no es
recomendable y rompe el criterio fail-closed del repo.

Tras modificar una rama de Dependabot, Dependabot deja de actualizar ese PR (lo dice su
propia descripción). No hay `Require branches to be up to date`: `main` no ha tocado
ninguno de los 3 archivos desde el branch point, así que no hace falta rebase.

## 3. Revisión de compatibilidad del bump (0.44.0 → 0.45.0)

| Comprobación | Resultado |
| --- | --- |
| `refs/tags/v0.45.0` == `f3b385e...` | ✅ coincide con el pin del PR |
| `action.yaml` 0.44.0 vs 0.45.0 | ✅ idéntico (diff vacío): sin cambios de inputs/interfaz |
| Claves de `configuration.toml` eliminadas en 0.45.0 | ✅ ninguna (solo +29 claves nuevas) |
| Claves de `.pr_agent.toml` huérfanas en 0.45.0 | ✅ ninguna (`config.*`, `github.*`, `pr_reviewer.*`, `pr_description.*`, `pr_questions.*` intactas) |
| `github_action_config.*` (auto_review/describe/improve, `pr_actions`, `handle_push_trigger`, `push_commands`) | ✅ siguen soportadas (`pr_agent/servers/github_action_runner.py` v0.45.0) |
| `enable_auto_approval` (nuevo) | ✅ `false` por defecto (alineado con “nunca aprobar” del prompt del repo) |
| `github_app.review_commands` (nuevo) | ✅ `[]` por defecto → **inactivo** (no dispara comandos nuevos) |
| `enable_large_pr_chunking` (nuevo) | ✅ `false` por defecto (`max_model_tokens=200000` sigue siendo la vía) |
| `retry_same_model_on_timeout` (nuevo) | ✅ `true` por defecto → sin cambio de comportamiento |

**Único cambio de comportamiento a tener en cuenta (no bloqueante):**
`persistent_finding_state = true` por defecto en 0.45.0 → las conclusiones de `/review`
se conservan entre re-ejecuciones del mismo PR. Es la feature `feat(review): preserve
findings across review reruns` de la release y conversa bien con el `persistent_comment`
que ya usa el repo; no requiere cambios en `.pr_agent.toml`.

## 4. Colisión con los otros PR abiertos

| PR | Rama | Archivos | ¿Solapa con #589 + fix? |
| --- | --- | --- | --- |
| #590 | `feat/dyndolod-uia-output-gate-v2` | dyndolod, hitl, pyproject/uv.lock… | ❌ no (0 archivos comunes) |
| #528 | `feat/t5v2-uia-output-gate` | dyndolod, hitl, uv.lock… | ❌ no (0 archivos comunes) |

- Archivos de #589 + fix: `.github/workflows/qodo-merge-adversarial.yml`,
  `.github/workflows/qodo-regression-test-oracle.yml`, `tests/test_qodo_workflow_invariant.py`.
- `main` no ha modificado ninguno de esos 3 archivos desde el branch point
  (`git log pr589..main -- <los 3 archivos>` → vacío).
- **Ensayo de merge real**: rama scratch desde `main` actual + merge del fix →
  `Merge made by the 'ort' strategy`, **0 conflictos**, y la invariante pasa en el árbol
  mergeado (6/6). Orden de merge indiferente respecto de #528/#590.

## 5. Verificación ejecutada

| Prueba | Resultado |
| --- | --- |
| `tests/test_qodo_workflow_invariant.py` en el head del PR (sin fix) | ❌ `1 failed, 5 passed` (reproduce el CI) |
| `tests/test_qodo_workflow_invariant.py` con el fix | ✅ `6 passed` |
| `tests/test_ci_platform_policy.py` (el otro test que lee workflows) | ✅ pasa |
| Suite completa `pytest tests/` con el fix (entorno real, `uv sync --extra dev`) | ✅ `6769 passed, 91 skipped, 10 failed` |
| Esos 10 fallos sobre `main` **sin** el fix | ❌ fallan igual → **preexistentes, ajenos al PR** |
| `git am` del parche sobre `2bcd2d3` (head real de la rama de Dependabot) | ✅ árbol resultante idéntico byte a byte al verificado |
| `git fetch` del bundle en un clon limpio | ✅ (`bundle verify` OK; prerequisito = `main` `c34cd3d`) |

**Caveat honesto:** los 10 fallos de la suite completa son ruido de plataforma Linux
(`test_journal.py` con `nan/inf` y `test_runtime_vault_inventory.py` en carreras de
reemplazo/borrado de archivo). El gate real `🧪 Tests` corre **solo en
windows-latest**; el job POSIX es un subconjunto informativo. No se pudo ejecutar la
suite en Windows desde este sandbox: la validación de plataforma de entrega la hará el
CI de #589 al aplicarse el arreglo, que es la única prueba que cambia el resultado.

## 6. Rollback

El arreglo es una línea de test. Revertir = volver la constante a
`ab6ec54bfeb37933ddb74259338752e9272016c6`; obviamente eso exige a su vez revertir el
bump de los 3 pins en los workflows. No hay estado, migración ni dato persistente
involucrado.
