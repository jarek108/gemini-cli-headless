"""Unit tests for the `auth_mode` parameter added to run_gemini_cli_headless.

These tests mock subprocess.Popen so they don't require a real GEMINI_API_KEY
or a working OAuth login on the host. The goal is to assert the wrapper's
behaviour at the boundary between Python and the `gemini` CLI subprocess:
argv and environment variables passed into Popen.
"""

import io
import os
import unittest
from unittest import mock

import gemini_cli_headless
from gemini_cli_headless import run_gemini_cli_headless


# Canned CLI response used by every happy-path test case. The wrapper parses
# JSON objects out of combined stdout, looking for a dict with session_id/text/response.
_CANNED_CLI_OUTPUT = '{"session_id": "unit-test-session", "text": "ok"}\n'


class _FakePopen:
    """Stand-in for subprocess.Popen that records how it was invoked."""

    # Populated by each call; the active test reads from here.
    last_instance = None

    def __init__(self, cmd, cwd=None, env=None, **kwargs):
        self.cmd = cmd
        self.cwd = cwd
        # Copy so the subprocess-level env is frozen at Popen time. Later
        # mutations of the wrapper's local `env` dict (unlikely but defensive)
        # won't leak into what the test inspects.
        self.env = dict(env) if env is not None else {}
        self.kwargs = kwargs
        self.stdout = io.StringIO(_CANNED_CLI_OUTPUT)
        self.returncode = 0
        _FakePopen.last_instance = self

    def wait(self, timeout=None):
        return 0

    def kill(self):
        pass


class AuthModeTests(unittest.TestCase):
    def setUp(self):
        # Each test runs in its own tmp cwd so the wrapper's project-root
        # discovery and tmp_dir creation don't pollute the repo.
        # `_env_patch` is the os.environ patch handle (restores the
        # caller's real env at tearDown); `_cwd` below is the actual
        # tempdir. Keep the names distinct so future readers don't
        # confuse the two.
        self._env_patch = mock.patch.dict(os.environ, {}, clear=False)
        self._env_patch.start()
        # Strip any ambient GEMINI_API_KEY the developer may have exported;
        # tests that need it will set it explicitly.
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("GEMINI_CLI_HOME", None)

        import tempfile
        self._cwd = tempfile.mkdtemp(prefix="gch_test_")

        # Patch shutil.which inside the module so the tests don't depend on
        # `gemini` being installed on the host PATH.
        self._which_patch = mock.patch.object(
            gemini_cli_headless.shutil, "which", return_value="/fake/bin/gemini"
        )
        self._which_patch.start()

        # Patch subprocess.Popen used by the module.
        self._popen_patch = mock.patch.object(
            gemini_cli_headless.subprocess, "Popen", _FakePopen
        )
        self._popen_patch.start()

        _FakePopen.last_instance = None

    def tearDown(self):
        self._popen_patch.stop()
        self._which_patch.stop()
        self._env_patch.stop()
        import shutil
        shutil.rmtree(self._cwd, ignore_errors=True)

    def _capture_logs(self):
        """Attach a list-based handler to the wrapper's logger and return
        (records_list, detach_callable). Used in place of self.assertLogs
        when the test must NOT depend on at least one record being
        emitted (assertLogs raises AssertionError on empty capture, and
        assertNoLogs is Python 3.10+ while this project targets 3.9)."""
        import logging

        captured = []

        class _ListHandler(logging.Handler):
            def emit(self, record):
                captured.append(self.format(record))

        handler = _ListHandler(level=logging.INFO)
        handler.setFormatter(
            logging.Formatter("%(levelname)s:%(name)s:%(message)s")
        )
        target_logger = logging.getLogger("gemini-cli-headless")
        target_logger.addHandler(handler)

        # Force the logger level down to INFO so the handler actually
        # receives records. Without this, a future test or conftest that
        # raises the logger level above INFO would make the negative log
        # assertions silently pass even when records *should* have been
        # captured. Save the original level and restore it on detach.
        original_level = target_logger.level
        target_logger.setLevel(logging.INFO)

        def detach():
            target_logger.removeHandler(handler)
            target_logger.setLevel(original_level)

        return captured, detach

    # ---------------- invalid / conflicting config ---------------- #

    def test_invalid_auth_mode_raises(self):
        with self.assertRaises(ValueError) as ctx:
            run_gemini_cli_headless(
                prompt="hi",
                auth_mode="invalid",
                cwd=self._cwd,
                max_retries=1,
            )
        self.assertIn("auth_mode", str(ctx.exception))
        # Regression: we must fail before ever spawning the CLI.
        self.assertIsNone(_FakePopen.last_instance)

    def test_oauth_with_api_key_raises(self):
        with self.assertRaises(ValueError) as ctx:
            run_gemini_cli_headless(
                prompt="hi",
                auth_mode="oauth",
                api_key="should-not-be-allowed",
                cwd=self._cwd,
                max_retries=1,
            )
        self.assertIn("oauth", str(ctx.exception).lower())
        self.assertIsNone(_FakePopen.last_instance)

    # ---------------- api_key mode ---------------- #

    def test_api_key_mode_missing_key_raises(self):
        """Regression guard: default behaviour (auth_mode='api_key' without a
        key in env or as kwarg) must still raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            run_gemini_cli_headless(
                prompt="hi",
                cwd=self._cwd,
                max_retries=1,
            )
        self.assertIn("GEMINI_API_KEY", str(ctx.exception))
        self.assertIsNone(_FakePopen.last_instance)

    def test_api_key_mode_env_var_is_passed_to_subprocess(self):
        os.environ["GEMINI_API_KEY"] = "env-key-xyz"
        try:
            run_gemini_cli_headless(
                prompt="hi",
                cwd=self._cwd,
                max_retries=1,
            )
        finally:
            os.environ.pop("GEMINI_API_KEY", None)

        self.assertIsNotNone(_FakePopen.last_instance)
        self.assertEqual(
            _FakePopen.last_instance.env.get("GEMINI_API_KEY"), "env-key-xyz"
        )

    def test_api_key_mode_kwarg_is_passed_to_subprocess(self):
        """Companion to test_api_key_mode_env_var_is_passed_to_subprocess,
        pinning the distinct code path where the caller passes
        `api_key="..."` as a kwarg without GEMINI_API_KEY in os.environ.
        The wrapper writes the kwarg value into the subprocess env;
        verify that plumbing end-to-end (no env-var fallback involved)."""
        # setUp already cleared GEMINI_API_KEY; don't reintroduce it.
        self.assertNotIn("GEMINI_API_KEY", os.environ)

        run_gemini_cli_headless(
            prompt="hi",
            api_key="kwarg-key",
            cwd=self._cwd,
            max_retries=1,
        )

        self.assertIsNotNone(_FakePopen.last_instance)
        self.assertEqual(
            _FakePopen.last_instance.env.get("GEMINI_API_KEY"), "kwarg-key"
        )

    def test_auth_mode_kwarg_flows_through_to_execute_single_run(self):
        """Plumbing regression guard for the public-to-internal handoff.

        Both the public `run_gemini_cli_headless` and the internal
        `_execute_single_run` default `auth_mode="api_key"`, so a
        behavioral test that only inspects subprocess env can't tell the
        difference between "wrapper forwarded auth_mode='api_key'
        correctly" and "wrapper dropped the kwarg entirely and the
        internal default filled in". Same hazard for 'oauth': if the
        forwarding line in the retry loop ever loses `auth_mode=...`,
        oauth callers would silently fall back to the api_key default
        and start raising "GEMINI_API_KEY is missing" — with no test
        pointing at the real root cause.

        Spy on the boundary itself: patch `_execute_single_run`, check
        `call_args.kwargs["auth_mode"]` for both explicit strings.
        """
        # A canned session object so the public wrapper returns
        # cleanly (no retry loop, no subprocess).
        fake_session = mock.MagicMock(name="fake_session")

        with mock.patch.object(
            gemini_cli_headless,
            "_execute_single_run",
            return_value=fake_session,
        ) as spy:
            # api_key path
            run_gemini_cli_headless(
                prompt="hi",
                auth_mode="api_key",
                cwd=self._cwd,
                max_retries=1,
            )
            self.assertEqual(spy.call_args.kwargs["auth_mode"], "api_key")

            # oauth path — same spy, second invocation
            run_gemini_cli_headless(
                prompt="hi",
                auth_mode="oauth",
                cwd=self._cwd,
                max_retries=1,
            )
            self.assertEqual(spy.call_args.kwargs["auth_mode"], "oauth")

            # Sanity: no positional auth_mode (would dodge the kwarg
            # assertion above via a future refactor).
            for call in spy.call_args_list:
                self.assertEqual(call.args, ())

    def test_api_key_mode_explicit_auth_mode_kwarg_positive_path(self):
        """Explicit auth_mode='api_key' behaves identically to default."""
        os.environ["GEMINI_API_KEY"] = "env-key-xyz"
        try:
            run_gemini_cli_headless(
                prompt="hi",
                auth_mode="api_key",
                cwd=self._cwd,
                max_retries=1,
            )
        finally:
            os.environ.pop("GEMINI_API_KEY", None)

        self.assertIsNotNone(_FakePopen.last_instance)
        self.assertEqual(
            _FakePopen.last_instance.env.get("GEMINI_API_KEY"), "env-key-xyz"
        )

    def test_api_key_mode_sets_gemini_cli_home_when_isolated(self):
        """Regression guard: in api_key mode with isolation enabled (the
        default), the subprocess env must contain GEMINI_CLI_HOME=cwd."""
        os.environ["GEMINI_API_KEY"] = "env-key-xyz"
        try:
            run_gemini_cli_headless(
                prompt="hi",
                cwd=self._cwd,
                max_retries=1,
                isolate_from_hierarchical_pollution=True,
            )
        finally:
            os.environ.pop("GEMINI_API_KEY", None)

        self.assertIsNotNone(_FakePopen.last_instance)
        env = _FakePopen.last_instance.env
        self.assertIn("GEMINI_CLI_HOME", env)
        self.assertEqual(
            os.path.realpath(env["GEMINI_CLI_HOME"]),
            os.path.realpath(self._cwd),
        )

    # ---------------- oauth mode ---------------- #

    def test_oauth_mode_without_api_key_does_not_raise(self):
        """Core feature: OAuth users shouldn't need GEMINI_API_KEY at all."""
        run_gemini_cli_headless(
            prompt="hi",
            auth_mode="oauth",
            cwd=self._cwd,
            max_retries=1,
        )
        self.assertIsNotNone(_FakePopen.last_instance)
        # And the subprocess env must not smuggle an API key in.
        self.assertNotIn("GEMINI_API_KEY", _FakePopen.last_instance.env)

    def test_oauth_mode_strips_inherited_api_key_from_subprocess(self):
        """If the caller's shell has GEMINI_API_KEY exported, the OAuth path
        must still strip it before launching the CLI — otherwise the two
        auth modes would silently mix and api-key would win."""
        os.environ["GEMINI_API_KEY"] = "inherited-key"
        try:
            run_gemini_cli_headless(
                prompt="hi",
                auth_mode="oauth",
                cwd=self._cwd,
                max_retries=1,
            )
        finally:
            os.environ.pop("GEMINI_API_KEY", None)

        self.assertIsNotNone(_FakePopen.last_instance)
        self.assertNotIn("GEMINI_API_KEY", _FakePopen.last_instance.env)

    # ---------------- oauth mode: silent-decision logging ---------------- #

    def test_oauth_mode_logs_when_stripping_inherited_gemini_cli_home(self):
        """When auth_mode='oauth' silently pops an inherited GEMINI_CLI_HOME
        from the subprocess env, the user should see a log line explaining
        that the var was stripped (otherwise OAuth cred resolution would
        break and the cause would be invisible)."""
        os.environ["GEMINI_CLI_HOME"] = "/some/inherited/home"
        try:
            with self.assertLogs("gemini-cli-headless", level="INFO") as cm:
                run_gemini_cli_headless(
                    prompt="hi",
                    auth_mode="oauth",
                    cwd=self._cwd,
                    max_retries=1,
                )
        finally:
            os.environ.pop("GEMINI_CLI_HOME", None)

        joined = "\n".join(cm.output)
        self.assertIn("stripped inherited GEMINI_CLI_HOME", joined)
        self.assertIn("/some/inherited/home", joined)
        # Pin both halves of the contract: log condition AND the actual
        # mutation at subprocess-env level. Without this, a future refactor
        # could fire the log line while leaving GEMINI_CLI_HOME in the env
        # passed to subprocess (or vice versa). Mirrors the same guard in
        # test_oauth_mode_logs_strip_for_empty_string_inherited_var.
        self.assertIsNotNone(_FakePopen.last_instance)
        self.assertNotIn("GEMINI_CLI_HOME", _FakePopen.last_instance.env)

    def test_oauth_mode_does_not_log_strip_when_no_inherited_var(self):
        """No GEMINI_CLI_HOME in the environment → no strip happened →
        no noise in the log.

        Uses _capture_logs (not self.assertLogs) so the assertion stands
        on its own: assertLogs would implicitly require at least one log
        record, which would silently rely on the co-emitted isolation-skip
        log. Removing that other log in a future refactor would then break
        this test for the wrong reason."""
        # setUp already cleared GEMINI_CLI_HOME from os.environ.
        captured, detach = self._capture_logs()
        try:
            run_gemini_cli_headless(
                prompt="hi",
                auth_mode="oauth",
                cwd=self._cwd,
                max_retries=1,
            )
        finally:
            detach()

        joined = "\n".join(captured)
        self.assertNotIn("stripped inherited GEMINI_CLI_HOME", joined)

    def test_oauth_mode_logs_skipped_isolation_override(self):
        """When isolate_from_hierarchical_pollution=True is silently
        bypassed for the GEMINI_CLI_HOME=cwd override (because oauth needs
        ~/.gemini/ resolution), the user should see exactly that explained
        in the log."""
        with self.assertLogs("gemini-cli-headless", level="INFO") as cm:
            run_gemini_cli_headless(
                prompt="hi",
                auth_mode="oauth",
                cwd=self._cwd,
                max_retries=1,
                isolate_from_hierarchical_pollution=True,
            )

        joined = "\n".join(cm.output)
        self.assertIn("skipping GEMINI_CLI_HOME", joined)
        # Path normalization: on Windows, tempfile.mkdtemp may return a
        # short-form path (e.g. C:\Users\RUNNER~1\...) while resolution
        # elsewhere can produce the long form — substring match would
        # then intermittently fail. Mirror the realpath-based pattern from
        # test_api_key_mode_sets_gemini_cli_home_when_isolated and accept
        # either form in the log.
        self.assertTrue(
            self._cwd in joined or os.path.realpath(self._cwd) in joined,
            f"expected cwd ({self._cwd!r} or its realpath) in log; got: {joined!r}",
        )
        # Without system_instruction_override the wrapper does NOT export
        # GEMINI_SYSTEM_MD, so the message must not claim that isolation
        # is active. Pin both the listed-isolation and the absent one.
        self.assertIn("GEMINI_PROJECT", joined)
        self.assertIn("tmp-dir", joined)
        self.assertNotIn("GEMINI_SYSTEM_MD", joined)

    def test_oauth_mode_skip_isolation_log_lists_system_md_when_override_set(self):
        """Companion to test_oauth_mode_logs_skipped_isolation_override: when
        the caller DOES pass system_instruction_override, the wrapper exports
        GEMINI_SYSTEM_MD, so the skip-isolation log message must list it
        among the still-active isolations. Pins the dynamic-message
        contract in both directions."""
        with self.assertLogs("gemini-cli-headless", level="INFO") as cm:
            run_gemini_cli_headless(
                prompt="hi",
                auth_mode="oauth",
                cwd=self._cwd,
                max_retries=1,
                isolate_from_hierarchical_pollution=True,
                system_instruction_override="custom system instruction",
            )

        joined = "\n".join(cm.output)
        self.assertIn("skipping GEMINI_CLI_HOME", joined)
        self.assertIn("GEMINI_PROJECT", joined)
        self.assertIn("GEMINI_SYSTEM_MD", joined)
        self.assertIn("tmp-dir", joined)

    def test_api_key_mode_does_not_emit_oauth_decision_logs(self):
        """Regression guard: in api_key mode, neither of the two
        oauth-specific decision log lines should ever be emitted, even
        when an inherited GEMINI_CLI_HOME is present (which only matters
        for the oauth path).

        Covers two invocations:
          1. default (no auth_mode kwarg) — exercises the implicit path.
          2. explicit auth_mode='api_key' — exercises the public kwarg
             plumbing, in case the default and the explicit string ever
             diverge (e.g. an alias map or normalisation step).
        """
        captured, detach = self._capture_logs()

        os.environ["GEMINI_API_KEY"] = "env-key-xyz"
        os.environ["GEMINI_CLI_HOME"] = "/some/inherited/home"
        try:
            run_gemini_cli_headless(
                prompt="hi",
                cwd=self._cwd,
                max_retries=1,
                isolate_from_hierarchical_pollution=True,
            )
            run_gemini_cli_headless(
                prompt="hi",
                auth_mode="api_key",
                cwd=self._cwd,
                max_retries=1,
                isolate_from_hierarchical_pollution=True,
            )
        finally:
            os.environ.pop("GEMINI_API_KEY", None)
            os.environ.pop("GEMINI_CLI_HOME", None)
            detach()

        joined = "\n".join(captured)
        self.assertNotIn("auth_mode='oauth'", joined)
        self.assertNotIn("stripped inherited GEMINI_CLI_HOME", joined)
        self.assertNotIn("skipping GEMINI_CLI_HOME", joined)

    def test_oauth_mode_logs_value_from_env_not_os_environ(self):
        """Regression for the env-vs-os.environ distinction in the oauth
        GEMINI_CLI_HOME pop branch
        (`inherited_cli_home = env.pop("GEMINI_CLI_HOME", None)`).

        The wrapper builds a subprocess env dict via os.environ.copy() and
        then mutates it. The 'inherited GEMINI_CLI_HOME' log line MUST
        read from that mutated env (the dict actually passed to the
        subprocess) — not from the live os.environ — otherwise any
        future refactor that sets/changes env['GEMINI_CLI_HOME'] between
        the copy and the oauth branch would log the wrong (stale) value
        or miss the strip entirely.

        We force a divergence by replacing os.environ in the wrapper's
        module with a dict subclass whose .copy() injects a sentinel
        value distinct from the one in os.environ itself. If the wrapper
        reads from os.environ we'd see 'from-os-environ' in the log; if
        it reads from env (correct) we see 'from-subprocess-env'.
        """
        class _DivergedEnviron(dict):
            def copy(self_inner):
                d = dict(self_inner)
                d["GEMINI_CLI_HOME"] = "from-subprocess-env"
                return d

        fake_environ = _DivergedEnviron(os.environ)
        fake_environ["GEMINI_CLI_HOME"] = "from-os-environ"

        with mock.patch.object(gemini_cli_headless.os, "environ", fake_environ):
            with self.assertLogs("gemini-cli-headless", level="INFO") as cm:
                run_gemini_cli_headless(
                    prompt="hi",
                    auth_mode="oauth",
                    cwd=self._cwd,
                    max_retries=1,
                )

        joined = "\n".join(cm.output)
        self.assertIn("stripped inherited GEMINI_CLI_HOME", joined)
        self.assertIn("from-subprocess-env", joined)
        self.assertNotIn("from-os-environ", joined)
        # Also lock down the combined contract: when an inherited
        # GEMINI_CLI_HOME is present AND isolate_from_hierarchical_pollution
        # is True (default), BOTH oauth decision logs must fire — the
        # strip log AND the skip-isolation log. No other test pins this
        # combination.
        self.assertIn("skipping GEMINI_CLI_HOME", joined)
        self.assertIn("isolation override", joined)
        # And — independent of what got logged — verify the strip
        # actually happened at the env-dict level. The log source could
        # be right while the dict mutation is wrong; assert both.
        self.assertIsNotNone(_FakePopen.last_instance)
        self.assertNotIn("GEMINI_CLI_HOME", _FakePopen.last_instance.env)

    def test_oauth_mode_logs_strip_for_empty_string_inherited_var(self):
        """Boundary test: GEMINI_CLI_HOME='' (empty string) is still an
        inherited value that the wrapper strips, so the strip log MUST
        fire. Pins the `is not None` check guarding the strip-log emission
        — a future truthiness refactor (e.g. `if inherited_cli_home:`)
        would silently suppress the log for empty strings, leaving users
        with no signal that env was modified."""
        os.environ["GEMINI_CLI_HOME"] = ""
        try:
            with self.assertLogs("gemini-cli-headless", level="INFO") as cm:
                run_gemini_cli_headless(
                    prompt="hi",
                    auth_mode="oauth",
                    cwd=self._cwd,
                    max_retries=1,
                )
        finally:
            os.environ.pop("GEMINI_CLI_HOME", None)

        joined = "\n".join(cm.output)
        self.assertIn("stripped inherited GEMINI_CLI_HOME", joined)
        # Pin both halves of the contract: the log condition AND the
        # actual mutation. Without this, a future refactor could fire
        # the log while leaving GEMINI_CLI_HOME='' in the subprocess
        # env (or vice versa).
        self.assertIsNotNone(_FakePopen.last_instance)
        self.assertNotIn("GEMINI_CLI_HOME", _FakePopen.last_instance.env)

    def test_oauth_mode_no_isolation_strips_but_does_not_log_skip(self):
        """Pin the contract for the `isolate_from_hierarchical_pollution=False`
        path independently from the strip path.

        The two oauth side-effects have DIFFERENT trigger conditions:
          * `env.pop("GEMINI_CLI_HOME", None)` is unconditional for oauth
            mode (independent of isolate flag) — so when an inherited
            GEMINI_CLI_HOME is present, the strip log MUST fire and the
            var must be absent from the subprocess env.
          * The `skipping GEMINI_CLI_HOME=<cwd> isolation override` log
            fires only when `isolate_from_hierarchical_pollution=True`
            (it explains the override that wasn't applied) — with
            isolate=False there is no override to skip, so this log
            must NOT fire even when an inherited var triggers the
            unconditional strip.

        Pre-setting GEMINI_CLI_HOME makes this test exercise the case
        most likely to confuse a future refactor (both branches in play
        for the same env var) and pins each log to its own trigger."""
        os.environ["GEMINI_CLI_HOME"] = "/some/inherited/home"
        try:
            with self.assertLogs("gemini-cli-headless", level="INFO") as cm:
                run_gemini_cli_headless(
                    prompt="hi",
                    auth_mode="oauth",
                    cwd=self._cwd,
                    max_retries=1,
                    isolate_from_hierarchical_pollution=False,
                )
        finally:
            os.environ.pop("GEMINI_CLI_HOME", None)

        joined = "\n".join(cm.output)
        # Strip log fires (pop is unconditional, inherited var was there).
        self.assertIn("stripped inherited GEMINI_CLI_HOME", joined)
        self.assertIn("/some/inherited/home", joined)
        # Skip-isolation log does NOT fire (isolate=False → no override
        # to skip).
        self.assertNotIn("skipping GEMINI_CLI_HOME", joined)
        # And the strip actually mutated the dict passed to subprocess.
        self.assertIsNotNone(_FakePopen.last_instance)
        self.assertNotIn("GEMINI_CLI_HOME", _FakePopen.last_instance.env)

    def test_oauth_mode_does_not_set_gemini_cli_home(self):
        """GEMINI_CLI_HOME=cwd breaks OAuth cred resolution (CLI looks under
        $GEMINI_CLI_HOME/.gemini/oauth_creds.json instead of ~/.gemini/).
        Even with isolate_from_hierarchical_pollution=True (the default),
        OAuth mode must NOT export GEMINI_CLI_HOME to the subprocess.

        We pre-set GEMINI_CLI_HOME in the caller's environment so the
        test exercises BOTH guards at once:
          * the wrapper's unconditional `env.pop("GEMINI_CLI_HOME", ...)`
            in the oauth branch (would otherwise inherit the caller's
            value via os.environ.copy()),
          * the wrapper's skip of the `env["GEMINI_CLI_HOME"] = cwd`
            isolation override (would otherwise re-add the cwd value).
        Without the pre-set, this assertion passes even if the wrapper's
        unconditional-pop line is deleted, because the setUp clears
        GEMINI_CLI_HOME. Pinning the pre-set makes the test catch that
        regression."""
        os.environ["GEMINI_CLI_HOME"] = "/tmp/fake-gch"
        try:
            run_gemini_cli_headless(
                prompt="hi",
                auth_mode="oauth",
                cwd=self._cwd,
                max_retries=1,
                isolate_from_hierarchical_pollution=True,
            )
        finally:
            os.environ.pop("GEMINI_CLI_HOME", None)

        self.assertIsNotNone(_FakePopen.last_instance)
        self.assertNotIn(
            "GEMINI_CLI_HOME", _FakePopen.last_instance.env
        )


if __name__ == "__main__":
    unittest.main()
