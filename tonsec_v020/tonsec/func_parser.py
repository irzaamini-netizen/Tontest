"""Conservative structural parser for top-level FunC functions."""

from .lexer import lex
from .syntax import (
    Diagnostic, DiagnosticSeverity, FunctionDecl, Language,
    Module, ParameterDecl, SourcePosition, SourceSpan, TokenKind,
)


def _position(source, offset):
    before = source[:offset]
    line = before.count("\n") + before.count("\r") - before.count("\r\n") + 1
    last_newline = max(before.rfind("\n"), before.rfind("\r"))
    return SourcePosition(offset, line, offset - last_newline)


def _span(source, start, end):
    return SourceSpan(_position(source, start), _position(source, end))


def _matching_open(tokens, close_index):
    depth = 0
    for i in range(close_index, -1, -1):
        if tokens[i].value == ")":
            depth += 1
        elif tokens[i].value == "(":
            depth -= 1
            if depth == 0:
                return i
    return None


def _split_parameters(tokens, start, end, source):
    result = []
    part_start = start
    paren = bracket = brace = 0

    for i in range(start, end + 1):
        value = tokens[i].value if i < end else ","

        if value == "(":
            paren += 1
        elif value == ")":
            paren -= 1
        elif value == "[":
            bracket += 1
        elif value == "]":
            bracket -= 1
        elif value == "{":
            brace += 1
        elif value == "}":
            brace -= 1

        if value == "," and paren == 0 and bracket == 0 and brace == 0:
            if part_start < i:
                segment = tokens[part_start:i]
                name_token = next(
                    (t for t in reversed(segment)
                     if t.kind == TokenKind.IDENTIFIER),
                    None,
                )

                if name_token is not None:
                    name = name_token.value
                    type_text = source[
                        segment[0].span.start.offset:
                        name_token.span.start.offset
                    ].strip()
                else:
                    name = source[
                        segment[0].span.start.offset:
                        segment[-1].span.end.offset
                    ].strip()
                    type_text = None

                result.append(ParameterDecl(
                    name,
                    type_text or None,
                    _span(
                        source,
                        segment[0].span.start.offset,
                        segment[-1].span.end.offset,
                    ),
                ))
            part_start = i + 1

    return tuple(result)


def parse_func(source):
    """Parse top-level FunC function declarations into the shared model."""
    if not isinstance(source, str):
        raise TypeError("source must be str")

    tokens, lexer_diagnostics = lex(source, Language.FUNC)
    diagnostics = list(lexer_diagnostics)
    functions = []
    depth = 0
    declaration_start = 0
    brace_stack = []
    directive_line = None

    for i, token in enumerate(tokens):
        value = token.value
        line = token.span.start.line

        if depth == 0 and directive_line is not None:
            if line == directive_line:
                continue
            directive_line = None
            declaration_start = i

        if depth == 0 and value in ("#include", "#pragma"):
            directive_line = line
            declaration_start = i + 1
            continue

        if value == "}":
            if depth:
                depth -= 1
                if depth == 0:
                    brace_stack.pop()
                    declaration_start = i + 1
            else:
                diagnostics.append(Diagnostic(
                    "PARSE001",
                    "Unmatched closing brace",
                    DiagnosticSeverity.ERROR,
                    token.span,
                ))
                declaration_start = i + 1
            continue

        if value == "{":
            if depth == 0:
                close_paren = None

                for j in range(i - 1, declaration_start - 1, -1):
                    if tokens[j].value == ")":
                        close_paren = j
                        break
                    if tokens[j].value in (";", "{", "}"):
                        break

                if close_paren is not None:
                    open_paren = _matching_open(tokens, close_paren)
                    name_index = open_paren - 1 if open_paren is not None else -1

                    if (
                        name_index >= declaration_start
                        and tokens[name_index].kind == TokenKind.IDENTIFIER
                    ):
                        prefix = tokens[declaration_start:name_index]

                        if prefix:
                            name_token = tokens[name_index]
                            return_type = source[
                                prefix[0].span.start.offset:
                                prefix[-1].span.end.offset
                            ].strip()

                            parameters = _split_parameters(
                                tokens, open_paren + 1, close_paren, source
                            )

                            body_depth = 1
                            close_body = None

                            for k in range(i + 1, len(tokens)):
                                if tokens[k].value == "{":
                                    body_depth += 1
                                elif tokens[k].value == "}":
                                    body_depth -= 1
                                    if body_depth == 0:
                                        close_body = k
                                        break

                            if close_body is not None:
                                declaration_offset = tokens[
                                    declaration_start
                                ].span.start.offset
                                body_start = token.span.end.offset
                                body_end = tokens[
                                    close_body
                                ].span.start.offset
                                declaration_end = tokens[
                                    close_body
                                ].span.end.offset

                                modifier_names = {
                                    "impure", "inline", "inline_ref",
                                    "auto_apply", "method_id", "operator",
                                }
                                modifiers = tuple(
                                    t.value
                                    for t in tokens[close_paren + 1:i]
                                    if t.value in modifier_names
                                )

                                functions.append(FunctionDecl(
                                    name=name_token.value,
                                    language=Language.FUNC,
                                    parameters=parameters,
                                    span=_span(
                                        source,
                                        declaration_offset,
                                        declaration_end,
                                    ),
                                    body_span=_span(
                                        source,
                                        body_start,
                                        body_end,
                                    ),
                                    return_type=return_type,
                                    modifiers=modifiers,
                                ))

            depth += 1
            brace_stack.append(token)
            continue

        if depth == 0 and value == ";":
            declaration_start = i + 1

    if depth:
        diagnostics.append(Diagnostic(
            "PARSE002",
            "Unclosed top-level brace",
            DiagnosticSeverity.ERROR,
            brace_stack[-1].span,
        ))

    return Module(
        language=Language.FUNC,
        span=_span(source, 0, len(source)),
        functions=tuple(functions),
        diagnostics=tuple(diagnostics),
    )
