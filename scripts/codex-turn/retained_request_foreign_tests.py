"""Actual owned ctypes foreign-memory tests: no sockets, providers or models."""
import argparse
import concurrent.futures
import copy
import ctypes
import json
from pathlib import Path
import sys
import unittest
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _rust_retained_request import _RetainedRequestOwner, _HandleFault

P = Path(__file__).resolve().parent
FIELD_MAPS = json.loads((P / "retained-request-source.json").read_text())["explicit_field_maps"]
LIBRARY = None
SHA = None
BEARER = b"Bearer owned-fixture-only-not-a-real-key"
THREAD = "00000000-0000-0000-0000-000000000001"

def materials():
    model = dict.fromkeys(FIELD_MAPS["model_info"])
    model.update({
        "slug": "owned-gpt-fixture", "display_name": "owned-gpt-fixture", "description": "owned fixture",
        "default_reasoning_level": "medium", "supported_reasoning_levels": [{"effort": "medium", "description": "medium"}],
        "shell_type": "shell_command", "visibility": "list", "supported_in_api": True, "priority": 1,
        "additional_speed_tiers": [], "service_tiers": [], "include_skills_usage_instructions": False,
        "include_plugin_usage_instructions": False, "include_apps_usage_instructions": True,
        "supports_reasoning_summary_parameter": True, "default_reasoning_summary": "auto",
        "support_verbosity": False, "web_search_tool_type": "text", "truncation_policy": {"mode": "bytes", "limit": 10000},
        "supports_image_detail_original": False, "context_window": 272000,
        "effective_context_window_percent": 95, "experimental_supported_tools": [], "input_modalities": ["text", "image"],
        "used_fallback_model_metadata": False, "supports_search_tool": False, "supports_experimental_context": False,
        "use_responses_lite": False, "supports_reasoning_effort_updates": False,
        "node_repl_auto_review_required": False, "node_repl_disabled": False,
    })
    metadata = dict.fromkeys(FIELD_MAPS["responses_metadata"])
    metadata.update({"installation_id": "owned-installation", "session_id": "owned-logical-session",
                     "thread_id": THREAD, "window_id": "owned-window", "turn_id": "owned-turn",
                     "request_kind": "turn", "workspaces": {}, "extra": {}})
    return {
        "abi_version": 1, "creation_key": uuid.uuid4().hex,
        "prompt": {"input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Owned history 中文 😀 é é"}]}],
                   "tools": [], "parallel_tool_calls": False,
                   "base_instructions": {"text": "Owned genuine core instructions", "provenance": None},
                   "output_schema": None, "output_schema_strict": True, "cyber_access_program": None},
        "model_info": model, "metadata": metadata,
        "policy": {"thread_id": THREAD, "is_openai": True, "is_bedrock": False, "namespace_tools": True,
                   "reasoning_effort_override_enabled": False, "concurrent_reasoning_summaries_enabled": False,
                   "model_verbosity": None, "prompt_cache_key": "owned-cache-affinity"},
        "provider": {"name": "owned-memory-fixture", "base_url": "https://example.com/v1", "query_params": None,
                     "headers": [], "retry": {"max_attempts": 1, "base_delay_ms": 1, "retry_429": False, "retry_5xx": False, "retry_transport": False},
                     "stream_idle_timeout_ms": 2000},
        "http_facts": {"responses_session_id": "owned-cache-affinity", "thread_id": THREAD, "session_source": "cli",
                       "beta": None, "sticky_turn_state": None, "originator": "owned-originator",
                       "compatibility_headers": [], "attestation_requirement": "not_required", "attestation": None,
                       "guardian_credits": "not_requested", "access_programs": None, "routing_hint": None,
                       "responses_headers": [], "content_item_kinds_enabled": False,
                       "expected_contributors": 0, "contributions": [], "trace_requirement": "not_required", "trace_header": None},
        "maximum": 64, "effort": None, "summary": "none", "service_tier": None, "include_internal": False,
        "timeout_ms": 750, "response_body_limit_bytes": 4096, "auth_mode": "static_api_key_bearer",
    }

class ForeignRetainedRequest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.owner = _RetainedRequestOwner(Path(LIBRARY), SHA)

    def rejection(self, value, bearer=BEARER, code=3):
        with self.assertRaises(_HandleFault) as ctx:
            self.owner.create(value, bearer)
        self.assertEqual(ctx.exception.code, code)

    def test_genuine_foreign_core_encoding_freeze_and_allocation(self):
        value = materials()
        request = self.owner.create(value, BEARER)
        info = request.borrow_state()
        self.assertTrue(info.encoded_frozen_same)
        self.assertTrue(info.cloned_body_same)
        self.assertTrue(info.auth_sensitive)
        body = request._copy_body_for_owned_verification()
        self.assertEqual(info.body_bytes, len(body))
        actual = json.loads(body)
        self.assertEqual(actual["max_output_tokens"], 64)
        self.assertEqual(actual["truncation"], "disabled")
        self.assertEqual(actual["instructions"], value["prompt"]["base_instructions"]["text"])
        self.assertEqual(actual["input"][0]["content"][0]["text"], value["prompt"]["input"][0]["content"][0]["text"])
        self.assertEqual(actual["model"], value["model_info"]["slug"])
        self.assertNotIn(BEARER, body)
        request.release()

    def test_clone_retains_same_allocation_after_original_release(self):
        request = self.owner.create(materials(), BEARER)
        clone = request.clone()
        body = request._copy_body_for_owned_verification()
        self.assertEqual(request.borrow_state(), clone.borrow_state())
        request.release()
        self.assertEqual(clone._copy_body_for_owned_verification(), body)
        self.assertTrue(clone.borrow_state().encoded_frozen_same)
        clone.release()

    def test_actual_double_release_unknown_and_use_after_release_are_rejected(self):
        request = self.owner.create(materials(), BEARER)
        request.release()
        for operation in [request.release, request.borrow_state, request.clone, request._copy_body_for_owned_verification]:
            with self.subTest(operation=operation.__name__), self.assertRaises(_HandleFault) as ctx:
                operation()
            self.assertEqual(ctx.exception.code, 1)
        self.assertEqual(self.owner._library.m63_request_release(2**64-1), 1)

    def test_creation_identity_cannot_reset_after_release_or_new_owner(self):
        value = materials()
        request = self.owner.create(value, BEARER)
        request.release()
        self.rejection(value, code=2)
        another = _RetainedRequestOwner(Path(LIBRARY), SHA)
        with self.assertRaises(_HandleFault) as ctx:
            another.create(value, BEARER)
        self.assertEqual(ctx.exception.code, 2)

    def test_concurrent_foreign_duplicate_construct_has_one_owner(self):
        value = materials()
        def create():
            try:
                return self.owner.create(copy.deepcopy(value), BEARER)
            except _HandleFault as fault:
                return fault.code
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: create(), range(8)))
        winners = [r for r in results if not isinstance(r, int)]
        self.assertEqual(len(winners), 1)
        self.assertEqual([r for r in results if isinstance(r, int)], [2]*7)
        winners[0].release()

    def test_concurrent_clones_share_one_retained_frozen_body(self):
        request = self.owner.create(materials(), BEARER)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            clones = list(pool.map(lambda _: request.clone(), range(8)))
        expected = request.borrow_state()
        self.assertTrue(all(c.borrow_state() == expected for c in clones))
        request.release()
        for clone in clones:
            self.assertTrue(clone.borrow_state().cloned_body_same)
            clone.release()

    def test_checked_null_foreign_buffers_fail_without_dereference(self):
        output = ctypes.c_uint64()
        fn = self.owner._library.m63_request_create
        self.assertEqual(fn(None, 0, None, 0, ctypes.byref(output)), 1)
        self.assertEqual(self.owner._library.m63_request_info(1, None), 1)
        self.assertEqual(self.owner._library.m63_request_clone(1, None), 1)

    def test_borrow_copy_requires_an_owned_sufficient_bounded_buffer(self):
        request = self.owner.create(materials(), BEARER)
        with self.assertRaises(_HandleFault) as ctx:
            request._copy_body_for_owned_verification(1)
        self.assertEqual(ctx.exception.code, 1)
        for cap in [0, 1048577]:
            with self.assertRaises(ValueError):
                request._copy_body_for_owned_verification(cap)
        self.assertTrue(request.borrow_state().encoded_frozen_same)
        request.release()

    def test_missing_defaulted_model_fact_is_unknown_and_rejected(self):
        value = materials()
        del value["model_info"]["supports_reasoning_summary_parameter"]
        self.rejection(value)

    def test_missing_optional_header_fact_is_unknown_and_rejected(self):
        value = materials()
        del value["http_facts"]["trace_header"]
        self.rejection(value)

    def test_nonempty_unsupported_tool_cyber_and_complex_metadata_rejected(self):
        for section, name, content in [("prompt", "tools", [{"type":"function","name":"unsupported"}]),
                                       ("prompt", "cyber_access_program", {"name":"unsupported"}),
                                       ("metadata", "mcp_attribution", {}),
                                       ("metadata", "workspaces", {"unsupported":{}}),
                                       ("http_facts", "access_programs", {})]:
            with self.subTest(section=section, field=name):
                value = materials()
                value[section][name] = content
                self.rejection(value)

    def test_unknown_session_source_is_not_a_resolved_root_default(self):
        for source in ["unknown", "unrecognized_source_kind"]:
            with self.subTest(source=source):
                value = materials()
                value["http_facts"]["session_source"] = source
                self.rejection(value)

    def test_duplicate_foreign_json_names_rejected_before_construction(self):
        carrier = json.dumps(materials()).encode()
        duplicate = b'{"abi_version":1,' + carrier[1:]
        with self.assertRaises(_HandleFault) as ctx:
            self.owner._create_carrier_for_owned_test(duplicate, BEARER)
        self.assertEqual(ctx.exception.code, 3)

    def test_nonstatic_or_malformed_auth_never_produces_a_handle(self):
        for auth in [b"Basic fixture", b"Bearer ", b"Bearer x y", b"Bearer x\r\nCookie: x"]:
            with self.subTest(auth_class=len(auth)):
                self.rejection(materials(), bearer=auth)
        value = materials()
        value["auth_mode"] = "refreshing"
        self.rejection(value)

    def test_zero_output_non_https_and_framing_material_rejected(self):
        value = materials()
        value["maximum"] = 0
        self.rejection(value)
        value = materials()
        value["provider"]["base_url"] = "http://example.com/v1"
        self.rejection(value)
        for name in ["host", "content-length", "transfer-encoding", "cookie", "proxy-authorization", "authorization"]:
            value = materials()
            value["provider"]["headers"] = [[name,"1"]]
            self.rejection(value)

    def test_failed_final_auth_cannot_reconstruct_same_creation_identity(self):
        value = materials()
        self.rejection(value, bearer=b"Bearer ")
        self.rejection(value, code=2)

    def test_mutating_python_material_after_foreign_creation_cannot_change_body(self):
        value = materials()
        request = self.owner.create(value, BEARER)
        before = request._copy_body_for_owned_verification()
        value["prompt"]["base_instructions"]["text"] = "late Python mutation"
        value["maximum"] = 999
        self.assertEqual(request._copy_body_for_owned_verification(), before)
        request.release()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    LIBRARY, SHA = args.library, args.sha256
    unittest.main(argv=[sys.argv[0]], verbosity=2)
