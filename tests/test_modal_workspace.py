import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.app.config import Settings
from backend.app.engines import modal_remote


def test_default_workspace_is_new_account(monkeypatch):
    monkeypatch.delenv("STUDIO_MODAL_WORKSPACE", raising=False)
    monkeypatch.delenv("PVS_MODAL_WORKSPACE", raising=False)
    assert Settings().modal_workspace == "lucj76861"


def test_old_account_is_rejected_before_function_lookup(monkeypatch):
    lookup = Mock()
    workspace = SimpleNamespace(hydrate=lambda: SimpleNamespace(name="kulejean567"))
    fake_modal = SimpleNamespace(Workspace=SimpleNamespace(from_context=lambda: workspace),
                                 Function=SimpleNamespace(from_name=lookup))
    monkeypatch.setitem(sys.modules, "modal", fake_modal)
    monkeypatch.setattr(modal_remote, "get_settings", lambda: SimpleNamespace(modal_workspace="lucj76861"))
    with pytest.raises(ValueError, match="Workspace Modal inattendu"):
        modal_remote.ModalEngine("modal_ltx")._function()
    lookup.assert_not_called()
