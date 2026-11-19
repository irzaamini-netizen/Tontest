"""Conservative structural parser for Tact sources."""
from .lexer import lex
from .syntax import (
    Diagnostic,
    DiagnosticSeverity,
    FunctionDecl,
    Language,
    Module,
    SourcePosition,
    SourceSpan,
)

def _pos(source, offset):
    line = source.count("\n", 0, offset) + 1
    last = source.rfind("\n", 0, offset)
    col = offset + 1 if last < 0 else offset - last
    return SourcePosition(offset, line, col)

def _span(source, start, end):
    return SourceSpan(_pos(source, start), _pos(source, end))

def _v(token):
    return getattr(token, "value", "")

def _kind(token):
    return str(getattr(getattr(token, "kind", None), "name", getattr(token, "kind", "")))

def _matching(tokens, start, opening, closing):
    depth = 0
    for i in range(start, len(tokens)):
        value = _v(tokens[i])
        if value == opening:
            depth += 1
        elif value == closing:
            depth -= 1
            if depth == 0:
                return i
    return None

def parse_tact(source):
    """Return Module with function-like declarations for Tact."""
    if not isinstance(source, str):
        raise TypeError("source must be str")

    tokens, diagnostics = lex(source, Language.TACT)
    functions = []
    i = 0
    n = len(tokens)

    while i < n:
        token = tokens[i]
        value = _v(token)

        is_get = value == "get" and i + 1 < n and _v(tokens[i + 1]) == "fun"
        is_fun = value == "fun"
        is_receive = value == "receive"

        if not (is_get or is_fun or is_receive):
            i += 1
            continue

        getter = is_get
        if is_get:
            name_idx = i + 2
        elif is_receive:
            name = "receive"
            paren = i + 1
            name_idx = None
        else:
            name_idx = i + 1

        if is_fun or is_get:
            if name_idx is None or name_idx >= n or _kind(tokens[name_idx]) not in ("IDENTIFIER", "KEYWORD"):
                i += 1
                continue
            name = _v(tokens[name_idx])
            paren = name_idx + 1

        if paren >= n or _v(tokens[paren]) != "(":
            i += 1
            continue
        close_paren = _matching(tokens, paren, "(", ")")
        if close_paren is None:
            i += 1
            continue
        brace = close_paren + 1
        while brace < n and _v(tokens[brace]) != "{":
            if _v(tokens[brace]) == ";":
                brace = None
                break
            brace += 1
        if brace is None or brace >= n or _v(tokens[brace]) != "{":
            i += 1
            continue
        close_brace = _matching(tokens, brace, "{", "}")
        if close_brace is None:
            diagnostics.append(
                Diagnostic(
                    "TACT-PARSE-001",
                    f"Unterminated body for {name}",
                    DiagnosticSeverity.ERROR,
                    tokens[brace].span,
                )
            )
            i += 1
            continue
        decl_start = token.span.start.offset
        body_start = tokens[brace].span.start.offset
        body_end = tokens[close_brace].span.end.offset
        functions.append(
            FunctionDecl(
                name=name,
                language=Language.TACT,
                parameters=(),
                span=_span(source, decl_start, body_end),
                body_span=_span(source, body_start, body_end),
                is_getter=getter,
            )
        )
        i = close_brace + 1

    end_offset = len(source)
    return Module(
        language=Language.TACT,
        span=_span(source, 0, end_offset),
        functions=tuple(functions),
        diagnostics=tuple(diagnostics),
    )
