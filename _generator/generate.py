import io
import sys
import argparse
from pathlib import Path

from ruamel import yaml
from dataclasses import dataclass

from typing import NewType, Union, Sequence, IO, List, Optional
import jinja2

from bs4 import BeautifulSoup
import weasyprint


@dataclass(frozen=True)
class Checkpoint:
    call: str
    response: str


Note = NewType("Note", str)

Item = Union[Checkpoint, Note]


@dataclass(frozen=True)
class Checklist:
    title: str
    items: Sequence[Item]
    audience: Optional[str] = None
    normal: bool = True
    order: int = 0


def load_checklist(f: IO[bytes]) -> Checklist:
    yaml_data = yaml.safe_load(f)

    title = yaml_data["title"]
    audience = yaml_data.get("audience", None)

    items: List[Item] = []

    for item in yaml_data["items"]:
        if isinstance(item, str):
            items.append(Note(item))
        else:
            call, response = item
            items.append(Checkpoint(call, response))

    is_normal = bool(yaml_data.get("normal", True))
    order = int(yaml_data.get("order", 0))

    return Checklist(
        title=title,
        audience=audience,
        items=items,
        normal=is_normal,
        order=order,
    )


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a checklist",
    )
    parser.add_argument(
        "checklist",
        type=Path,
        help="Path to the checklist directories to generate",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Path to the output file",
    )
    parser.add_argument(
        "--pdf",
        dest="format",
        action="store_const",
        const="pdf",
        default="pdf",
        help="Output as a PDF",
    )
    parser.add_argument(
        "--html",
        dest="format",
        action="store_const",
        const="html",
        help="Output as HTML",
    )
    parser.add_argument(
        "--txt",
        dest="format",
        action="store_const",
        const="txt",
        help="Output as a plain text file",
    )
    parser.add_argument(
        "--a5",
        dest="size",
        action="store_const",
        const="a5",
        default="a4",
        help="Output as A5 paper",
    )
    parser.add_argument(
        "--a4",
        dest="size",
        action="store_const",
        const="a4",
        help="Output as A4 paper",
    )
    parser.add_argument(
        "--title",
        type=str,
        help="Title to use for the document",
        default="Student Robotics QRH",
    )
    parser.add_argument(
        "--beautify",
        action="store_true",
        dest="beautify",
        default=True,
        help="Beautify the output",
    )
    parser.add_argument(
        "--no-beautify",
        action="store_false",
        dest="beautify",
        help="Don't beautify the output",
    )
    return parser


TEMPLATES_BY_FORMAT = {
    "pdf": "template.html",
    "html": "template.html",
    "txt": "template.txt",
}


def beautify_noop(source: str) -> str:
    return source


def beautify_html(source: str) -> str:
    soup = BeautifulSoup(source, "html.parser")
    return soup.prettify()


BEAUTIFIERS_BY_FORMAT = {
    "pdf": beautify_html,
    "html": beautify_html,
    "txt": beautify_noop,
}


def process_pdf(source: str, size: str) -> bytes:
    weasy_html = weasyprint.HTML(string=source)
    buffer = io.BytesIO()
    weasy_html.write_pdf(buffer)
    return buffer.getvalue()


def process_utf8(source: str, size: str) -> bytes:
    return source.encode("utf-8")


POSTPROCESSORS_BY_FORMAT = {
    "pdf": process_pdf,
    "html": process_utf8,
    "txt": process_utf8,
}


def main():
    parser = argument_parser()
    args = parser.parse_args()

    root_path: Path = args.checklist
    checklists: List[Checklist] = []

    for path in root_path.glob("**/*.yaml"):
        with path.open() as f:
            checklists.append(load_checklist(f))

    # Order: normal then non-normal, then follow explicit order
    checklists.sort(key=lambda x: (not x.normal, x.order, x.title))

    template_name = TEMPLATES_BY_FORMAT[args.format]

    jinja_environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(Path(__file__).parent),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
    )

    template = jinja_environment.get_template(template_name)

    rendered_template = template.render(
        title=args.title,
        checklists=checklists,
        page_size=args.size,
    )

    if args.beautify:
        rendered_template = BEAUTIFIERS_BY_FORMAT[args.format](rendered_template)

    output = POSTPROCESSORS_BY_FORMAT[args.format](rendered_template, args.size)

    if args.output:
        with args.output.open("wb") as f:
            f.write(output)
    else:
        sys.stdout.buffer.write(output)


if __name__ == "__main__":
    main()
