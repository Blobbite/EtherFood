# Markdown-Abnahmefixtures M01–M25

[contracts.json](contracts.json) enthält pro Prüffall den genauen Markdown-Text
(`source`) und das erwartete Ergebnis (`expected`). CRLF ist als `\r\n` notiert.
Die Fixtures sind synthetisch; Bilddateien entstehen nur in temporären Projekten.

Die automatisierten Prüfungen stehen in
[Syntax und Pfade](../../test_markdown_contract.py),
[Netzwerk](../../test_markdown_network.py) und
[echte Qt-Bedienung](../../gui/test_markdown_contract_ui.py).
Für Interaktionen werden Dokumente, Anhänge, Bilder und lokale Server passend
zum Szenario ergänzt. Der Platzhalter `PORT` gehört ausschließlich zum Testserver.
`example.org` in M11 wird ausdrücklich **nicht** abgerufen.

Ein Fixture-Renderlauf allein nimmt weder die Animation noch Undo, Speichern,
Zugriffsregeln oder Pipeline-Regressionen ab. Diese Ergebnisse werden durch die
zugehörigen Verhaltensprüfungen und im Arbeitsplan getrennt ausgewiesen.
