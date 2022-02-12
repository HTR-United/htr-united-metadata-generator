import os
import json
import click
from lxml import etree
from collections import Counter, defaultdict
from typing import Dict, Counter as CounterType, List, Tuple
from tabulate import tabulate

UNKNOWN_SEGMENT_TYPE = "Not specified"


class Parser:
    def __init__(self):
        self.lines: Dict[str, int] = Counter()
        self.chars: Dict[str, int] = Counter()
        self.regions: Dict[str, int] = Counter()

    def get_lines(self, xml: etree.ElementTree) -> Dict[str, int]:
        raise NotImplementedError

    def get_chars(self, xml: etree.ElementTree) -> Dict[str, int]:
        raise NotImplementedError

    def get_regions(self, xml: etree.ElementTree) -> Dict[str, int]:
        raise NotImplementedError

    def parse(self, filepath: str) -> etree.ElementTree:
        raise NotImplementedError


class Alto4Parser(Parser):
    def __init__(self):
        super(Alto4Parser, self).__init__()
        self._ns = {"a": "http://www.loc.gov/standards/alto/ns-v4#"}
        self._labels: Dict[str, str] = {}

    def parse(self, filepath: str) -> etree.ElementTree:
        xml = etree.parse(filepath)
        self._labels = {
            node.attrib["ID"]: node.attrib["LABEL"]
            for node in xml.xpath("//a:OtherTag", namespaces=self._ns)
        }
        return xml

    def get_lines(self, xml: etree.ElementTree) -> CounterType[str]:
        return Counter([
            self._labels.get(line.attrib.get("TAGREFS", "####"), UNKNOWN_SEGMENT_TYPE)
            for line in xml.xpath("//a:TextLine", namespaces=self._ns)
        ])

    def get_chars(self, xml: etree.ElementTree) -> CounterType[str]:
        return Counter("".join([
            str(line)
            for line in xml.xpath("//a:TextLine/a:String/@CONTENT", namespaces=self._ns)
        ]).replace(" ", ""))

    def get_regions(self, xml: etree.ElementTree) -> CounterType[str]:
        return Counter([
            self._labels.get(line.attrib.get("TAGREFS", "####"), UNKNOWN_SEGMENT_TYPE)
            for line in xml.xpath("//a:TextBlock", namespaces=self._ns)
        ])


class Page2019Parser(Parser):
    def __init__(self):
        super(Page2019Parser, self).__init__()
        self._ns = {"p": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15"}
        self._labels: Dict[str, str] = {}

    def parse(self, filepath: str) -> etree.ElementTree:
        # TODO: There's no equivalent to alto's //OtherTag in PAGEXML
        xml = etree.parse(filepath)
        return xml

    def get_lines(self, xml: etree.ElementTree) -> CounterType[str]:
        return Counter([
            self._handle_custom_type(line.attrib.get("custom", UNKNOWN_SEGMENT_TYPE))
            for line in xml.xpath("//p:TextLine", namespaces=self._ns)
        ])

    def get_chars(self, xml: etree.ElementTree) -> CounterType[str]:
        return Counter("".join([
            str(line.text)
            for line in xml.xpath("//p:TextLine/p:TextEquiv/p:Unicode", namespaces=self._ns)
        ]).replace(" ", ""))

    def get_regions(self, xml: etree.ElementTree) -> CounterType[str]:
        return Counter([
            self._handle_custom_type(line.attrib.get("custom", UNKNOWN_SEGMENT_TYPE))
            for line in xml.xpath("//p:TextRegion", namespaces=self._ns)
        ])

    @staticmethod
    def _handle_custom_type(value: str) -> str:
        # there's no equivalent to TAGREFS in PAGEXML
        # eScriptorium stores this info in @custom with value formed such as:
        # custom="structure {type:MYTAG ;}"
        return value.replace("structure {type:", "").replace(";}", "").strip()


def sort_counter(counter: CounterType[str], item_place: int = 1) -> List[Tuple[str, int]]:
    return sorted(list(counter.items()), key=lambda x: x[item_place], reverse=True)


def print_counter(counter: CounterType[str], category: str) -> None:
    print(tabulate(
        [*sort_counter(counter), ("-----", "-----"), ("All", sum(counter.values()))],
        headers=[category, "Count"],
        tablefmt="pipe"
    ))


def show_title(title):
    click.echo("#" * int(len(title) * 1.5))
    click.secho("#  " + title, color=True, fg="yellow")
    click.echo("#" * int(len(title) * 1.5))
    click.echo()


def print_counter_group(counters: Dict[str, CounterType[str]], category: str) -> None:
    table = []
    total = 0
    for directory, counter in counters.items():
        cnter = sort_counter(counter, 0)  # We sort per category here
        for idx, (key, cnt) in enumerate(cnter):
            if idx == 0:
                table.append((directory, key, cnt))
            else:
                table.append(("", key, cnt))
        total += sum(counter.values())
    table.append(["-----", "-----", "-----"])
    table.append(["All", "All", total])
    print(tabulate(
        table,
        headers=["Directory", category, "Count"],
        tablefmt="pipe"
    ))


def separator():
    print("\n\n")


@click.command()
@click.argument("files", nargs=-1)
@click.option("-c", "--chars", default=False, is_flag=True, help="Show chars")
@click.option("-g", "--group", default=False, is_flag=True, help="Group by directory for logs")
@click.option("--parse", type=click.Choice(["alto", "page"]), default="alto")
@click.option("--github-envs", default=False, is_flag=True)
@click.option("--to-json)", type=click.File("w"), default=False, is_flag=True)
def run(files, chars: bool = False, group: bool = False, parse: str = "alto", github_envs: bool = False,
        to_json = None):
    parser: Parser = None
    if parse == "alto":
        parser = Alto4Parser()
    elif parse == "page":
        parser = Page2019Parser()

    total_chars = Counter()
    total_lines = Counter()
    total_regns = Counter()

    if group:
        group_chars = defaultdict(Counter)
        group_lines = defaultdict(Counter)
        group_regns = defaultdict(Counter)

    for file_name in files:
        xml = parser.parse(file_name)
        l, c, r = parser.get_lines(xml), parser.get_chars(xml), parser.get_regions(xml)
        # Update groups
        if group:
            dirname = os.path.dirname(file_name)
            group_chars[dirname].update(c)
            group_lines[dirname].update(l)
            group_regns[dirname].update(r)

        # Update global
        total_chars.update(c)
        total_lines.update(l)
        total_regns.update(r)

    show_title("Lines (All)")
    print_counter(total_lines, "Line type")
    separator()

    show_title("Regions (All)")
    print_counter(total_regns, "Region type")
    separator()

    if chars:
        show_title("Characters (All)")
        print_counter(total_chars, "Characters type")
        separator()

    if group:
        show_title("Lines (Directory)")
        print_counter_group(group_lines, "Line type")
        separator()
        show_title("Regions (Directory)")
        print_counter_group(group_regns, "Region type")
        separator()

    show_title("Yaml Cataloging Details for HTR United")
    click.secho("""volume:
    - {count: """ + str(sum(total_lines.values())) + """, metric: "lines"}
    - {count: """ + str(len(files)) + """, metric: "files"}
    - {count: """ + str(sum(total_regns.values())) + """, metric: "regions"}
    - {count: """ + str(sum(total_chars.values())) + """, metric: "characters"}""", color=True, fg="blue")

    if github_envs:
        with open("envs.txt", "w") as f:
            f.write(f"HTRUNITED_LINES={str(sum(total_lines.values()))}\n")
            f.write(f"HTRUNITED_REGNS={str(sum(total_regns.values()))}\n")
            f.write(f"HTRUNITED_CHARS={str(sum(total_chars.values()))}\n")
            f.write(f"HTRUNITED_FILES={len(files)}\n")
    if to_json is not None:
        json.dump(
            {"lines": str(sum(total_lines.values())),
             "files": str(len(files)),
             "regions": str(sum(total_regns.values())),
             "characters": str(sum(total_chars.values()))},
            to_json
        )


if __name__ == "__main__":
    run()
