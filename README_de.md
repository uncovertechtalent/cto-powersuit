[English](README.md) · **Deutsch**

# cto-powersuit

<p align="center"><img src="assets/canary.svg" width="200" alt="Der CTO-Powersuit-Kanarienvogel: ein Kanarienvogel mit Schutzhelm und Brustpanzer auf einer Deploy-Pipeline"></p>

[![checks](https://github.com/uncovertechtalent/cto-powersuit/actions/workflows/checks.yml/badge.svg)](https://github.com/uncovertechtalent/cto-powersuit/actions/workflows/checks.yml) [![skills.sh](https://skills.sh/b/uncovertechtalent/cto-powersuit)](https://skills.sh/uncovertechtalent/cto-powersuit)

**Der CTO-Powersuit ist ein Satz Agent-Skills, ein Modul pro CTO-Funktion vom Deploy-Gate bis zur Übergabe, mit dem eine einzelne Person die gesamte Engineering-Plattform eines Unternehmens betreibt.**

> The CTO powersuit is a set of agent skills, one module per CTO function from the deploy gate to the hand-over, that one person uses to run a company's whole engineering platform.

von [Stefan Coetzee](https://machinebehavior.io/your-next-cto/)

Die Module kommen als ein Plugin-Marketplace für Claude Code, ein Plugin pro Funktion, und lassen sich auch mit der skills CLI installieren. Ein Team installiert die Module, die es braucht, und betreibt sie mit allgemeinen Standardwerten.

Jeder Skill liest außerdem ein privates Overlay, wenn es eines gibt: deine eigenen Daten für dieses Modul, außerhalb des Repositorys gespeichert. Siehe [Overlay](#overlay-deine-private-ebene).

## Drei Wege, den Powersuit zu nutzen

1. **Selbst betreiben.** Dein Team installiert die Module aus diesem Repository und betreibt sie selbst. Siehe [Installation](#installation).
2. **Hilfe holen.** Kommt dein Team nicht weiter, übernimmt Stefan Coetzee eine Bestandsaufnahme oder die Installation.
3. **Stefan Coetzee als Fractional CTO.** Er betreibt den Powersuit für dein Unternehmen, mit seiner eigenen Forschung und seinen eigenen Daten in einem privaten Overlay über den offenen Modulen. Dieses Overlay bleibt außerhalb dieses Repositorys.

Für den zweiten und dritten Weg: [machinebehavior.io/your-next-cto/](https://machinebehavior.io/your-next-cto/).

## Module

| Plugin | Was es tut | Braucht |
|---|---|---|
| `ai-ops` | Betrieb der Coding-Agenten eines Teams: ein gemeinsames Harness mit engen Berechtigungen, Agenten-Kosten pro API-Anfrage gemessen, mit einem Budget-Alert, ein Audit-Trail jedes Tool-Aufrufs mit der Angabe, wer ihn erlaubt oder abgelehnt hat, und einem Alert bei einer Häufung abgelehnter Aufrufe, und ein Koordinator-Muster mit dem Zustand in Dateien. `vestige`, `stance` und `vault` sind seine optionalen Teile. Ein Gate-Check, der prüft, dass gemeinsame Agenten-Einstellungen keine Secrets und keine Wildcard-Berechtigungen enthalten. | Python 3.9+; `observability` für das Metering und den Audit-Trail |
| `aieo` | Sichtbarkeit in KI-Suchen: `llms.txt`, strukturierte Daten, ein fester Satz von Anfragen an KI-Suchmaschinen und datierte Vorhersagen, die vor dem Livegang einer Seite gehasht werden. Ein Gate-Check, der prüft, dass jede Vorhersage-Datei zu ihrem Hash passt. | Python 3.9+ |
| `compliance` | Eine Control-Map zu ISO 27001, TISAX, NIS2 und DSGVO nach Klausel- und Artikelnummer, eine Triage nach dem AI Act und eine rechtliche Grundausstattung für eine Website (Impressum, Datenschutzseite, security.txt, keine Anfragen an Dritte beim Laden der Seite). Gate-Checks für security.txt und Anfragen an Dritte. | Python 3.9+ |
| `decisions` | RFCs, Architecture Decision Records (ADRs) und ein Review des Entscheidungslogs. Vorlagen für beide Dokumente und ein Gate-Check, der prüft, dass jeder ADR einen Status, einen Owner und ein Datum hat. | Python 3.9+ für den Gate-Check |
| `docs` | Ein Docs-Baum, in dem jede Seite einen Owner und Review-Daten hat, Runbooks und eine Suche nach veralteten Seiten. Ein statischer Docs-Build und ein Gate-Check auf die Review-Felder. | Python 3.9+ |
| `finops` | Eine Kosten-Baseline aus Rechnungen und Billing-Exporten, Showback pro Team oder Service, Stückkosten, ein Audit des SaaS-Bestands (behalten, kündigen oder ersetzen) und ein FOCUS-Export. Ein Gate-Check, der prüft, dass jede Kostenangabe in den Docs einen Zeitraum und eine Quelle nennt. | Python 3.9+ |
| `fit` | Die Eingangsbewertung: liest ein Repository und seine Docs, führt das SDLC-Audit aus und empfiehlt, welche Module in welcher Reihenfolge eingesetzt werden. Eine Repo-Sprechstunde, die ein öffentliches Repository auf Wunsch seiner Eigentümer prüft und einen kurzen Bericht mit den drei größten Lücken und einen kleinen Pull Request entwirft; Secrets und Sicherheitslücken landen nur in einer privaten Notiz. Ein Gate-Check, der prüft, dass jedes als eingesetzt markierte Modul installiert ist. | `sdlc`; `gate` und `security` für die Sprechstunde |
| `gate` | Ein Deploy-Gate: ein Regelordner mit Pass- und Fail-Fixtures pro Regel, Laufprotokolle, Befunde, die sich erst mit einem bestandenen späteren Lauf schließen, und ein Workflow, dessen Deploy-Job auf das Gate wartet. Die Checks der anderen Module laufen darin. Gate-Checks, die prüfen, dass jede blockierende Regel funktionierende Fixtures hat und jede Action von außerhalb des Repositorys auf einen Commit-SHA festgelegt ist. | Python 3.9+, GitHub Actions für den Workflow |
| `handover` | Übergabe der Plattform an ihren Owner: Schulungs-Checklisten pro installiertem Modul, Exit-Kriterien und ein Testplan, der zeigt, dass der Owner die Plattform allein mit den Docs betreibt. Ein Gate-Check, der prüft, dass jedes installierte Modul einen benannten Owner hat. | Python 3.9+ für den Gate-Check |
| `hiring` | Ein Interview-Ablauf, in dem jede Stufe ein Signal erhebt, Bewertungsraster mit verankerten Stufen, Debriefs mit Belegen vor der Abstimmung und das Profil der Person, die die Plattform übernimmt. Ein Gate-Check, der prüft, dass jede Dimension eines Rasters verankerte Stufen hat. | Python 3.9+ für den Gate-Check |
| `observability` | Alloy, Prometheus, Loki, Grafana und Alertmanager mit Docker Compose, Dashboards als Code und Alert-Routen. Ein Gate-Check, der prüft, dass jede Alert-Regel eine Route und ein Runbook nennt. | Docker, Python 3.9+ |
| `red-team` | Drucktests für die KI-Funktionen eines Teams: Taktiken wählen, mehrstufigen Druck nach Skript in einer Welt mit bekannter richtiger Antwort ausüben und die getroffene Entscheidung bewerten. Ein Gate-Check, der prüft, dass jeder Lauf die erwartete und die beobachtete Entscheidung nennt. | Python 3.9+ |
| `reliability` | Verfügbarkeitsziele pro Service mit der Ausfallzeit, die jedes Ziel erlaubt, SLOs und Error Budgets, Abläufe für Incidents und Postmortems, eine statische Statusseite und eine On-Call-Regelung. Ein Gate-Check, der prüft, dass jeder Service im Katalog einen Owner, ein SLO und ein Runbook hat. | Python 3.9+ |
| `sdlc` | Der Lebenszyklus, der die Module verbindet: ein Audit, das die fehlenden Phasen eines Repositorys ohne Prozess nach Dringlichkeit ordnet, die Übersicht der Phasen, Tickets, Change-Review für Code von Agenten (`change-review`), ein lokaler CI-Lauf vor jedem Push (`pre-push`, mit preloop), Teststrategie und Release mit Rollback. Ein Gate-Check, der prüft, dass jede Änderung ein Ticket oder eine Entscheidung nennt. | Python 3.9+, git; preloop für `pre-push` (optional) |
| `security` | Sicherheit für ein Repository und seine Coding-Agenten: Actions per Commit-SHA gepinnt und auf eine Liste erlaubter Owner begrenzt, ein Schwachstellen-Scan der Lock-Dateien und eine SBOM, eine Herkunftsprüfung vor der Installation eines Agent-Skills oder MCP-Servers, Runbooks für die Schlüsselrotation, ein Zugriffs-Review nur mit Lesezugriff, das Merges am Pflicht-Review vorbei findet, Threat Models pro RFC und Schwachstellen-Tickets mit Frist. Gate-Checks für Secrets in versionierten Dateien und für Action-Owner, dazu ein Pre-Push-Hook, der private Begriffe (Namen, internes Kürzel, private Hosts) aus öffentlichen Repositorys heraushält; die Begriffsliste bleibt auf deinem Rechner. | Python 3.9+, `gh`; osv-scanner optional |

## Wissensinfrastruktur

Diese drei Plugins bilden die Ebene der Wissensinfrastruktur und sind die optionalen Teile des Moduls `ai-ops` ([was Wissensinfrastruktur für LLMs bedeutet](https://coetzeestefan.substack.com/p/knowledge-infrastructure-for-llms), auf Englisch). `vault` ist die Wissensbasis mit ihrer Suche, `vestige` setzt deine Regeln an der Ausgabegrenze durch, und `stance` ergänzt Grenzregeln und eine Prüfung nach dem Receipts-Standard. Jedes dieser Plugins ersetzt eine manuelle Installation (Dateien nach `~/.claude/` kopieren, dann `settings.json` von Hand bearbeiten) durch zwei Befehle.

| Plugin | Was es tut | Braucht |
|---|---|---|
| `vestige` | Ein Ausgabefilter, den du auf dich selbst kalibrierst. `/vestige:calibrate` durchsucht deine eigenen Transkripte nach den Momenten, in denen du widersprochen hast, und baut daraus deinen Katalog. Hooks prüfen jede Antwort und jede Markdown-Datei, die Claude schreibt. | Node 14+ |
| `vault` | Ein Vault aus reinem Markdown mit hybrider Stichwort- und semantischer Suche, für Claude als MCP-Server bereitgestellt. Skills, um den Vault anzulegen, ihn aus einem Interview zu befüllen und Dokumente in Atome zu zerlegen. | [uv](https://docs.astral.sh/uv/) (Python 3.12+) |
| `stance` | Haltungsfilter gegen den antrainierten Anpassungsreflex: `professional-b2` (klares Register, keine Höflichkeitsreste), `good-chad` (hält die Position bei Widerspruch, kein Einknicken), `receipts` (erst prüfen, dann behaupten), `poles` (Entscheidungen ohne Absicherungsfloskeln) und `mode-leak` (Sprechmuster in geschriebenem Text). | Node 14+, bash |

Die Plugins sind unabhängig voneinander. Installiere die, die du brauchst. Jedes Modul funktioniert ohne die anderen; die Gate-Checks der Module brauchen `gate`, um in der CI zu laufen. In einem bestehenden Repository beginnst du mit `/sdlc:sdlc-audit`: Es braucht kein anderes Modul und nennt für jede Lücke das Modul, das sie schließt.

## Installation

Dieses Projekt gibt es nur unter [github.com/uncovertechtalent/cto-powersuit](https://github.com/uncovertechtalent/cto-powersuit). Installiere es ausschließlich mit den beiden Befehlen unten, die den Eigentümer des Repositorys ausdrücklich nennen: `claude plugin marketplace add uncovertechtalent/cto-powersuit` und `npx skills add uncovertechtalent/cto-powersuit`, oder aus einem Klon dieses Repositorys. Releases sind Git-Tags mit Release Notes. Jedes Release nach v0.1.0 trägt außerdem einen Quell-Tarball seines Tags, dessen sha256 und eine Build-Provenance-Attestierung, damit du eine Kopie gegen dieses Repository prüfen kannst ([Versionen und Rollback](#versionen-und-rollback)). Der Tarball dient der Prüfung und ist kein Installationsweg. Wer dir anderswo eine Kopie mit Download-Button anbietet, bietet nicht dieses Projekt an. Andere Skills und MCP-Server prüfst du vor der Installation mit der Herkunftsprüfung des Security-Moduls: [`/security:supply-chain`](plugins/security/skills/supply-chain/SKILL.md), Schritt 7.

```bash
claude plugin marketplace add uncovertechtalent/cto-powersuit
claude plugin install ai-ops@cto-powersuit
claude plugin install aieo@cto-powersuit
claude plugin install compliance@cto-powersuit
claude plugin install decisions@cto-powersuit
claude plugin install docs@cto-powersuit
claude plugin install finops@cto-powersuit
claude plugin install fit@cto-powersuit
claude plugin install gate@cto-powersuit
claude plugin install handover@cto-powersuit
claude plugin install hiring@cto-powersuit
claude plugin install observability@cto-powersuit
claude plugin install red-team@cto-powersuit
claude plugin install reliability@cto-powersuit
claude plugin install sdlc@cto-powersuit
claude plugin install security@cto-powersuit
claude plugin install vestige@cto-powersuit
claude plugin install vault@cto-powersuit
claude plugin install stance@cto-powersuit
```

In Claude Code funktioniert dasselbe als `/plugin marketplace add ...` und `/plugin install ...`. Starte Claude Code nach der Installation neu.

Aus einem lokalen Klon: `claude plugin marketplace add /path/to/cto-powersuit`.

Mit der [skills-CLI](https://skills.sh), für Claude Code und andere Agenten:

```bash
npx skills add uncovertechtalent/cto-powersuit
```

Die skills-CLI kopiert nur die Skill-Ordner. Skills, die Vorlagen kopieren, die Hooks und der MCP-Server brauchen die Plugin-Installation oben oder einen Klon dieses Repositorys.

## Versionen und Rollback

Jedes Release ist ein Git-Tag `v<version>` auf `main` mit einem Eintrag in [CHANGELOG.md](CHANGELOG.md). Die Version des Powersuits steht in `.claude-plugin/marketplace.json` unter `metadata.version`. Jedes Plugin hat seine eigene Version in seiner `plugin.json`, und ein Release erhöht die Version jedes Plugins, dessen Dateien sich seit dem letzten Tag geändert haben. `claude plugin update` vergleicht nur diese Version. Deshalb lässt CI eine Änderung an einem Plugin scheitern, die seine Version nicht erhöht.

Die Installationsbefehle oben folgen `main`. Um ein Release festzuhalten, hänge seinen Tag an die Quelle:

```bash
claude plugin marketplace add uncovertechtalent/cto-powersuit#v0.1.0
npx skills add uncovertechtalent/cto-powersuit#v0.1.0
```

Beide Installer geben die Ref an `git clone --branch` weiter. Ein Tag oder ein Branch-Name funktioniert, ein Commit-SHA nicht. `claude plugin marketplace update` bleibt auf dem festgehaltenen Tag. Die skills-CLI schreibt die Ref in `skills-lock.json`, und `npx skills update` behält sie bei.

Für ein Rollback oder einen Wechsel auf ein anderes Release entfernst du den Marketplace, fügst ihn mit dem gewünschten Release wieder hinzu und installierst die Plugins neu. Das Entfernen des Marketplace deinstalliert seine Plugins und löscht ihre gespeicherten Optionen. Notiere dir deshalb vorher Optionen wie den `vault`-Pfad. Die `ref` in `settings.json` von Hand zu ändern, verschiebt den Pin nicht: In einem Test mit Claude Code 2.1.286 fehlte der Marketplace danach.

```bash
claude plugin marketplace remove cto-powersuit
claude plugin marketplace add uncovertechtalent/cto-powersuit#v0.1.0
claude plugin install sdlc@cto-powersuit
```

Mit der skills-CLI führst du `npx skills add` mit dem gewünschten Tag erneut aus. Der Befehl überschreibt die installierten Skills und die Ref in `skills-lock.json`.

Getestet mit Claude Code 2.1.286 und skills 1.7.2.

Jedes Release nach v0.1.0 trägt zwei Dateien: `cto-powersuit-<version>.tar.gz`, ein `git archive` des Tags, und `cto-powersuit-<version>.tar.gz.sha256`. Wenn ein Tag gepusht wird, prüft der Release-Workflow ([`.github/workflows/release.yml`](.github/workflows/release.yml)) die Release-Metadaten, baut beide Dateien, attestiert sie mit Build-Provenance und hängt sie an das GitHub-Release. Gibt es das Release noch nicht, legt der Workflow es an, mit dem Abschnitt des Tags aus dem Changelog als Release Notes. v0.1.0 wurde getaggt, bevor es den Workflow gab, und hat weder Dateien noch eine Attestierung. So prüfst du eine heruntergeladene Datei:

```bash
gh attestation verify cto-powersuit-<version>.tar.gz --repo uncovertechtalent/cto-powersuit
sha256sum -c cto-powersuit-<version>.tar.gz.sha256
```

`gh attestation verify` prüft die Sigstore-Signatur und dass der signierende Workflow in diesem Repository lief. Mit `--signer-workflow uncovertechtalent/cto-powersuit/.github/workflows/release.yml` verlangst du zusätzlich genau diesen Release-Workflow. Unter macOS nimmst du für den zweiten Befehl `shasum -a 256 -c`. Die Herkunftsprüfung des Security-Moduls ([`/security:supply-chain`](plugins/security/skills/supply-chain/SKILL.md)) wertet ein attestiertes Release-Asset nicht als ungeprüfte Binärdatei. Sie liest, dass die Attestierung existiert, und überlässt die Signatur `gh attestation verify`. Eine Attestierung zeigt, welcher Workflow welches Repositorys die Datei gebaut hat, nicht, ob dieses Repository Vertrauen verdient; das bewerten die anderen Signale der Prüfung.

## Overlay: deine private Ebene

Jeder Skill in diesem Repository arbeitet mit allgemeinen Standardwerten. Jeder Skill prüft außerdem, ob es ein Overlay gibt: einen Ordner außerhalb des Repositorys mit deinen eigenen Daten für das jeweilige Modul, zum Beispiel Bewertungsraster, Kalibrierungen, frühere Entscheidungen, Incident-Historie und lokale Konventionen.

Setze `POWERSUIT_OVERLAY` auf den Stammordner des Overlays, in deiner Shell oder im `env`-Block von `settings.json`. Ein Ordner pro Modul, benannt nach dem Plugin:

```text
$POWERSUIT_OVERLAY/
  decisions/
    README.md      what this overlay holds; every skill in the module reads it first
    adr/           files for one skill, named after the skill
  docs/
  gate/
  vestige/
```

Lesereihenfolge für den Skill `<skill>` im Modul `<module>`:

1. `$POWERSUIT_OVERLAY/<module>/README.md`, falls vorhanden.
2. `$POWERSUIT_OVERLAY/<module>/<skill>/`, falls vorhanden.
3. Die Standardwerte im Skill selbst.

Wenn Overlay und Skill sich widersprechen, folgt der Skill dem Overlay. Ist die Variable nicht gesetzt oder fehlt der Modulordner, läuft der Skill mit seinen Standardwerten und fragt nicht nach einem Overlay.

Nichts aus einem Overlay kommt in dieses Repository. Bewahre es an einem privaten Ort ohne öffentliches Remote auf. Ein Team, das die Module installiert, baut mit der Zeit sein eigenes Overlay aus seinen Entscheidungen, Incidents, Docs und Kostendaten auf.

## Aufbau eines Moduls

Jedes Modul ist ein Plugin unter `plugins/<module>/` mit vier Teilen:

| Teil | Pfad im Plugin | Was es ist |
|---|---|---|
| Skills | `skills/<skill>/SKILL.md` | Eine Aufgabe pro Skill, im Agent-Skills-Format. Jeder Skill prüft zuerst das Overlay. |
| Vorlagen | `templates/` | Dateien, die im Ziel-Repository landen, unter den Pfaden, die sie dort haben. Skills kopieren sie und überschreiben nie eine vorhandene Datei. |
| Gate-Check | `checks/<rule>.py`, `checks/fixtures/<rule-id>/pass/` und `fail/` | Eine Regel, die das Deploy-Gate des Moduls `gate` ausführen kann. Die beiden Fixtures sind kleine Repository-Bäume: Die Regel muss auf `pass/` bestehen und auf `fail/` scheitern. |
| Demo | eine Zeile in der `README.md` des Moduls | Die Seite auf machinebehavior.io/inside, auf der das Modul öffentlich läuft. |

Das Plugin braucht außerdem `.claude-plugin/plugin.json` und einen Eintrag in `.claude-plugin/marketplace.json`.

Die Plugins der Wissensinfrastruktur (`vestige`, `vault`, `stance`) folgen demselben Aufbau. Ihre Vorlagen sind die Filter-Vorlage von vestige und der Start-Vault, und jedes hat einen eigenen Gate-Check.

## vestige

Führe zuerst `/vestige:calibrate` aus. Bis dahin nutzen die Hooks eine kleine Starttabelle (Lob zum Einstieg, Service-Floskeln am Ende, Füllphrasen, Bühnen-Einstiege). Die Kalibrierung schreibt zwei Dateien, die dir gehören, außerhalb des Plugins, damit Plugin-Updates sie nie überschreiben:

- `~/.claude/skills/output-filter/SKILL.md`: dein Filter-Skill, geschrieben aus der Vorlage in `plugins/vestige/templates/output-filter/`. Die Vorlage wird erst zum Skill, wenn die Kalibrierung sie ausfüllt.
- `~/.claude/vestige-patterns.js`: deine Regeltabelle. Die Hooks laden sie anstelle der Starttabelle.

Treffer-Logs landen in `~/.claude/vestige-scan.log` und `~/.claude/guess-scan.log`. `node <plugin>/hooks/analyze-log.js` macht aus dem Log Kandidaten zum Hochstufen und zum Ausmustern. Alle Pfade folgen `CLAUDE_CONFIG_DIR`, wenn du die Variable setzt.

Hooks: Ein Stop-Hook prüft jede Antwort (`vestige-scan.js`) und die Pfade, die sie nennt (`guess-scan.js`); ein PostToolUse-Hook prüft `.md`-Dateien nach Write und Edit (`vestige-write-scan.js`). Die Methode und ihre Grenzen: [vestige-kit](https://github.com/uncovertechtalent/vestige-kit).

## vault

1. `/vault:vault-init` kopiert den Start-Vault nach `~/vault`. Dabei wird nie eine Datei überschrieben.
2. `/vault:seed` interviewt dich und baut die Struktur aus deinen eigenen Themengebieten.
3. Der MCP-Server `vault-search` gibt Claude `vault_search`, `vault_read`, `vault_ask`, `vault_reindex` und `vault_list_tags`.

Für einen Vault an einem anderen Ort setzt du die Plugin-Option: `/plugin configure vault@cto-powersuit` in Claude Code oder `claude plugin install vault@cto-powersuit --config vault_path=/path/to/vault`. Starte Claude Code nach der Änderung neu.

Die private Grenze: Ordner, die in `.vsearchignore` im Stammordner des Vaults stehen, und Notizen mit den Tags `private`, `status/private` oder `status/sensitive` werden nie indexiert und nie zurückgegeben, und `vault_read` lehnt sie ab. Der erste Suchlauf lädt etwa 130 MB Embedding-Gewichte herunter. Details: [vault-kit](https://github.com/uncovertechtalent/vault-kit).

## stance

Das Plugin `stance` ist standardmäßig aktiv. Beim Start einer Sitzung laden seine Hooks `receipts`, `professional-b2` (Stufe `full`), `good-chad` und zwei Beispielpaare korrigierter Ausgabe. Bei jedem Prompt fügen die Modus-Tracker für jeden aktiven Modus eine einzeilige Erinnerung ein.

Modi in der Sitzung umschalten: `/stance:professional-b2 lite|full|ultra`, `b2 mode`, `stop b2`, `/stance:good-chad off`, `stop good chad`, `normal mode` (alle aus). `poles` und `mode-leak` laufen nur, wenn du sie aufrufst.

Die Standardwerte änderst du mit Umgebungsvariablen (in der Shell oder im `env`-Block von `settings.json`):

| Variable | Werte | Standard |
|---|---|---|
| `PROFESSIONAL_B2_DEFAULT_MODE` | `off`, `lite`, `full`, `ultra` | `full` |
| `GOOD_CHAD_DEFAULT_MODE` | `off`, `on` | `on` |
| `STANCE_RECEIPTS` | `off`, `on` | `on` |
| `STANCE_EXEMPLARS` | `off`, `on` | `on` |

Die Filter sind Text im Kontextfenster, deshalb entfernt sich das Modell im Lauf einer langen Sitzung von ihnen. Die Hooks wiederholen sie in jeder Runde, und der Stop-Hook von `vestige` erfasst den Teil, den ein regulärer Ausdruck finden kann. Die Prüfung, die hält, bist du, wenn du die Ausgabe liest.

Optional: [caveman](https://github.com/JuliusBrussee/caveman) (Drittanbieter) komprimiert die Ausgabe. Es lässt sich mit `professional-b2` und `good-chad` kombinieren.

## Umstieg von der manuellen Installation

Wenn du die Kits früher nach `~/.claude/` kopiert hast, entferne nach der Installation der Plugins die kopierten Hook-Einträge aus `~/.claude/settings.json` und die kopierten Skills aus `~/.claude/skills/`. Sonst wird jede Antwort zweimal geprüft, und die Skills werden doppelt geladen. Behalte deine kalibrierte `vestige-patterns.js`: Verschiebe sie von `~/.claude/hooks/` nach `~/.claude/`.

## Eine Änderung prüfen

```bash
claude plugin validate --strict .
for p in plugins/* plugins/*/skills; do claude plugin validate --strict "$p"; done
python3 scripts/test_checks.py
python3 plugins/sdlc/skills/sdlc-audit/test_probe.py
python3 plugins/gate/tests/test_run.py
python3 scripts/check_repo.py
python3 scripts/test_release.py
python3 scripts/check_release.py
```

`scripts/test_checks.py` führt den Gate-Check jedes Moduls mit dem Gate-Runner gegen seine Pass- und Fail-Fixtures aus. Das Skript braucht Python 3.9+ und endet mit Exit-Code 1, wenn ein Check eine Fail-Fixture besteht oder an einer Pass-Fixture scheitert. `plugins/sdlc/skills/sdlc-audit/test_probe.py` führt die aufgezeichneten Fälle der Probe des SDLC-Audits aus. `plugins/gate/tests/test_run.py` testet den Gate-Runner selbst an kleinen Repositories, die es in einem temporären Ordner anlegt. `scripts/check_repo.py` gleicht Marketplace, Plugin-Ordner, beide READMEs, die Demo-Zeilen und den Overlay-Abschnitt jedes Skills miteinander ab. `scripts/check_release.py` prüft, dass Changelog und Version des Powersuits übereinstimmen und dass jedes Plugin, das sich seit dem letzten Release-Tag geändert hat, eine höhere Version trägt. `scripts/test_release.py` testet das an kleinen Repositories.

CI führt diese Befehle bei jedem Push und jedem Pull Request aus ([`.github/workflows/checks.yml`](.github/workflows/checks.yml)), dazu zizmor auf die Workflows; jeder akzeptierte Befund steht mit Begründung in `.github/zizmor.yml`.

Reviews laufen in drei Ebenen, und jede Ebene sieht nur den Kontext, den sie sehen darf:

1. **Selbst-Review in der CI.** Bei einem Pull Request aus einem Branch dieses Repositorys führt [`.github/workflows/change-review.yml`](.github/workflows/change-review.yml) `/sdlc:change-review` vom Basis-Branch aus. Der Skill liest zuerst den Changelog, die READMEs, die Konventionen, die CI durchsetzt, und das verknüpfte Issue. Dann prüft er die Änderung dagegen und postet einen Kommentar. Eine Entscheidung, die diese Dateien festhalten, wird zur Notiz ("intentional per <Datei>"), nicht zum Befund. Das Modell bekommt den Pull Request als Dateien und hat keine Shell und kein Netzwerk. Das Review ist beratend: Es meldet einen neutralen Check mit der Zahl der Befunde und lässt nie einen scheitern; "block"-Befunde werden zum scheiternden Check, sobald die Quote falscher Befunde aus den ersten Reviews bekannt ist. Der Workflow überspringt Dependabot und andere Bots und braucht das Repository-Secret `CLAUDE_CODE_OAUTH_TOKEN`; ohne es wird er übersprungen.
2. **Review mit privatem Kontext, nur auf deinem eigenen Rechner.** Mit `kb` liest der Skill zusätzlich deine private Wissensbasis: einen `vault-search`-MCP-Server oder einen Ordner, den dein Overlay nennt. Dann postet er einen Kommentar, der nur öffentliche Dateien zitiert, nachdem du ihn gelesen hast. Nichts Privates erreicht die CI oder einen Review-Bot.
3. **CodeRabbit** liest [`.coderabbit.yaml`](.coderabbit.yaml): Pfad-Anweisungen, die auf die Entscheidungen zeigen, die dieses Repository festhält, und keine MCP-Wissensquelle.

```bash
claude "/sdlc:change-review 42 kb"
```

### Lokales Review, bis es CI-Tokens gibt

Das Review in der CI braucht `CLAUDE_CODE_OAUTH_TOKEN` oder einen API-Schlüssel, und keins von beiden ist bisher gesetzt, deshalb wird der Workflow übersprungen. Bis er läuft, führt jede Session das lokale Review auf ihrem Pull Request aus, bevor sie ihn als fertig meldet. Das Skript hält das Design der CI ein:
- Es lädt das sdlc-Plugin aus einem sauberen Klon von `main` in `~/.cache/powersuit-main`, nie aus dem Pull Request, und nur für diesen Lauf. Nichts wird installiert, keine Einstellungsdatei ändert sich.
- Das Modell bekommt den Pull Request als Dateien, ohne Shell und ohne Netzwerk, und läuft mit `--restricted`.
- Die private Wissensbasis erreicht es nur über deren MCP-Suchwerkzeuge (standardmäßig der Server `vault-search` aus deiner Claude-Konfiguration).
- Das Skript, nicht das Modell, prüft den Kommentar mit dem Private-Terms-Check und postet oder aktualisiert einen Kommentar pro Pull Request. Der Kommentar endet mit einer Zeile, die ihn als beratendes, lokal ausgeführtes Review kennzeichnet.

```bash
git clone https://github.com/uncovertechtalent/cto-powersuit.git ~/.cache/powersuit-main
install -d ~/.config/powersuit
install -m 755 ~/.cache/powersuit-main/plugins/sdlc/skills/change-review/review-pr.sh ~/.config/powersuit/review-pr.sh
~/.config/powersuit/review-pr.sh uncovertechtalent/cto-powersuit 42
~/.config/powersuit/review-pr.sh uncovertechtalent/cto-powersuit 42 --post-saved
```

Ein Lauf speichert den Kommentar, zeigt Züge, Dauer und Kostenschätzung und fragt im Terminal vor dem Posten. `--post-saved` postet den gespeicherten Kommentar ohne neues Review, damit online steht, was du gelesen hast. Das Skript postet nicht, wenn der Private-Terms-Check einen Begriff findet. Es postet auch nicht, wenn der Check nicht laufen kann (keine Liste oder eine leere), außer du gibst nach dem Lesen `--allow-unscanned` an.

## Evals

`claude plugin eval` führt Verhaltensfälle für drei Skills aus: `/sdlc:sdlc-audit` und `/sdlc:pre-push` in `plugins/sdlc/evals/` sowie `/fit:repo-clinic` in `plugins/fit/evals/`. Fünf der sechs Fälle prüfen einen Fehlerpfad, in dem der Skill ablehnen oder anhalten muss. Jeder Lauf ist ein Modellaufruf auf deinem Konto. Deshalb laufen die Fälle lokal und nicht in CI.

```bash
cd plugins/sdlc
claude plugin eval . --trust-plugin --scaffold --allow-tools Bash Write Edit --model claude-sonnet-5-5 --judge-model claude-haiku-5-5 --no-publish --threshold 0.8
cd ../fit
claude plugin eval . --trust-plugin --scaffold --allow-tools Bash Write Edit --model claude-sonnet-5-5 --judge-model claude-haiku-5-5 --no-publish --threshold 0.8
```

`--scaffold` führt das `scaffold.sh` jedes Falls aus, das im Arbeitsordner des Laufs ein kleines Fixture-Repository anlegt. Setze auf macOS `/Library/Developer/CommandLineTools/usr/bin` an den Anfang von `PATH`: Die Sandbox der Evals bricht den Shim `/usr/bin/git`, und die Skills lesen die Git-Historie. Ein voller Lauf kostet etwa 4 $. [EVALS.md](EVALS.md) enthält die Ergebnisse.

## Lizenz

MIT. `plugins/stance/THIRD_PARTY_NOTICES.md` listet den Code auf, der aus caveman übernommen wurde.
