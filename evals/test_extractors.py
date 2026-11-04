"""CLI regressions for material inventory and first-pass endpoint discovery."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
INVENTORY = REPO / "skills/miniapp-recon/scripts/inventory.py"
EXTRACTOR = REPO / "skills/miniapp-static-audit/scripts/extract_endpoints.py"


class ExtractorCLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "miniapp"
        self.root.mkdir()

    def put(self, relative, content=""):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def config(self, value, raw=False):
        return self.put("app-config.json" if raw else "app.json", json.dumps(value))

    def source_page(self, page):
        self.put(page + ".js")
        self.put(page + ".wxml")

    def invoke(self, script, *arguments, expected=0):
        process = subprocess.run(
            [sys.executable, str(script), "--root", str(self.root), *arguments],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(process.returncode, expected, process.stderr)
        return process

    def inventory(self, *arguments, expected=0):
        return json.loads(self.invoke(INVENTORY, *arguments, expected=expected).stdout)

    def surface(self, *arguments):
        return json.loads(self.invoke(EXTRACTOR, *arguments).stdout)

    def test_source_layout_counts_and_checks_every_declared_subpackage_page(self):
        self.config({
            "pages": ["pages/home/index"],
            "subPackages": [{"root": "shop", "pages": ["list/index", "order/index"]}],
        })
        self.put("app.js")
        self.source_page("pages/home/index")
        self.source_page("shop/list/index")
        result = self.inventory("--strict", expected=1)
        self.assertEqual(result["skill"], "miniapp-recon")
        self.assertEqual(result["completeness"], "PARTIAL")
        self.assertEqual(result["metadata"]["pages_count"], 3)
        self.assertEqual(result["subpackages"]["found"], ["shop"])
        self.assertEqual(result["subpackages"]["missing"], [])
        self.assertEqual(result["subpackages"]["issues"][0]["file"], "shop/order/index")
        self.assertEqual([page["complete"] for page in result["pages"]], [True, True, False])
        self.assertNotIn("severity", result["subpackages"]["issues"][0])

    def test_existing_but_empty_subpackage_is_partial(self):
        self.config({"pages": [], "subpackages": [{"root": "empty", "pages": ["index"]}]})
        self.put("app.js")
        (self.root / "empty").mkdir()
        result = self.inventory("--strict", expected=1)
        self.assertEqual(result["completeness"], "PARTIAL")
        self.assertEqual(result["subpackages"]["issues"][0]["type"], "missing_subpackage_page")
        self.assertEqual(result["pages"][0]["page"], "empty/index")
        self.assertFalse(result["pages"][0]["complete"])

    def test_subpackage_without_declared_pages_is_unverifiable(self):
        self.config({"subPackages": [{"root": "empty", "pages": []}]})
        self.put("app.js")
        (self.root / "empty").mkdir()
        result = self.inventory("--strict", expected=1)
        self.assertEqual(result["completeness"], "PARTIAL")
        self.assertIn("no declared pages", result["subpackages"]["issues"][0]["impact"])

    def test_missing_subpackage_still_lists_all_declared_pages(self):
        self.config({"subPackages": [{"root": "absent", "pages": ["one", "two"]}]})
        self.put("app.js")
        result = self.inventory("--strict", expected=1)
        self.assertEqual(result["subpackages"]["missing"], ["absent"])
        self.assertEqual(result["metadata"]["pages_count"], 2)
        self.assertEqual({page["page"] for page in result["pages"]}, {"absent/one", "absent/two"})

    def test_raw_layout_uses_html_for_main_and_subpackage_pages(self):
        self.config({
            "pages": ["pages/home/index"],
            "subPackages": [{"root": "detail", "pages": ["index"]}],
        }, raw=True)
        self.put("app-service.js")
        self.put("pages/home/index.html")
        self.put("detail/index.html")
        result = self.inventory("--strict")
        self.assertEqual(result["completeness"], "COMPLETE")
        self.assertEqual(result["config_file"], "app-config.json")
        self.assertTrue(all(page["complete"] for page in result["pages"]))
        self.assertFalse(any(page["present"]["js"] for page in result["pages"]))
        self.assertEqual(result["metadata"]["pages_count"], 2)

    def test_missing_raw_entry_is_an_explicit_main_package_issue(self):
        self.config({"pages": ["index"]}, raw=True)
        self.put("index.html")
        result = self.inventory("--strict", expected=1)
        self.assertEqual(result["main_package"]["status"], "ISSUES")
        self.assertEqual(result["main_package"]["issues"][0]["file"], "app-service.js")
        self.assertNotIn("severity", result["main_package"]["issues"][0])

    def test_plugins_missing_or_unverified_both_make_material_partial(self):
        self.config({"plugins": {
            "missing": {"provider": "wx0000000000000001", "version": "1.0.0"},
            "local": {"provider": "wx0000000000000002", "version": "2.0.0"},
        }})
        self.put("app.js")
        self.put("__plugin__/wx0000000000000002/index.js", "module.exports = {};")
        result = self.inventory("--strict", expected=1)
        self.assertEqual(result["completeness"], "PARTIAL")
        self.assertEqual(result["metadata"]["plugins_count"], 2)
        issues = {item["plugin"]: item for item in result["plugins"]["issues"]}
        self.assertEqual(issues["missing"]["type"], "missing_plugin")
        self.assertEqual(issues["local"]["type"], "unverified_plugin")
        self.assertTrue(all("severity" not in issue for issue in issues.values()))

    def test_subpackage_plugin_declaration_is_not_ignored(self):
        self.config({"subPackages": [{
            "root": "shop", "pages": ["index"],
            "plugins": {"payment": {"provider": "wx0000000000000003"}},
        }]})
        self.put("app.js")
        self.source_page("shop/index")
        result = self.inventory("--strict", expected=1)
        self.assertEqual(result["plugins"]["declared"], ["shop:payment"])
        self.assertEqual(result["metadata"]["plugins_count"], 1)

    def test_complete_structure_does_not_claim_quality_or_version_validation(self):
        self.config({"pages": ["pages/v1.2"]})
        self.put("app.js")
        self.source_page("pages/v1.2")
        result = self.inventory("--strict")
        self.assertEqual(result["completeness"], "COMPLETE")
        self.assertEqual(result["quality"]["version_consistency"], "UNKNOWN")
        self.assertEqual(result["quality"]["decompile_quality"], "UNKNOWN")
        self.assertTrue(result["coverage_notes"])

    def test_missing_or_invalid_config_is_blocked_without_claiming_main_package_ok(self):
        for value in (None, "{broken", "[]"):
            with self.subTest(value=value):
                if value is not None:
                    self.put("app.json", value)
                result = self.inventory("--strict", expected=1)
                self.assertEqual(result["completeness"], "BLOCKED")
                self.assertEqual(result["main_package"]["status"], "UNKNOWN")
                self.assertEqual(result["quality"]["version_consistency"], "UNKNOWN")
                for field in ("pages_count", "subpackages_count", "plugins_count", "app_id"):
                    self.assertIsNone(result["metadata"][field])

    def test_extractor_unread_config_preserves_real_api_counts(self):
        self.put("app.js", "wx.request({url:'http://api.example', method:'GET'});")
        for value in (None, "{broken", "[]"):
            with self.subTest(value=value):
                if value is not None:
                    self.put("app.json", value)
                result = self.surface()
                for field in ("pages_count", "subpackages_count", "plugins_count", "app_id"):
                    self.assertIsNone(result["metadata"][field])
                self.assertEqual(result["statistics"]["total_apis"], 1)
                self.assertEqual(result["statistics"]["files_scanned"], 1)
                self.assertTrue(any("counts are unknown" in item for item in result["limitations"]))

    def test_successfully_read_empty_config_has_known_zero_counts(self):
        self.config({})
        self.put("app.js")
        for result in (self.inventory(), self.surface()):
            for field in ("pages_count", "subpackages_count", "plugins_count"):
                self.assertEqual(result["metadata"][field], 0)
            self.assertIsNone(result["metadata"]["app_id"])

    def test_top_level_quoted_properties_win_over_nested_data_properties(self):
        self.put("app.js", '''wx.request({
  data: {url: 'https://nested.invalid', method: 'DELETE'},
  "url": 'https://api.example/users?fields=id,name',
  'method': "post"
});
wx.cloud.callFunction({data: {name: 'nested'}, 'name': "outer"});
wx.request({data: {url: 'https://nested.invalid/only'}});
''')
        result = self.surface()
        self.assertEqual(result["skill"], "miniapp-static-audit")
        self.assertEqual(result["apis"][0]["url"], "https://api.example/users?fields=id,name")
        self.assertEqual(result["apis"][0]["method"], "POST")
        self.assertEqual(result["cloud_functions"][0]["name"], "outer")
        self.assertEqual(result["apis"][1]["url"], "")
        self.assertTrue(result["apis"][1]["dynamic"])
        self.assertEqual(result["apis"][1]["method"], "UNKNOWN")
        self.assertEqual({domain["domain"] for domain in result["domains"]}, {"api.example"})
        self.assertTrue(any("top-level url" in item for item in result["limitations"]))

    def test_templates_and_concatenations_remain_dynamic(self):
        expressions = [
            "`https://api.example/${user.id}`",
            "'https://api.example/' + 'users'",
            "baseUrl + '/users'",
            "`https://api.example/${choose(`item-${id}`)}`",
        ]
        self.put("app.js", "\n".join(
            "wx.request({url: " + expression + ", method: selectedMethod});"
            for expression in expressions
        ))
        result = self.surface()
        self.assertEqual(len(result["apis"]), 4)
        self.assertEqual([item["url_expression"] for item in result["apis"]], expressions)
        self.assertTrue(all(item["dynamic"] for item in result["apis"]))
        self.assertTrue(all(item["method"] == "UNKNOWN" for item in result["apis"]))
        self.assertEqual(result["domains"], [])
        self.assertTrue(any("method unknown" in item for item in result["limitations"]))

    def test_cloud_and_navigation_expressions_remain_dynamic(self):
        self.put("app.js", """wx.cloud.callFunction({name: `lookup-${kind}`});
wx.cloud.callFunction({name: 'lookup-' + kind});
wx.navigateTo({'url': '/pages/' + selected});
wx.redirectTo({url: `/pages/${selected}`});
""")
        result = self.surface()
        self.assertTrue(all(item["dynamic"] for item in result["cloud_functions"]))
        self.assertTrue(all(item["dynamic"] for item in result["navigation"]))
        self.assertEqual(result["cloud_functions"][0]["name_expression"], "`lookup-${kind}`")
        self.assertEqual(result["navigation"][0]["url_expression"], "'/pages/' + selected")

    def test_static_template_and_escaped_literals_can_be_read_without_execution(self):
        self.put("app.js", r'''wx.request({"url": `http://api.example/static`, "method": "get"});
wx.request({'url': 'https:\/\/api.example\/\x76\u0031', method: 'POST'});
''')
        result = self.surface()
        self.assertEqual([item["url"] for item in result["apis"]], [
            "http://api.example/static", "https://api.example/v1",
        ])
        self.assertFalse(any(item["dynamic"] for item in result["apis"]))

    def test_repeated_api_cloud_and_navigation_calls_retain_all_locations(self):
        for filename, quote in (("a.js", "'"), ("b.js", '"')):
            self.put(filename, "\n".join([
                f"wx.request({{url: {quote}https://api.example/item{quote}, method: 'GET'}});",
                "wx.cloud.callFunction({name: 'lookup'});",
                "wx.navigateTo({url: '/pages/detail'});",
                "wx.request({url: 'https://api.example/item', method: 'get'});",
            ]))
        result = self.surface()
        self.assertEqual(len(result["apis"]), 1)
        self.assertEqual(result["apis"][0]["locations"], [
            {"file": "a.js", "line": 1}, {"file": "a.js", "line": 4},
            {"file": "b.js", "line": 1}, {"file": "b.js", "line": 4},
        ])
        self.assertEqual(len(result["cloud_functions"][0]["locations"]), 2)
        self.assertEqual(len(result["navigation"][0]["locations"]), 2)
        self.assertEqual(result["statistics"]["total_apis"], 1)

    def test_same_line_duplicate_calls_are_both_retained(self):
        self.put("app.js", "wx.request({url:'/x'}); wx.request({url:'/x'});")
        result = self.surface()
        self.assertEqual(len(result["apis"]), 1)
        self.assertEqual(len(result["apis"][0]["locations"]), 2)

    def test_domain_protocol_and_type_are_taken_from_real_urls(self):
        calls = [
            ("request", "http"), ("request", "https"),
            ("connectSocket", "ws"), ("connectSocket", "wss"),
            ("uploadFile", "http"), ("downloadFile", "https"),
        ]
        self.put("app.js", "\n".join(
            f"wx.{call}({{url: '{scheme}://same.example/path'}});"
            for call, scheme in calls
        ))
        result = self.surface()
        self.assertEqual({(item["domain"], item["protocol"], item["type"]) for item in result["domains"]}, {
            ("same.example", "http", "request"), ("same.example", "https", "request"),
            ("same.example", "ws", "socket"), ("same.example", "wss", "socket"),
            ("same.example", "http", "upload"), ("same.example", "https", "download"),
        })
        self.assertEqual(result["statistics"]["unique_domains"], 1)
        self.assertTrue(all("is_third_party" not in item for item in result["domains"]))
        self.assertTrue(all(item["method"] == "UNKNOWN" for item in result["apis"]))

    def test_uncertain_options_do_not_invent_an_endpoint_or_method(self):
        sources = [
            "wx.request(options);",
            "wx.request({url:'https://known.example', ...overrides});",
            "wx.request({[key]:'https://computed.example'});",
            "wx.request({url:'/literal', method: chooseMethod()});",
            "wx.request({url:'https://unfinished.example'",  # No closing delimiters.
        ]
        for index, source in enumerate(sources):
            self.put(f"case{index}.js", source)
        result = self.surface()
        self.assertTrue(result["apis"])
        self.assertTrue(all(item["method"] == "UNKNOWN" for item in result["apis"]))
        self.assertEqual(result["domains"], [])
        self.assertTrue(any("unbalanced" in item for item in result["limitations"]))
        self.assertTrue(any("spread" in item for item in result["limitations"]))
        self.assertTrue(any("not a direct object" in item for item in result["limitations"]))

    def test_comments_strings_and_regex_literals_are_not_call_sites(self):
        self.put("app.js", r'''// wx.request({url:'https://comment.example'});
/* wx.request({url:'https://block.example'}); */
const example = "wx.request({url:'https://string.example'})";
const pattern = /wx.request\({url:'https:\/\/regex.example'}\)/;
wx.request({data:{pattern:/[,}]/}, url:'http://real.example', method:'GET'});
''')
        result = self.surface()
        self.assertEqual(len(result["apis"]), 1)
        self.assertEqual(result["apis"][0]["url"], "http://real.example")

    def test_literal_and_variable_with_same_spelling_do_not_merge(self):
        self.put("app.js", "wx.request({url:'target'}); wx.request({url:target});")
        result = self.surface()
        self.assertEqual(len(result["apis"]), 2)
        self.assertEqual([item["dynamic"] for item in result["apis"]], [False, True])

    def test_unassessed_capabilities_are_limits_instead_of_empty_results(self):
        self.put("app.js", "wx.request({url:'/api'});")
        result = self.surface()
        for field in ("cloud_database", "sensitive_apis", "request_wrappers"):
            self.assertNotIn(field, result)
        for field in ("used", "undeclared"):
            self.assertNotIn(field, result["permissions"])
        for field in ("cloud_database_collections", "sensitive_apis", "third_party_domains"):
            self.assertNotIn(field, result["statistics"])
        self.assertEqual(result["metadata"]["framework"], "unknown")
        self.assertTrue(any("permission usage" in item for item in result["limitations"]))

    def test_cli_output_file_and_app_id_override(self):
        self.config({"pages": []})
        self.put("app.js")
        output = Path(self.temporary.name) / "result.json"
        for script, expected_skill in ((INVENTORY, "miniapp-recon"), (EXTRACTOR, "miniapp-static-audit")):
            with self.subTest(script=script):
                process = self.invoke(script, "--output", str(output), "--app-id", "wx1234567890abcdef")
                self.assertEqual(process.stdout, "")
                result = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(result["skill"], expected_skill)
                self.assertEqual(result["metadata"]["app_id"], "wx1234567890abcdef")

    def test_invalid_root_exits_two_without_json(self):
        for script in (INVENTORY, EXTRACTOR):
            with self.subTest(script=script):
                process = self.invoke(script, "--root", str(self.root / "absent"), expected=2)
                self.assertEqual(process.stdout, "")
                self.assertIn("not a directory", process.stderr)


if __name__ == "__main__":
    unittest.main()
