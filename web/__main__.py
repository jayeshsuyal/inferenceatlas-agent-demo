"""Run: python -m web"""

import sys

import uvicorn

if __name__ == "__main__":
    try:
        import fastapi  # noqa: F401
    except ImportError:
        print(
            "Web dependencies missing. Install with:\n"
            "  pip install -r agent/requirements.txt\n"
            "  pip install fastapi 'uvicorn[standard]>=0.27.0'",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    print("InferenceAtlas web: http://127.0.0.1:8080")
    print("Skills API: GET /api/skills  (restart server after pulling skill UI changes)")
    uvicorn.run("web.app:app", host="127.0.0.1", port=8080, reload=False)
