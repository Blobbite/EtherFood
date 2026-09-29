"""Create a file report through the studio tool SDK without modifying the input."""

import json

from helper import describe


def run(context, inputs, parameters):
    output = context.artifact("report.json", "json")
    output.path.write_text(
        json.dumps(describe(inputs["image"].path), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    context.log("Dateibericht erstellt.")
    return {"report": output}
