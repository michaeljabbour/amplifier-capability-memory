"""Required scope identifiers must be valid before opening any native log."""
import contextlib
import io
import unittest
from unittest.mock import patch
from amplifier_module_tool_memory import evidence_cli


class EvidenceCliScopeTests(unittest.TestCase):
    def test_blank_required_wing_does_not_open_a_store(self):
        for wing in ("", " ", "\t\n"):
            for operation, arguments in (("search", ["--query", "fictional"]), ("export", []), ("remember", ["--room", "decisions", "--content", "fictional"])):
                with self.subTest(wing=repr(wing), operation=operation), patch.object(evidence_cli, "NativeMemoryStore") as store:
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as stopped:
                        evidence_cli.main(["--store", "fictional-new.log", operation, "--wing", wing, *arguments])
                    self.assertEqual(stopped.exception.code, 2)
                    store.assert_not_called()

    def test_supplied_blank_room_does_not_open_a_store(self):
        for room in ("", "  ", "\t"):
            with self.subTest(room=repr(room)), patch.object(evidence_cli, "NativeMemoryStore") as store:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    evidence_cli.main(["--store", "fictional-new.log", "search", "--wing", "project", "--room", room, "--query", "fictional"])
                store.assert_not_called()

    def test_explicit_nonblank_scope_identifiers_are_preserved(self):
        with patch.object(evidence_cli, "NativeMemoryStore") as constructor, contextlib.redirect_stdout(io.StringIO()):
            constructor.return_value.search.return_value = []
            self.assertEqual(evidence_cli.main(["--store", "fictional-new.log", "search", "--wing", "Projet élève", "--room", "room one", "--query", "fictional"]), 0)
            self.assertEqual(constructor.return_value.search.call_args.kwargs["wing"], "Projet élève")
            self.assertEqual(constructor.return_value.search.call_args.kwargs["room"], "room one")
            constructor.return_value.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
