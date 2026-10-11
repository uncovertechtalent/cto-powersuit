[English](README.md) · **Deutsch**

# cto-powersuit

[![skills.sh](https://skills.sh/b/uncovertechtalent/cto-powersuit)](https://skills.sh/uncovertechtalent/cto-powersuit)

Agent-Skills für die Arbeit eines CTO, ein Plugin pro Funktion, in einem Plugin-Marketplace für Claude Code. Ein Team installiert die Module, die es braucht, und betreibt sie mit allgemeinen Standardwerten.

Jeder Skill liest außerdem ein privates Overlay, wenn es eines gibt: deine eigenen Daten für dieses Modul, außerhalb des Repositorys gespeichert. Siehe [Overlay](#overlay-deine-private-ebene).

## Module

| Plugin | Was es tut | Braucht |
|---|---|---|
| `decisions` | RFCs, Architecture Decision Records (ADRs) und ein Review des Entscheidungslogs. Vorlagen für beide Dokumente und ein Gate-Check, der prüft, dass jeder ADR einen Status, einen Owner und ein Datum hat. | Python 3.9+ für den Gate-Check |
| `docs` | Ein Docs-Baum, in dem jede Seite einen Owner und Review-Daten hat, Runbooks und eine Suche nach veralteten Seiten. Ein statischer Docs-Build und ein Gate-Check auf die Review-Felder. | Python 3.9+ |
| `gate` | Ein Deploy-Gate: ein Regelordner mit Pass- und Fail-Fixtures pro Regel, Laufprotokolle, Befunde, die sich erst mit einem bestandenen späteren Lauf schließen, und ein Workflow, dessen Deploy-Job auf das Gate wartet. Die Checks der anderen Module laufen darin. | Python 3.9+, GitHub Actions für den Workflow |
| `observability` | Alloy, Prometheus, Loki, Grafana und Alertmanager mit Docker Compose, Dashboards als Code und Alert-Routen. Ein Gate-Check, der prüft, dass jede Alert-Regel eine Route und ein Runbook nennt. | Docker, Python 3.9+ |
| `sdlc` | Der Lebenszyklus, der die Module verbindet: ein Audit, das die fehlenden Phasen eines Repositorys ohne Prozess nach Dringlichkeit ordnet, die Übersicht der Phasen, Tickets, Review für Änderungen von Agenten, Teststrategie und Release mit Rollback. Ein Gate-Check, der prüft, dass jede Änderung ein Ticket oder eine Entscheidung nennt. | Python 3.9+, git |

## Wissensinfrastruktur

Diese drei Plugins bilden die Ebene der Wissensinfrastruktur ([was Wissensinfrastruktur für LLMs bedeutet](https://coetzeestefan.substack.com/p/knowledge-infrastructure-for-llms), auf Englisch). `vault` ist die Wissensbasis mit ihrer Suche, `vestige` setzt deine Regeln an der Ausgabegrenze durch, und `stance` ergänzt Grenzregeln und eine Prüfung nach dem Receipts-Standard. Jedes dieser Plugins ersetzt eine manuelle Installation (Dateien nach `~/.claude/` kopieren, dann `settings.json` von Hand bearbeiten) durch zwei Befehle.

| Plugin | Was es tut | Braucht |
|---|---|---|
| `vestige` | Ein Ausgabefilter, den du auf dich selbst kalibrierst. `/vestige:calibrate` durchsucht deine eigenen Transkripte nach den Momenten, in denen du widersprochen hast, und baut daraus deinen Katalog. Hooks prüfen jede Antwort und jede Markdown-Datei, die Claude schreibt. | Node 14+ |
| `vault` | Ein Vault aus reinem Markdown mit hybrider Stichwort- und semantischer Suche, für Claude als MCP-Server bereitgestellt. Skills, um den Vault anzulegen, ihn aus einem Interview zu befüllen und Dokumente in Atome zu zerlegen. | [uv](https://docs.astral.sh/uv/) (Python 3.12+) |
| `stance` | Haltungsfilter gegen den antrainierten Anpassungsreflex: `professional-b2` (klares Register, keine Höflichkeitsreste), `good-chad` (hält die Position bei Widerspruch, kein Einknicken), `receipts` (erst prüfen, dann behaupten), `poles` (Entscheidungen ohne Absicherungsfloskeln) und `mode-leak` (Sprechmuster in geschriebenem Text). | Node 14+, bash |

Die Plugins sind unabhängig voneinander. Installiere die, die du brauchst. Jedes Modul funktioniert ohne die anderen; die Gate-Checks der Module brauchen `gate`, um in der CI zu laufen. In einem bestehenden Repository beginnst du mit `/sdlc:sdlc-audit`: Es braucht kein anderes Modul und nennt für jede Lücke das Modul, das sie schließt.

## Installation

```bash
claude plugin marketplace add uncovertechtalent/cto-powersuit
claude plugin install decisions@cto-powersuit
claude plugin install docs@cto-powersuit
claude plugin install gate@cto-powersuit
claude plugin install observability@cto-powersuit
claude plugin install sdlc@cto-powersuit
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

Die Plugins der Wissensinfrastruktur (`vestige`, `vault`, `stance`) sind älter als dieser Aufbau und behalten ihre eigene Struktur.

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
```

`scripts/test_checks.py` führt den Gate-Check jedes Moduls mit dem Gate-Runner gegen seine Pass- und Fail-Fixtures aus. Das Skript braucht Python 3.9+ und endet mit Exit-Code 1, wenn ein Check eine Fail-Fixture besteht oder an einer Pass-Fixture scheitert.

## Lizenz

MIT. `plugins/stance/THIRD_PARTY_NOTICES.md` listet den Code auf, der aus caveman übernommen wurde.
