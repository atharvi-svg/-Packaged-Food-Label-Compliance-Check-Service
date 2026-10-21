"""Command-line entry point for the sample workflow."""

import argparse
import json

from food_label_compliance.audit_report import build_audit_report
from food_label_compliance.workflow import (
    run_sample,
    run_source_of_protein_sample,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a fictional mock-data food-label workflow sample."
    )
    parser.add_argument(
        "--sample",
        choices=("default", "source-of-protein"),
        default="default",
        help="Choose the default label or the source-of-protein test label.",
    )
    args = parser.parse_args()
    workflow_result = (
        run_source_of_protein_sample()
        if args.sample == "source-of-protein"
        else run_sample()
    )
    print(
        json.dumps(
            build_audit_report(workflow_result),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
