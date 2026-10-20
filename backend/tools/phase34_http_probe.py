"""Real HTTP privacy checks against known existing test-owned files."""

import argparse
import hashlib
import http.client
import json
import time
from pathlib import Path
from urllib.parse import urlsplit

from phase34_target_guard import validate_target


def response(url, method, headers):
    target = urlsplit(url)
    if (
        target.scheme != "http"
        or target.hostname != "phase34-http"
        or target.port != 8080
        or target.username
        or target.password
    ):
        raise RuntimeError("HTTP proof target is outside the isolated service")
    connection = http.client.HTTPConnection("phase34-http", 8080, timeout=5)
    try:
        path = target.path + ("?" + target.query if target.query else "")
        connection.request(method, path, headers=headers)
        result = connection.getresponse()
        return result.status, dict(result.getheaders()), result.read(1024 * 1024)
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--after-restart", action="store_true")
    parser.add_argument("--after-crash", action="store_true")
    args = parser.parse_args()
    validate_target()
    root = Path("/phase34/owned/resources")
    evidence = Path("/phase34/evidence")
    manifest = json.loads((evidence / "http-files.json").read_text())
    deadline = time.monotonic() + 50
    rows = []
    base = "http://phase34-http:8080/assets/romm/resources/"
    for private in (True, False):
        for relative in manifest["private" if private else "positive"]:
            path = root / relative
            assert path.exists(), "negative HTTP request must address existing bytes"
            variants = [relative, relative + "?phase34=1"]
            if private:
                variants.extend(
                    [relative.replace(".", "%2e"), "normalize/../" + relative]
                )
            for variant in variants:
                for method, headers in (
                    ("GET", {}),
                    ("HEAD", {}),
                    ("GET", {"Range": "bytes=0-7"}),
                ):
                    assert time.monotonic() < deadline, "HTTP scenario deadline"
                    status, result_headers, body = response(
                        base + variant, method, headers
                    )
                    if private:
                        assert status == 404, (relative, method, status)
                        assert result_headers.get("Cache-Control") == "no-store"
                        assert b"private-sentinel" not in body
                    else:
                        assert status == (206 if headers else 200), (
                            relative,
                            method,
                            status,
                        )
                        if method != "HEAD":
                            expected = path.read_bytes()
                            assert body == (expected[:8] if headers else expected)
                    rows.append(
                        {
                            "path": variant,
                            "method": method,
                            "range": bool(headers),
                            "status": status,
                            "on_disk": True,
                            "body_sha256": hashlib.sha256(body).hexdigest(),
                        }
                    )
    name = (
        "http-after-restart.json"
        if args.after_restart
        else "http-after-crash.json" if args.after_crash else "http-live.json"
    )
    (evidence / name).write_text(json.dumps(rows, indent=2))
    print("PASS existing-private denial and committed-resource controls:", len(rows))


if __name__ == "__main__":
    main()
