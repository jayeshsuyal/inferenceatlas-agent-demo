"""Google Drive file list/attach for chat."""

from agent.connector_runtime import save_session
from agent.google_drive_files import attach_drive_file, build_drive_chat_context, list_drive_files


def _demo_drive_session(sid: str) -> None:
    save_session(
        sid,
        {
            "connections": {
                "google_drive": {
                    "status": "connected",
                    "mode": "demo_session",
                    "connector_id": "google_drive",
                }
            }
        },
    )


def test_list_drive_files_demo():
    sid = "test-drive-list"
    _demo_drive_session(sid)
    out = list_drive_files(sid, kind="images")
    assert out["ok"]
    assert out["demo"]
    assert any(f["media_kind"] == "images" for f in out["files"])


def test_attach_drive_and_chat_context():
    sid = "test-drive-attach"
    _demo_drive_session(sid)
    fid = "demo-drive-brief"
    result = attach_drive_file(sid, fid)
    assert result["ok"]
    assert result["digest_chars"] > 50

    ctx, used = build_drive_chat_context(sid, [fid])
    assert used
    assert "GOOGLE DRIVE" in ctx
    assert "Decision" in ctx or "support_triage" in ctx
