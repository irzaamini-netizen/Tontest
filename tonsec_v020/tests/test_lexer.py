import unittest

from tonsec.lexer import lex
from tonsec.syntax import Language, TokenKind


class LexerTests(unittest.TestCase):
    def values(self, source, language):
        tokens, diagnostics = lex(source, language)
        return tokens, diagnostics

    def test_tolk_keywords_and_get_fun(self):
        tokens, diagnostics = self.values(
            "get fun currentCounter() { return 1; }",
            Language.TOLK,
        )
        words = [t.value for t in tokens]
        self.assertEqual(words[:3], ["get", "fun", "currentCounter"])
        self.assertEqual(tokens[0].kind, TokenKind.KEYWORD)
        self.assertEqual(tokens[1].kind, TokenKind.KEYWORD)
        self.assertEqual(diagnostics, [])

    def test_comments_are_skipped(self):
        tokens, diagnostics = self.values(
            "fun a() { // comment\n /* block */ return 1; }",
            Language.TOLK,
        )
        words = [t.value for t in tokens]
        self.assertNotIn("comment", words)
        self.assertIn("return", words)
        self.assertEqual(diagnostics, [])

    def test_string_content_is_not_tokenized(self):
        tokens, diagnostics = self.values(
            'const X = "send_raw_message // text";',
            Language.TOLK,
        )
        strings = [t for t in tokens if t.kind == TokenKind.STRING]
        self.assertEqual(len(strings), 1)
        self.assertIn("send_raw_message", strings[0].value)
        self.assertEqual(diagnostics, [])

    def test_longest_match_operator(self):
        tokens, diagnostics = self.values(
            "a >>= 2; b <=> c;",
            Language.FUNC,
        )
        operators = [
            t.value for t in tokens
            if t.kind == TokenKind.OPERATOR
        ]
        self.assertIn(">>=", operators)
        self.assertIn("<=>", operators)
        self.assertEqual(diagnostics, [])

    def test_source_positions_after_newline(self):
        tokens, diagnostics = self.values(
            "fun a() {}\nfun b() {}",
            Language.TOLK,
        )
        second_fun = next(t for t in tokens if t.value == "b")
        self.assertEqual(second_fun.span.start.line, 2)
        self.assertEqual(second_fun.span.start.column, 5)
        self.assertEqual(diagnostics, [])

    def test_unterminated_block_comment(self):
        tokens, diagnostics = self.values(
            "fun a() {} /* unfinished",
            Language.TOLK,
        )
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].code, "LEX001")
        self.assertEqual(tokens[-1].kind, TokenKind.EOF)

    def test_unterminated_string(self):
        tokens, diagnostics = self.values(
            'const X = "unfinished',
            Language.TOLK,
        )
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].code, "LEX002")

    def test_unknown_character_has_diagnostic(self):
        tokens, diagnostics = self.values(
            "fun a() { § }",
            Language.TOLK,
        )
        self.assertTrue(any(t.kind == TokenKind.UNKNOWN for t in tokens))
        self.assertEqual(diagnostics[0].code, "LEX003")


    def test_persian_digits_do_not_crash(self):
        tokens, diagnostics = self.values("۱۲۳", Language.TOLK)
        self.assertEqual(tokens[0].kind, TokenKind.UNKNOWN)
        self.assertEqual(tokens[-1].kind, TokenKind.EOF)
        self.assertTrue(diagnostics)
        self.assertTrue(all(d.code == "LEX003" for d in diagnostics))

    def test_arabic_digits_do_not_crash(self):
        tokens, diagnostics = self.values("١٢٣", Language.TOLK)
        self.assertEqual(tokens[0].kind, TokenKind.UNKNOWN)
        self.assertEqual(tokens[-1].kind, TokenKind.EOF)
        self.assertTrue(diagnostics)
        self.assertTrue(all(d.code == "LEX003" for d in diagnostics))

    def test_eof_token_has_final_position(self):
        tokens, diagnostics = self.values("abc", Language.UNKNOWN)
        self.assertEqual(tokens[-1].kind, TokenKind.EOF)
        self.assertEqual(tokens[-1].span.start.offset, 3)
        self.assertEqual(diagnostics, [])

    def test_crlf_positions(self):
        tokens, diagnostics = self.values(
            "fun a() {}\r\nfun b() {}",
            Language.TOLK,
        )
        second_fun = next(t for t in tokens if t.value == "b")
        self.assertEqual(second_fun.span.start.line, 2)
        self.assertEqual(second_fun.span.start.column, 5)
        self.assertEqual(diagnostics, [])


class FuncLexerRegressionTests(unittest.TestCase):
    def values(self, source, language):
        tokens, diagnostics = lex(source, language)
        return [t.value for t in tokens], diagnostics, tokens

    def test_func_line_comment(self):
        values, diagnostics, _ = self.values(
            "int a = 1; ;; comment\nint b = 2;",
            Language.FUNC,
        )
        self.assertEqual(
            values,
            ["int", "a", "=", "1", ";", "int", "b", "=", "2", ";", ""],
        )
        self.assertEqual(diagnostics, [])

    def test_func_nested_block_comment(self):
        values, diagnostics, _ = self.values(
            "{- outer {- inner -} tail -} int x = 1;",
            Language.FUNC,
        )
        self.assertEqual(values, ["int", "x", "=", "1", ";", ""])
        self.assertEqual(diagnostics, [])

    def test_func_line_comment_inside_block_comment(self):
        values, diagnostics, _ = self.values(
            "{- outer ;; ignored -}\nstill comment -} int x = 1;",
            Language.FUNC,
        )
        self.assertEqual(values, ["int", "x", "=", "1", ";", ""])
        self.assertEqual(diagnostics, [])

    def test_func_unterminated_nested_comment(self):
        _, diagnostics, _ = self.values(
            "{- outer {- inner -}",
            Language.FUNC,
        )
        self.assertTrue(any(d.code == "LEX001" for d in diagnostics))

    def test_func_operator_longest_match(self):
        _, diagnostics, tokens = self.values(
            "int x = a ^/= b;",
            Language.FUNC,
        )
        self.assertEqual(diagnostics, [])
        self.assertIn("^/=", [t.value for t in tokens])

    def test_func_standalone_underscore_is_reserved(self):
        _, diagnostics, tokens = self.values("_ my_var", Language.FUNC)
        self.assertEqual(diagnostics, [])
        meaningful = [t for t in tokens if t.kind != TokenKind.EOF]
        self.assertEqual(meaningful[0].value, "_")
        self.assertEqual(meaningful[0].kind, TokenKind.KEYWORD)
        self.assertEqual(meaningful[1].kind, TokenKind.IDENTIFIER)
        self.assertEqual(meaningful[1].value, "my_var")

    def test_func_include_is_single_keyword_token(self):
        tokens, diagnostics = lex(
            '#include "stdlib.fc"\nint x = 1;',
            Language.FUNC,
        )
        meaningful = [t for t in tokens if t.kind != TokenKind.EOF]

        self.assertEqual(meaningful[0].value, "#include")
        self.assertEqual(meaningful[0].kind, TokenKind.KEYWORD)
        self.assertEqual(meaningful[1].kind, TokenKind.STRING)
        self.assertEqual(meaningful[1].value, '"stdlib.fc"')
        self.assertEqual(diagnostics, [])

    def test_func_pragma_is_single_keyword_token(self):
        tokens, diagnostics = lex(
            "#pragma version = 0.4.4",
            Language.FUNC,
        )
        meaningful = [t for t in tokens if t.kind != TokenKind.EOF]

        self.assertEqual(meaningful[0].value, "#pragma")
        self.assertEqual(meaningful[0].kind, TokenKind.KEYWORD)
        self.assertEqual(diagnostics, [])

    def test_func_pragma_version_is_single_number_token(self):
        tokens, diagnostics = lex(
            "#pragma version = 0.4.4",
            Language.FUNC,
        )
        meaningful = [t for t in tokens if t.kind != TokenKind.EOF]

        self.assertEqual(
            [t.value for t in meaningful],
            ["#pragma", "version", "=", "0.4.4"],
        )
        self.assertEqual(meaningful[-1].kind, TokenKind.NUMBER)
        self.assertEqual(diagnostics, [])

    def test_func_dotted_number_outside_pragma_is_not_version_token(self):
        tokens, diagnostics = lex("int x = 0.4.4;", Language.FUNC)
        meaningful = [t for t in tokens if t.kind != TokenKind.EOF]

        self.assertEqual(
            [t.value for t in meaningful],
            ["int", "x", "=", "0.4", ".", "4", ";"],
        )
        self.assertEqual(meaningful[4].kind, TokenKind.UNKNOWN)
        self.assertEqual([d.code for d in diagnostics], ["LEX003"])

    def test_func_directive_prefix_is_not_misclassified(self):
        tokens, diagnostics = lex(
            "#included",
            Language.FUNC,
        )
        meaningful = [t for t in tokens if t.kind != TokenKind.EOF]

        self.assertEqual(
            [t.value for t in meaningful],
            ["#", "included"],
        )
        self.assertEqual(meaningful[0].kind, TokenKind.UNKNOWN)
        self.assertEqual(meaningful[1].kind, TokenKind.IDENTIFIER)
        self.assertEqual(
            [d.code for d in diagnostics],
            ["LEX003"],
        )

    def test_tolk_hash_directive_behavior_unchanged(self):
        tokens, diagnostics = lex(
            '#include "stdlib.fc"',
            Language.TOLK,
        )
        meaningful = [t for t in tokens if t.kind != TokenKind.EOF]

        self.assertEqual(
            [t.value for t in meaningful],
            ["#", "include", '"stdlib.fc"'],
        )
        self.assertEqual(diagnostics, [])

    def test_tolk_c_style_comments_unchanged(self):
        values, diagnostics, _ = self.values(
            "/* comment */ fun test() {} // end",
            Language.TOLK,
        )
        self.assertEqual(values, ["fun", "test", "(", ")", "{", "}", ""])
        self.assertEqual(diagnostics, [])

    def test_tact_c_style_comments_unchanged(self):
        values, diagnostics, _ = self.values(
            "/* comment */ contract Test {} // end",
            Language.TACT,
        )
        self.assertEqual(values, ["contract", "Test", "{", "}", ""])
        self.assertEqual(diagnostics, [])


class LanguageSpecificOperatorTests(unittest.TestCase):
    def tokens(self, source, language):
        tokens, diagnostics = lex(source, language)
        return [
            token for token in tokens
            if token.kind != TokenKind.EOF
        ], diagnostics

    def test_func_operators_are_language_specific(self):
        source = "<=> ~>>= ^>>= ^/= ~/= ~%= ^%= <<= >>= ->"
        tokens, diagnostics = self.tokens(source, Language.FUNC)

        self.assertEqual(
            [token.value for token in tokens],
            source.split(),
        )
        self.assertTrue(
            all(token.kind == TokenKind.OPERATOR for token in tokens)
        )
        self.assertEqual(diagnostics, [])

    def test_func_hash_is_not_a_standalone_operator(self):
        tokens, diagnostics = self.tokens("#", Language.FUNC)

        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].kind, TokenKind.UNKNOWN)
        self.assertEqual([d.code for d in diagnostics], ["LEX003"])

    def test_tolk_specific_operators(self):
        source = "?? => -> @ ~>> ^/ <<= >>= !"
        tokens, diagnostics = self.tokens(source, Language.TOLK)

        self.assertEqual(
            [token.value for token in tokens],
            source.split(),
        )
        self.assertEqual(diagnostics, [])

    def test_tolk_does_not_merge_unsupported_composites(self):
        tokens, diagnostics = self.tokens("** ++ :: ?.", Language.TOLK)

        values = [token.value for token in tokens]
        self.assertNotIn("**", values)
        self.assertNotIn("++", values)
        self.assertNotIn("::", values)
        self.assertNotIn("?.", values)
        self.assertEqual(diagnostics, [])

    def test_tact_specific_operators(self):
        source = "=> !! ||= &&= @ ."
        tokens, diagnostics = self.tokens(source, Language.TACT)

        self.assertEqual(
            [token.value for token in tokens],
            source.split(),
        )
        self.assertEqual(diagnostics, [])

    def test_tact_rejects_bare_hash(self):
        tokens, diagnostics = self.tokens("#", Language.TACT)

        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].kind, TokenKind.UNKNOWN)
        self.assertEqual([d.code for d in diagnostics], ["LEX003"])

    def test_tact_does_not_merge_unsupported_composites(self):
        tokens, diagnostics = self.tokens("?? -> ** ++ :: ?.", Language.TACT)

        values = [token.value for token in tokens]
        for unsupported in ("??", "->", "**", "++", "::", "?."):
            self.assertNotIn(unsupported, values)

        self.assertEqual(diagnostics, [])

    def test_unknown_language_keeps_legacy_operator_table(self):
        source = "?? ** ++ :: && => !!"
        tokens, diagnostics = self.tokens(source, Language.UNKNOWN)

        self.assertEqual(
            [token.value for token in tokens],
            ["??", "**", "++", "::", "&&", "=>", "!", "!"],
        )
        self.assertEqual(diagnostics, [])


if __name__ == "__main__":
    unittest.main()
