"""Web file registry and mind API smoke tests."""

import unittest

from web.files_io import load_upload, register_download, resolve_download, save_output, save_upload


class WebFilesTests(unittest.TestCase):
    def test_upload_load_roundtrip(self) -> None:
        scope = "test_scope"
        file_id, name, _ = save_upload(
            scope=scope,
            filename="note.txt",
            data=b"hello evidence",
        )
        loaded = load_upload(scope, file_id)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded[0], name)
        self.assertIn("hello", loaded[1])

    def test_register_download(self) -> None:
        path = save_output(scope="test_dl", filename="x.md", content="# hi", use_timestamp=False)
        file_id = register_download(path, label="Hi")
        resolved = resolve_download(file_id)
        self.assertIsNotNone(resolved)
        assert resolved is not None
        self.assertTrue(resolved[0].is_file())

    def test_mind_init_and_step_handlers(self) -> None:
        from web.app import mind_init, mind_step

        init_data = mind_init()
        self.assertTrue(init_data.get("cycle_results"))
        self.assertEqual(len(init_data["minds"]), 3)
        step_data = mind_step(type("B", (), {"scenario": None, "no_cortex": False})())
        self.assertTrue(step_data.get("cycle_results"))
        self.assertGreaterEqual(len(step_data["cycle_results"]), 3)
        arts = step_data["cycle_results"][0]["live"]["artifacts"]
        self.assertTrue(any(a.get("file_id") for a in arts))


if __name__ == "__main__":
    unittest.main()
