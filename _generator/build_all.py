import argparse

from pathlib import Path
from ruamel import yaml

import subprocess
import jinja2
import sys
from bs4 import BeautifulSoup

def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the checklists website",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Path to the output directory",
        default=Path("site"),
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to the config file",
        default=Path("on-site.yaml"),
    )
    return parser


def run_build(checklist_path: str, site_dir: Path, title: str) -> str:
    checklist_subpath = f"checklists/{checklist_path}.pdf"
    target_path = site_dir / checklist_subpath
    # Add the parent directory
    target_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Building {checklist_path} to {target_path}", file=sys.stderr)
    subprocess.check_call([
        "python",
        "_generator/generate.py",
        checklist_path,
        "--pdf",
        "--output",
        str(target_path),
        "--title",
        title,
    ])
    return checklist_subpath


def build_group(site_dir: Path, checklists):
    checklist_entries = []

    for checklist in checklists:
        name = checklist["name"]
        path = checklist["path"]

        subpath = run_build(path, site_dir, name)

        checklist_entries.append((name, subpath))

    return checklist_entries


def main():
    parser = argument_parser()
    args = parser.parse_args()

    with open(args.config) as config_file:
        config = yaml.safe_load(config_file)

    args.output.mkdir(parents=True, exist_ok=True)

    (args.output / "checklists").mkdir(parents=False, exist_ok=True)

    groups = []

    for group in config["groups"]:
        groups.append((group["name"], build_group(args.output, group["checklists"])))

    with open("_generator/index_template.html") as template_file:
        template = jinja2.Template(template_file.read())

    with open(args.output / "index.html", "w") as index_file:
        output = template.render(groups=groups)
        output_beautified = BeautifulSoup(output, "html.parser").prettify()
        index_file.write(output_beautified)


if __name__ == "__main__":
    main()