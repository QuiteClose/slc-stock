import importlib
from unittest.mock import patch


class TestPrefetchYearsParsing:
    def test_invalid_prefetch_years_falls_back_to_default(self):
        """Issue 6: non-integer PREFETCH_YEARS should fall back to 3."""
        with patch.dict("os.environ", {"PREFETCH_YEARS": "abc"}):
            import slc_stock.config as cfg
            importlib.reload(cfg)
            assert cfg.PREFETCH_YEARS == 3

    def test_valid_prefetch_years_parsed(self):
        with patch.dict("os.environ", {"PREFETCH_YEARS": "5"}):
            import slc_stock.config as cfg
            importlib.reload(cfg)
            assert cfg.PREFETCH_YEARS == 5

    def test_empty_prefetch_years_falls_back(self):
        with patch.dict("os.environ", {"PREFETCH_YEARS": ""}):
            import slc_stock.config as cfg
            importlib.reload(cfg)
            assert cfg.PREFETCH_YEARS == 3
