import io
import json
import os
import pytest
from click.testing import CliRunner
from humg import Alto4Parser, Page2019Parser, run

DATA = os.path.join(os.path.dirname(__file__), "data")
ALTO = os.path.join(DATA, "sample.alto4.xml")
PAGE = os.path.join(DATA, "sample.page.xml")

# The ALTO fixture has:
#   TextBlock TYPE_1 → "MainZone"
#   TextLine  TYPE_2 → "NumberingZone"  CONTENT="Hello world"
#   TextLine  TYPE_1 → "MainZone"       CONTENT="Bonjour"
# So: lines = {"NumberingZone": 1, "MainZone": 1}
#     regions = {"MainZone": 1}
#     chars = Counter("Helloworld" + "Bonjour") = 17 chars (no spaces)


class TestAlto4Parser:
    def setup_method(self):
        self.parser = Alto4Parser()
        self.xml = self.parser.parse(ALTO)

    def test_get_lines(self):
        lines = self.parser.get_lines(self.xml)
        assert sum(lines.values()) == 2
        assert lines["NumberingZone"] == 1
        assert lines["MainZone"] == 1

    def test_get_regions(self):
        regions = self.parser.get_regions(self.xml)
        assert sum(regions.values()) == 1
        assert regions["MainZone"] == 1

    def test_get_chars(self):
        chars = self.parser.get_chars(self.xml)
        # "Hello world" → "Helloworld" (10) + "Bonjour" (7) = 17
        assert sum(chars.values()) == 17

    def test_normalization_nfd(self):
        parser_nfd = Alto4Parser(normalization="NFD")
        xml = parser_nfd.parse(ALTO)
        chars = parser_nfd.get_chars(xml)
        # NFD splits combined chars; ASCII stays same here
        assert sum(chars.values()) >= 17


class TestPage2019Parser:
    def setup_method(self):
        self.parser = Page2019Parser()
        self.xml = self.parser.parse(PAGE)

    def test_get_lines(self):
        lines = self.parser.get_lines(self.xml)
        assert sum(lines.values()) == 2
        assert lines["HeadingLine"] == 1
        assert lines["DefaultLine"] == 1

    def test_get_regions(self):
        regions = self.parser.get_regions(self.xml)
        assert sum(regions.values()) == 1
        assert regions["MainZone"] == 1

    def test_get_chars(self):
        chars = self.parser.get_chars(self.xml)
        assert sum(chars.values()) == 17

    def test_handle_custom_type(self):
        assert Page2019Parser._handle_custom_type("structure {type:MyTag ;}") == "MyTag"
        assert Page2019Parser._handle_custom_type("Not specified") == "Not specified"


class TestCLI:
    def setup_method(self):
        self.runner = CliRunner()

    def test_alto_json_output(self):
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(run, [ALTO, "--to-json", "out.json"])
            assert result.exit_code == 0, result.output
            with open("out.json") as f:
                data = json.load(f)
            assert data["volume"][0]["metric"] == "lines"
            assert data["volume"][0]["count"] == 2
            assert data["volume"][1]["metric"] == "files"
            assert data["volume"][1]["count"] == 1
            assert data["volume"][2]["metric"] == "regions"
            assert data["volume"][2]["count"] == 1
            assert data["volume"][3]["metric"] == "characters"
            assert data["volume"][3]["count"] == 17

    def test_page_json_output(self):
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(run, [PAGE, "--parse", "page", "--to-json", "out.json"])
            assert result.exit_code == 0, result.output
            with open("out.json") as f:
                data = json.load(f)
            assert data["volume"][0]["count"] == 2   # lines
            assert data["volume"][2]["count"] == 1   # regions
            assert data["volume"][3]["count"] == 17  # characters

    def test_chars_flag_adds_characters_to_json(self):
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(run, [ALTO, "--chars", "--to-json", "out.json"])
            assert result.exit_code == 0, result.output
            with open("out.json") as f:
                data = json.load(f)
            assert "characters" in data
            assert "members" in data["characters"]
