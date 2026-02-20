import json
import os
import tempfile

from click.testing import CliRunner

from slc_stock.cli import cli


class TestDumpLoadRoundTrip:
    def test_dump_and_load(self):
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            dump_path = f.name

        try:
            result = runner.invoke(cli, ["dump", "--output", dump_path])
            assert result.exit_code == 0
            assert "Dumped" in result.output

            with open(dump_path) as f:
                data = json.load(f)
            assert isinstance(data, list)

            result = runner.invoke(cli, ["load", dump_path])
            assert result.exit_code == 0
            assert "Loaded" in result.output
        finally:
            os.unlink(dump_path)


class TestProvidersCommand:
    def test_providers_list(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["providers"])
        assert result.exit_code == 0
        assert "mock" in result.output
