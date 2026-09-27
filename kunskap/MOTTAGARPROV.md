# Mottagarprov (del 1:s färdigvillkor) — GODKÄNT 2026-09-26

En färsk läsarsession (Runtimes skrivskyddade profil, claude-opus-5, startad i kontorets rot med kontorets egen AGENTS.md som
systeminstruktion, läsning bara inom kontoret) fick tre frågor om Digitalas kunskapsstöd **utan något filnamn i frågan**.
Den följde den ordinarie ingången — `docs/uppdrag.md`, `DEFINITION.md`, `docs/plan.md` (raden om kunskapsstödet) —
och läste sedan `evidence/digitala/local/kunskap/REGISTER.md`; fyra läsningar, fem turer, 28 sekunder.

Svaren stämde mot registret: (1) det redaktionella passet läser `redaktionellt-pass.md` helt och frontend-designs
"More on writing in design"; (2) vid briefens §5 används "Design principles", "Process: plan, review against the brief,
build, critique" och "Restraint and self-critique" ur `externa/anthropic-frontend-design-SKILL.md`; (3) granskning D
läser WIG `command.md`:s avsnitt Accessibility … Anti-patterns (inte Output Format), med konfliktregeln "ett råd som
strider mot ett accepterat krav redovisas som förslag och ändrar inget".

Det visar **åtkomst och koppling** från ordinarie ingång, inte att kvaliteten förbättrats. Råmaterial:
`mottagarprov-20260926/` (prompt, launch.json med argv och kontorets main vid provet, session.stream.jsonl, svar.md med
lästa filer i ordning). Office main vid provet: c1d0341. Modellanrop: ett (räknas som övrigt paketanrop, inte del 3).

## Mottagarprov etapp 1 (2026-09-26) — DELVIS

Kontrollen i tilläggsmandatets etapp 1: en färsk byggsession (kedjedrivarens Claude Code 2.1.280, claude-opus-5,
verktyg Read, Write, Skill; användarnivåns skills och plugins laddade; tom arbetsyta) fick en mobil-först-uppgift
("Säsongsplan"-sektion för en fiktiv trädgårdsfirma) utan att någon skill nämndes. Utfall: sessionen anropade
`frontend-design:frontend-design` av sig själv som första handling och skrev sedan `index.html`; `emil-design-eng` och
`mobile-native` var listade som tillgängliga men anropades inte. Villkoret "frontend-design och minst en av Emils
skills" är därmed **delvis** uppfyllt: pluginen laddas av sig själv, Emils skills är registrerade och tillgängliga men
laddas inte automatiskt på den uppgiften (L14). 160 s, 0,50 USD; en modellsession (etapp 1, session 1 av 2).
Råmaterial: `../genomforande-20260926/etapp1/mottagarprov-1/` (prompt i `launch.json`, `stream.jsonl`, `UTFALL.md`,
arbetsytans `index.html`).

