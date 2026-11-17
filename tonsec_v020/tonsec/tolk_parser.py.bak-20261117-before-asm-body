
from .lexer import lex
from .syntax import (
    Language, Module, FunctionDecl, ParameterDecl,
    SourcePosition, SourceSpan, Diagnostic, DiagnosticSeverity,
)

def _pos(source, offset):
    offset = max(0, min(offset, len(source)))
    line = source.count("\n", 0, offset) + 1
    last = source.rfind("\n", 0, offset)
    return SourcePosition(offset, line, offset - last)

def _span(source, start, end):
    return SourceSpan(_pos(source, start), _pos(source, end))

def _v(token):
    return getattr(token, "value", "")

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

def _text(source, tokens, start, end):
    if start >= end:
        return ""
    return source[
        tokens[start].span.start.offset:
        tokens[end - 1].span.end.offset
    ].strip()

def _split(tokens, start, end):
    result = []
    part = start
    depths = {"(": 0, "[": 0, "{": 0, "<": 0}
    pairs = {")": "(", "]": "[", "}": "{", ">": "<"}
    for i in range(start, end):
        value = _v(tokens[i])
        if value in depths:
            depths[value] += 1
        elif value in pairs:
            key = pairs[value]
            depths[key] = max(0, depths[key] - 1)
        elif value == "," and not any(depths.values()):
            if part < i:
                result.append((part, i))
            part = i + 1
    if part < end:
        result.append((part, end))
    return result

def _parameters(source, tokens, start, end):
    result = []
    for a, b in _split(tokens, start, end):
        colon = None
        depth = 0
        for i in range(a, b):
            value = _v(tokens[i])
            if value in ("(", "[", "<"):
                depth += 1
            elif value in (")", "]", ">"):
                depth = max(0, depth - 1)
            elif value == ":" and depth == 0:
                colon = i
                break
        if colon is None:
            name, typ = _text(source, tokens, a, b), ""
        else:
            name = _text(source, tokens, a, colon)
            typ = _text(source, tokens, colon + 1, b)
        if name:
            result.append(ParameterDecl(
                name=name,
                type_text=typ,
                span=_span(
                    source,
                    tokens[a].span.start.offset,
                    tokens[b - 1].span.end.offset,
                ),
            ))
    return tuple(result)

def parse_tolk(source):
    if not isinstance(source, str):
        raise TypeError("source must be str")

    result = lex(source, Language.TOLK)
    if isinstance(result, tuple) and len(result) == 2:
        tokens, lexer_diagnostics = result
    else:
        tokens = getattr(result, "tokens", ())
        lexer_diagnostics = getattr(result, "diagnostics", ())

    tokens = list(tokens)
    diagnostics = list(lexer_diagnostics or ())
    functions = []
    depth = 0
    i = 0

    while i < len(tokens):
        value = _v(tokens[i])

        if value == "}":
            depth = max(0, depth - 1)
            i += 1
            continue
        if value == "{":
            depth += 1
            i += 1
            continue
        if value != "fun" or depth > 1:
            i += 1
            continue

        fun_index = i
        getter = i > 0 and _v(tokens[i - 1]) == "get"
        declaration_index = i - 1 if getter else i
        name_start = i + 1
        open_paren = None
        j = name_start

        while j < len(tokens):
            value = _v(tokens[j])
            if value == "(":
                open_paren = j
                break
            if value in ("{", "}", ";", "=", "=>"):
                break
            j += 1

        if open_paren is None:
            i += 1
            continue

        name = _text(source, tokens, name_start, open_paren)
        if not name:
            i += 1
            continue

        close_paren = _matching(tokens, open_paren, "(", ")")
        if close_paren is None:
            diagnostics.append(Diagnostic(
                code="TOLK-PARSE-001",
                message=f"Unclosed parameter list for {name}",
                severity=DiagnosticSeverity.ERROR,
                span=_span(
                    source,
                    tokens[fun_index].span.start.offset,
                    tokens[open_paren].span.end.offset,
                ),
            ))
            i = open_paren + 1
            continue

        body_open = close_paren + 1
        while body_open < len(tokens):
            value = _v(tokens[body_open])
            if value == "{" or value in (";", "}"):
                break
            body_open += 1

        if body_open >= len(tokens) or _v(tokens[body_open]) != "{":
            diagnostics.append(Diagnostic(
                code="TOLK-PARSE-002",
                message=f"Function body not found for {name}",
                severity=DiagnosticSeverity.WARNING,
                span=_span(
                    source,
                    tokens[fun_index].span.start.offset,
                    tokens[close_paren].span.end.offset,
                ),
            ))
            i = close_paren + 1
            continue

        body_close = _matching(tokens, body_open, "{", "}")
        if body_close is None:
            diagnostics.append(Diagnostic(
                code="TOLK-PARSE-003",
                message=f"Unclosed function body for {name}",
                severity=DiagnosticSeverity.ERROR,
                span=_span(
                    source,
                    tokens[fun_index].span.start.offset,
                    tokens[body_open].span.end.offset,
                ),
            ))
            i = body_open + 1
            continue

        return_type = None
        if close_paren + 1 < body_open:
            tail = _text(source, tokens, close_paren + 1, body_open)
            if tail.startswith(":"):
                return_type = tail[1:].strip() or None

        functions.append(FunctionDecl(
            name=name,
            language=Language.TOLK,
            parameters=_parameters(
                source, tokens, open_paren + 1, close_paren
            ),
            span=_span(
                source,
                tokens[declaration_index].span.start.offset,
                tokens[body_close].span.end.offset,
            ),
            body_span=_span(
                source,
                tokens[body_open].span.start.offset,
                tokens[body_close].span.end.offset,
            ),
            return_type=return_type,
            modifiers=("get",) if getter else (),
            is_getter=getter,
        ))

        i = body_close + 1
        depth = 0
        for token in tokens[:i]:
            value = _v(token)
            if value == "{":
                depth += 1
            elif value == "}":
                depth = max(0, depth - 1)

    return Module(
        language=Language.TOLK,
        span=_span(source, 0, len(source)),
        functions=tuple(functions),
        diagnostics=tuple(diagnostics),
    )
