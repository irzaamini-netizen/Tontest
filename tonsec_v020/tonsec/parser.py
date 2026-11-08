"""Conservative tokenizer and balanced-brace function extractor."""
import re
from dataclasses import dataclass

@dataclass
class Function:
    name: str
    start: int
    body_start: int
    body_end: int
    text: str
    line: int

TOKEN = re.compile(r'(?P<ws>\s+)|(?P<line>//[^\n]*)|(?P<block>/\*[\s\S]*?\*/)|(?P<string>"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')|(?P<ident>[A-Za-z_$][\w$]*)|(?P<number>0x[0-9a-fA-F]+|\d+)|(?P<op>==|!=|<=|>=|=>|->|::|&&|\|\||.)', re.M)

def tokens(src):
    return [(m.group(), m.start(), m.end(), m.lastgroup) for m in TOKEN.finditer(src) if m.lastgroup not in ('ws','line','block')]

def extract_functions(src):
    ts = tokens(src)
    out = []

    # Record brace depth before each token. Contract-level declarations
    # are allowed at depth 1; declarations inside function bodies are not.
    depths = []
    depth = 0
    for value, token_start, token_end, kind in ts:
        depths.append(depth)
        if value == "{":
            depth += 1
        elif value == "}":
            depth = max(0, depth - 1)

    for i, (value, start, end, kind) in enumerate(ts):
        if depths[i] > 1:
            continue

        if value in ("fun", "function", "get"):
            if i + 1 >= len(ts) or ts[i + 1][3] != "ident":
                continue
            name = ts[i + 1][0]
            search = i + 2
        elif value == "receive":
            name = "receive"
            search = i + 1
        elif value in ("recv_internal", "recv_external", "run_ticktock", "main"):
            name = value
            search = i + 1
        else:
            continue

        # Find the parameter-list opening parenthesis.
        par = None
        for j in range(search, min(search + 180, len(ts))):
            if ts[j][0] == "(":
                par = j
                break
            if ts[j][0] in (";", "{", "}"):
                break

        if par is None:
            continue

        # Match the parameter-list closing parenthesis.
        par_depth = 0
        par_close = None
        for j in range(par, len(ts)):
            if ts[j][0] == "(":
                par_depth += 1
            elif ts[j][0] == ")":
                par_depth -= 1
                if par_depth == 0:
                    par_close = j
                    break

        if par_close is None:
            continue

        # Locate the function body, allowing a return-type annotation.
        brace = None
        for j in range(par_close + 1, min(par_close + 180, len(ts))):
            if ts[j][0] == "{":
                brace = j
                break
            if ts[j][0] in (";", "}"):
                break

        if brace is None:
            continue

        # Match the function body's closing brace.
        body_depth = 0
        close = None
        for j in range(brace, len(ts)):
            if ts[j][0] == "{":
                body_depth += 1
            elif ts[j][0] == "}":
                body_depth -= 1
                if body_depth == 0:
                    close = j
                    break

        if close is None:
            continue

        body_start = ts[brace][2]
        body_end = ts[close][1]
        out.append(
            Function(
                name,
                start,
                body_start,
                body_end,
                src[body_start:body_end],
                src.count('\n', 0, start) + 1,
            )
        )

    unique = {(f.start, f.name): f for f in out}
    return sorted(unique.values(), key=lambda f: f.start)

def line_at(src,offset): return src.count('\n',0,offset)+1
