import unittest

from tonsec.func_parser import parse_func
from tonsec.syntax import DiagnosticSeverity, Language


class FuncParserTests(unittest.TestCase):
    def test_standard_signature_and_modifiers(self):
        src = "() send_money(slice address, int amount) impure inline { return; }"
        module = parse_func(src)
        self.assertEqual(module.language, Language.FUNC)
        self.assertEqual(len(module.functions), 1)

        fn = module.functions[0]
        self.assertEqual(fn.name, "send_money")
        self.assertEqual(fn.return_type, "()")
        self.assertEqual([p.name for p in fn.parameters], ["address", "amount"])
        self.assertEqual([p.type_text for p in fn.parameters], ["slice", "int"])
        self.assertEqual(fn.modifiers, ("impure", "inline"))
        self.assertEqual(
            src[fn.body_span.start.offset:fn.body_span.end.offset],
            " return; ",
        )

    def test_nonempty_return_type(self):
        fn = parse_func("int get_balance() { return 0; }").functions[0]
        self.assertEqual(fn.return_type, "int")
        self.assertEqual(fn.name, "get_balance")
        self.assertEqual(fn.parameters, ())

    def test_multiple_top_level_functions(self):
        src = """
() first() { return; }
int second(int value) { return value; }
"""
        self.assertEqual(
            [f.name for f in parse_func(src).functions],
            ["first", "second"],
        )

    def test_include_and_pragma_do_not_pollute_return_type(self):
        src = '#include "stdlib.fc"\n#pragma version = 0.4.4\n() main() { return; }'
        fn = parse_func(src).functions[0]
        self.assertEqual(fn.name, "main")
        self.assertEqual(fn.return_type, "()")

    def test_nested_braces_and_fake_function_text(self):
        src = r'''
() outer() {
    if (1) { int x = 2; }
    ;; fun fake() { }
    var s = "fun also_fake() { }";
}
'''
        self.assertEqual(
            [f.name for f in parse_func(src).functions],
            ["outer"],
        )

    def test_nested_parentheses_in_parameter_type(self):
        src = "() f((int -> int) callback, slice data) { return; }"
        fn = parse_func(src).functions[0]
        self.assertEqual([p.name for p in fn.parameters], ["callback", "data"])

    def test_unclosed_body_diagnostic(self):
        module = parse_func("() broken() {")
        self.assertTrue(any(
            d.code == "PARSE002"
            and d.severity == DiagnosticSeverity.ERROR
            for d in module.diagnostics
        ))

    def test_unmatched_closing_brace_diagnostic(self):
        module = parse_func("}")
        self.assertTrue(any(d.code == "PARSE001" for d in module.diagnostics))

    def test_empty_source(self):
        module = parse_func("")
        self.assertEqual(module.functions, ())
        self.assertEqual(module.diagnostics, ())

    def test_non_string_input_rejected(self):
        with self.assertRaises(TypeError):
            parse_func(None)


if __name__ == "__main__":
    unittest.main()
