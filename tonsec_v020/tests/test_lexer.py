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
_FUNC,
        )
