"""Explicit connection and exact stack ownership boundaries."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase34_portainer import Portainer


class PortainerTests(unittest.TestCase):
    def config(self, **extra):
        return {
            "PHASE34_PORTAINER_URL": "https://portainer.example.test",
            "PHASE34_PORTAINER_API_KEY": "generated-test-key",
            "PHASE34_PORTAINER_ENDPOINT_ID": "1",
            **extra,
        }

    def test_missing_explicit_connection_fails_before_network(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "phase34_portainer.http.client.HTTPSConnection"
        ) as request:
            with self.assertRaisesRegex(RuntimeError, "explicit approved"):
                Portainer()
            request.assert_not_called()

    def test_remote_plaintext_credentials_are_refused(self):
        with patch.dict(
            os.environ,
            self.config(PHASE34_PORTAINER_URL="http://remote.example.test"),
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "explicit approved"):
                Portainer()

    def test_different_engine_is_refused(self):
        with patch.dict(os.environ, self.config(), clear=True):
            client = Portainer()
        client.call = Mock(return_value={"ID": "foreign-engine"})
        run = Mock()
        run.command.return_value.stdout = "approved-local-engine"
        with self.assertRaisesRegex(RuntimeError, "differs"):
            client.verify_engine(run)

    def test_stack_cleanup_requires_exact_identity(self):
        with patch.dict(os.environ, self.config(), clear=True):
            client = Portainer()
        client.call = Mock(return_value={"Name": "foreign-stack", "EndpointId": 1})
        with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
            client.delete(5, "pgdp34-" + "a" * 32 + "-production")
        self.assertEqual(client.call.call_count, 1)


if __name__ == "__main__":
    unittest.main()
