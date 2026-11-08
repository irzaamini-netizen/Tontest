"""Conservative shared lexer for TON contract source languages."""
import re

from .syntax import (
    Diagnostic,
    DiagnosticSeverity,
    Language,
    SourcePosition,
    SourceSpan,
    Token,
    TokenKind,
)


KEYWORDS = {
    Language.FUNC: {
        "return", "var", "repeat", "do", "while", "until",
        "try", "catch", "if", "ifnot", "then", "else",
        "elseif", "elseifnot", "int", "cell", "slice",
        "builder", "cont", "tuple", "type", "forall",
        "extern", "global", "asm", "impure", "inline",
        "inline_ref", "auto_apply", "method_id", "operator",
        "infix", "infixl", "infixr", "const", "_",
    },
    Language.TOLK: {
        "fun", "get", "contract", "struct", "message",
        "trait", "extends", "with", "type", "const",
        "global", "val", "var", "return", "if", "else",
        "while", "do", "repeat", "break", "continue",
        "try", "catch", "throw", "assert", "match",
        "lazy", "mutate", "import", "as", "is",
        "true", "false", "null",
    },
    Language.TACT: {
        "contract", "trait", "extends", "with", "message",
        "struct", "primitive", "enum", "const", "let",
        "map", "init", "receive", "bounced", "external",
        "internal", "get", "fun", "virtual", "override",
        "abstract", "inline", "if", "else", "while",
        "foreach", "return", "try", "catch", "throw",
        "true", "false", "null",
    },
}

# Legacy shared table: retained only for Language.UNKNOWN compatibility.
OPERATORS = tuple(sorted({
    "<=>", "~>>=", "^>>=", "^/=", "~/=", "~%=", "^%=", "<<=",
    ">>=", "==", "!=", "<=", ">=", "=>", "->", "::",
    "&&", "||", "<<", ">>", "~>>", "^>>", "~/", "^/",
    "~%", "^%", "/%", "+=", "-=", "*=", "/=", "%=",
    "&=", "|=", "^=", "++", "--", "??", "?.", "**",
    "+", "-", "*", "/", "%", "?", ":", "=", "<", ">",
    "&", "|", "^", "~", "!", ".", "@", "#",
}, key=len, reverse=True))


def operator_table(symbols):
    return tuple(sorted(set(symbols), key=len, reverse=True))


OPERATORS_BY_LANGUAGE = {
    Language.FUNC: operator_table({
        "<=>", "~>>=", "^>>=", "^/=", "~/=", "~%=", "^%=",
        "<<=", ">>=", "==", "!=", "<=", ">=", "->",
        "<<", ">>", "~>>", "^>>", "~/", "^/", "~%", "^%",
        "/%", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
        "+", "-", "*", "/", "%", "?", ":", "=", "<", ">",
        "&", "|", "^", "~",
    }),
    Language.TOLK: operator_table({
        "??", "&&", "||", "<=>", "==", "!=", "<=", ">=",
        "<<", ">>", "~>>", "^>>", "~/", "^/", "->", "=>",
        "+=", "-=", "*=", "/=", "%=", "<<=", ">>=",
        "&=", "|=", "^=", "+", "-", "*", "/", "%", "?",
        ":", "=", "<", ">", "&", "|", "^", "!", "~",
        ".", "@",
        # Preserve the existing Tolk #include tokenization behavior.
        "#",
    }),
    Language.TACT: operator_table({
        "||=", "&&=", ">>=", "<<=", "-=", "+=", "*=", "/=",
        "%=", "|=", "&=", "^=", "==", "!=", "<=", ">=",
        "||", "&&", "<<", ">>", "!!", "=>",
        "=", "?", ":", "<", ">", "+", "-", "*", "/", "%",
        "|", "^", "&", "!", "~", ".", "@",
    }),
}

PUNCTUATION = set("()[]{};,")
FUNC_DIRECTIVES = ("#include", "#pragma")
IDENTIFIER_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
NUMBER_RE = re.compile(
    r"(?:0[xX][0-9a-fA-F](?:_?[0-9a-fA-F])*"
    r"|0[bB][01](?:_?[01])*"
    r"|(?:[0-9](?:_?[0-9])*)(?:\.[0-9](?:_?[0-9])*)?"
    r"(?:[eE][+-]?[0-9](?:_?[0-9])*)?)"
)


# Dotted compiler versions are recognized only in FunC pragma values.
FUNC_PRAGMA_VERSION_PREFIX_RE = re.compile(
    r"[ \t]*#pragma[ \t]+version[ \t]*=[ \t]*"
)
FUNC_VERSION_RE = re.compile(r"[0-9]+(?:\.[0-9]+)+")

class Lexer:
    def __init__(self, source, language=Language.UNKNOWN):
        if not isinstance(source, str):
            raise TypeError("source must be str")
        if not isinstance(language, Language):
            language = Language(language)

        self.source = source
        self.language = language
        self.length = len(source)
        self.offset = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        self.diagnostics = []

    def position(self):
        return SourcePosition(self.offset, self.line, self.column)

    def span_from(self, start):
        return SourceSpan(start, self.position())

    def advance(self):
        ch = self.source[self.offset]
        self.offset += 1

        if ch == "\r":
            if self.offset < self.length and self.source[self.offset] == "\n":
                self.offset += 1
            self.line += 1
            self.column = 1
        elif ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return ch

    def emit(self, kind, value, start):
        self.tokens.append(Token(kind, value, self.span_from(start)))

    def diagnostic(self, code, message, start):
        self.diagnostics.append(
            Diagnostic(
                code,
                message,
                DiagnosticSeverity.ERROR,
                self.span_from(start),
            )
        )

    def scan_line_comment(self):
        while self.offset < self.length:
            if self.source[self.offset] in "\r\n":
                break
            self.advance()

    def scan_block_comment(self):
        start = self.position()
        self.advance()
        self.advance()

        while self.offset < self.length:
            if self.source.startswith("*/", self.offset):
                self.advance()
                self.advance()
                return

            self.advance()

        self.diagnostic(
            "LEX001",
            "Unterminated block comment",
            start,
        )

    def scan_func_block_comment(self):
        start = self.position()
        self.advance()
        self.advance()
        depth = 1

        while self.offset < self.length:
            if self.source.startswith(";;", self.offset):
                self.scan_line_comment()
                continue

            if self.source.startswith("{-", self.offset):
                self.advance()
                self.advance()
                depth += 1
                continue

            if self.source.startswith("-}", self.offset):
                self.advance()
                self.advance()
                depth -= 1
                if depth == 0:
                    return
                continue

            self.advance()

        self.diagnostic(
            "LEX001",
            "Unterminated FunC block comment",
            start,
        )

    def scan_string(self):
        start = self.position()
        quote = self.source[self.offset]
        self.advance()
        escaped = False
        terminated = False

        while self.offset < self.length:
            ch = self.source[self.offset]

            if ch in "\r\n" and not escaped:
                break

            self.advance()

            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                terminated = True
                break

        value = self.source[start.offset:self.offset]
        self.emit(TokenKind.STRING, value, start)

        if not terminated:
            self.diagnostic(
                "LEX002",
                "Unterminated string literal",
                start,
            )

    def scan_number(self):
        start = self.position()
        match = None

        if self.language == Language.FUNC:
            line_start = max(
                self.source.rfind("\\n", 0, self.offset),
                self.source.rfind("\\r", 0, self.offset),
            ) + 1
            prefix = self.source[line_start:self.offset]

            if FUNC_PRAGMA_VERSION_PREFIX_RE.fullmatch(prefix):
                candidate = FUNC_VERSION_RE.match(
                    self.source,
                    self.offset,
                )

                if candidate is not None:
                    end = candidate.end()
                    if end == self.length or not (
                        self.source[end].isalnum()
                        or self.source[end] in "_$."
                    ):
                        match = candidate

        if match is None:
            match = NUMBER_RE.match(self.source, self.offset)

        value = match.group(0)

        for _ in value:
            self.advance()

        self.emit(TokenKind.NUMBER, value, start)

    def scan_identifier(self):
        start = self.position()
        match = IDENTIFIER_RE.match(self.source, self.offset)
        value = match.group(0)

        for _ in value:
            self.advance()

        keywords = KEYWORDS.get(self.language, set())
        kind = (
            TokenKind.KEYWORD
            if value in keywords
            else TokenKind.IDENTIFIER
        )
        self.emit(kind, value, start)

    def scan_func_directive(self):
        if self.language != Language.FUNC:
            return False

        for directive in FUNC_DIRECTIVES:
            if not self.source.startswith(directive, self.offset):
                continue

            end = self.offset + len(directive)
            if end < self.length:
                next_char = self.source[end]
                if (
                    next_char.isalnum()
                    or next_char in "_$"
                ):
                    continue

            start = self.position()
            for _ in directive:
                self.advance()

            self.emit(TokenKind.KEYWORD, directive, start)
            return True

        return False

    def scan_operator(self):
        start = self.position()

        operators = OPERATORS_BY_LANGUAGE.get(
            self.language,
            OPERATORS,
        )

        for operator in operators:
            if self.source.startswith(operator, self.offset):
                for _ in operator:
                    self.advance()

                kind = (
                    TokenKind.PUNCTUATION
                    if operator in {",", ";", ":"}
                    else TokenKind.OPERATOR
                )
                self.emit(kind, operator, start)
                return True

        return False

    def run(self):
        while self.offset < self.length:
            ch = self.source[self.offset]

            if ch.isspace():
                self.advance()
                continue

            if self.language == Language.FUNC:
                if self.source.startswith(";;", self.offset):
                    self.scan_line_comment()
                    continue

                if self.source.startswith("{-", self.offset):
                    self.scan_func_block_comment()
                    continue
            else:
                if self.source.startswith("//", self.offset):
                    self.scan_line_comment()
                    continue

                if self.source.startswith("/*", self.offset):
                    self.scan_block_comment()
                    continue

            if self.scan_func_directive():
                continue

            if ch in ('"', "'"):
                self.scan_string()
                continue

            if "0" <= ch <= "9":
                self.scan_number()
                continue

            if IDENTIFIER_RE.match(self.source, self.offset):
                self.scan_identifier()
                continue

            if ch in PUNCTUATION:
                start = self.position()
                self.advance()
                self.emit(TokenKind.PUNCTUATION, ch, start)
                continue

            if self.scan_operator():
                continue

            start = self.position()
            self.advance()
            self.emit(TokenKind.UNKNOWN, ch, start)
            self.diagnostic(
                "LEX003",
                "Unrecognized source character",
                start,
            )

        eof = self.position()
        self.tokens.append(
            Token(TokenKind.EOF, "", SourceSpan(eof, eof))
        )

        return self.tokens, self.diagnostics


def lex(source, language=Language.UNKNOWN):
    """Return (tokens, diagnostics) for source text."""
    return Lexer(source, language).run()
