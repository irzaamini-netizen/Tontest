import os,re,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
from .parser import Function, extract_functions, line_at
from .func_parser import parse_func
from .tolk_parser import parse_tolk

EXTS={'.fc','.func','.tolk','.tact','.ts','.js','.py','.txt'}
SKIP={'.git','.venv','venv','node_modules','__pycache__','dist','build'}
SEND=[r'\bsend_raw_message\s*\(',r'\braw_reserve\s*\(',r'\bsend\s*\(']
AUTH_GUARD_IDENTITY = [
    r'\b(sender|msg_sender|context\.sender|sender_address)\b'
]
AUTH_GUARD_ROLE = [
    r'\b(owner|admin|authorized|is_authorized|role)\b'
]
AUTH_GUARD_FUNCTION = [
    r'\b(check_signature|verify_signature|is_authorized|is_owner|only_owner|only_admin)\s*\('
]

def has_auth_guard(source):
    guards = re.finditer(
        r'\b(?:require|throw_if|throw_unless|assert)\s*\(([^;{}]*)\)',
        source,
        re.I
    )
    for match in guards:
        expr = match.group(1)
        if has(AUTH_GUARD_IDENTITY, expr) and has(AUTH_GUARD_ROLE, expr):
            return True
        if has(AUTH_GUARD_FUNCTION, expr):
            return True
    return False
SIG=[r'\bsignature\b',r'\bcheck_signature\b',r'\bcheck_data_signature\b',r'\bverify_signature\b']
REPLAY=[r'\bseqno\b',r'\bvalid_until\b',r'\bquery_id\b',r'\bnonce\b']

def has(patterns,s): return any(re.search(p,s,re.I) for p in patterns)
def has_auth_guard_before(source, offset, helper_guards):
    prefix = source[:offset]

    if has_auth_guard(prefix):
        return True

    for name, guarded in helper_guards.items():
        if guarded and re.search(r'\b' + re.escape(name) + r'\s*\(', prefix):
            return True

    return False



def _functions_from_module(src, module):
    functions = []
    for declaration in module.functions:
        if declaration.body_span is None:
            continue
        body_start = declaration.body_span.start.offset
        body_end = declaration.body_span.end.offset
        functions.append(Function(
            name=declaration.name,
            start=declaration.span.start.offset,
            body_start=body_start,
            body_end=body_end,
            text=src[body_start:body_end],
            line=declaration.span.start.line,
        ))
    return functions


def extract_functions_for_source(path, src):
    suffix = Path(path).suffix.lower()
    if suffix not in {".fc", ".func"}:
        return extract_functions(src)
    return _functions_from_module(src, parse_func(src))


def _diagnostic_record(item):
    return {
        "code": item.code,
        "message": item.message,
        "severity": item.severity.value,
        "line": item.span.start.line,
        "column": item.span.start.column,
        "offset": item.span.start.offset,
    }


def _analyze_source(path, src):
    suffix = Path(path).suffix.lower()
    diagnostics = []

    if suffix in {".fc", ".func", ".tolk"}:
        module = parse_func(src) if suffix in {".fc", ".func"} else parse_tolk(src)
        funcs = _functions_from_module(src, module)
        diagnostics = [_diagnostic_record(d) for d in module.diagnostics]
    else:
        funcs = extract_functions(src)

    findings = []

    helper_groups = {}
    for helper in funcs:
        helper_groups.setdefault(helper.name, []).append(helper)

    helper_guards = {}
    for name, definitions in helper_groups.items():
        summaries = []
        for helper in definitions:
            helper_sends = sorted(
                [m for pattern in SEND for m in re.finditer(pattern, helper.text, re.I)],
                key=lambda m: m.start()
            )
            if helper_sends:
                summaries.append(
                    has_auth_guard_before(helper.text, helper_sends[0].start(), {})
                )
            else:
                summaries.append(has_auth_guard(helper.text))

        # Ambiguous same-name helpers are trusted only if every definition is guarded.
        helper_guards[name] = all(summaries)
    def add(rule,title,severity,confidence,fn,offset,evidence,rationale,limits):
        findings.append({'rule_id':rule,'title':title,'severity':severity,'confidence':confidence,'classification':'UNKNOWN','file':path,'line':line_at(src,offset),'function':fn,'evidence':evidence[:280],'rationale':rationale,'limitations':limits})
    for f in funcs:
        b=f.text
        sends=sorted(
            [m for p in SEND for m in re.finditer(p,b,re.I)],
            key=lambda m: m.start()
        )

        for m in sends:
            if not has_auth_guard_before(b, m.start(), helper_guards):
                add(
                    'TON-AUTH-001',
                    'Outbound message path without visible local authorization guard',
                    'HIGH','MEDIUM',f.name,f.body_start+m.start(),
                    b[max(0,m.start()-90):m.end()+120],
                    'A message-emission primitive appears without a recognized authorization guard before this send.',
                    'This is a lexical prefix check. Branches, scopes, caller authorization, modifiers, and semantic control flow are not resolved.'
                )
        if has(SIG,b) and not has(REPLAY,b):
            m=re.search(SIG[0],b,re.I); add('TON-REPLAY-001','Signature handling without visible replay-domain control','MEDIUM','LOW',f.name,f.body_start+(m.start() if m else 0),b[:240],'Signature-related logic appears without seqno/nonce/query_id/valid_until markers in this function.','Replay protection may be in a helper or signed payload; this is not proof of replayability.')
        m=re.search(r'\bvalid_until\b',b,re.I)
        if m and not re.search(r'\b(now|timestamp|block_time|cur_lt)\b',b,re.I):
            add('TON-TIME-001','Expiry field without visible time comparison','MEDIUM','LOW',f.name,f.body_start+m.start(),b[max(0,m.start()-80):m.end()+120],'valid_until appears without a recognizable current-time comparison in this function.','A helper or language-specific time API may implement the check.')
        m=re.search(r'\bseqno\b',b,re.I)
        if m and not re.search(r'(seqno\s*==|==\s*seqno|seqno\s*\+|seqno\s*!=)',b,re.I):
            add('TON-REPLAY-002','Sequence counter without visible validation/update','LOW','LOW',f.name,f.body_start+m.start(),b[max(0,m.start()-70):m.end()+120],'seqno appears without a recognizable comparison or increment in this function.','State validation may be delegated or expressed indirectly.')
        if has([r'\b(extension|plugin|add_extension|remove_extension|install_extension)\b'],b):
            for m in sends:
                if not has_auth_guard_before(b, m.start(), helper_guards):
                    add(
                        'TON-EXT-001',
                        'Extension-related outbound message without visible local authorization',
                        'HIGH','LOW',f.name,f.body_start+m.start(),
                        b[max(0,m.start()-90):m.end()+120],
                        'Extension/plugin vocabulary co-occurs with this outbound message without a recognized preceding local guard.',
                        'Wallet extension authorization may be enforced elsewhere; confirm lifecycle and installed-authority state.'
                    )
    for opcode,rule,title in [('0x0f8a7ea5','TON-ASSET-001','Jetton transfer opcode marker'),('0x5fcc3d14','TON-ASSET-002','NFT transfer opcode marker')]:
        m=re.search(opcode,src,re.I)
        if m: add(rule,title,'INFO','HIGH','<file>',m.start(),m.group(),'A standard TON asset opcode marker is present.','Presence does not prove correct implementation or a vulnerability.')
    m=re.search(r'\b(sendTransaction|send_transaction|tonConnect|signData)\b',src,re.I)
    if m: add('TON-CLIENT-001','TON Connect/client signing API marker','INFO','HIGH','<file>',m.start(),m.group(),'A TON Connect or client signing API marker is present.','TON Connect connection or signData alone does not grant arbitrary wallet withdrawal authority.')
    return findings, funcs, diagnostics


def scan_source(path, src):
    findings, functions, _ = _analyze_source(path, src)
    return findings, functions


def scan(root):
    from .pipeline import scan_project
    return scan_project(root)


def write_report(report, outdir):
    out = Path(outdir).expanduser()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(
            f"Refusing to overwrite non-empty directory: {out}"
        )

    out.mkdir(parents=True, exist_ok=True)
    (out / "ton_raw.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary = report["summary"]
    lines = [
        "# TON Security Engine — Raw Report",
        f"- Version: {report['engine_version']}",
        f"- Target: `{report['target']}`",
        f"- Files analyzed: {summary['files_analyzed']}",
        f"- Functions extracted: {summary['functions_extracted']}",
        f"- Findings: {summary['findings_total']}",
        f"- Files with diagnostics: {summary['files_with_diagnostics']}",
        f"- Diagnostics: {summary['diagnostics_total']}",
        "",
        "## Findings",
    ]

    for finding in report["findings"]:
        lines += [
            "",
            f"### [{finding['severity']}] {finding['rule_id']} — {finding['title']}",
            f"- Location: `{finding['file']}:{finding['line']}` / `{finding['function']}`",
            f"- Confidence: {finding['confidence']} | Classification: {finding['classification']}",
            f"- Evidence: `{finding['evidence']}`",
            f"- Rationale: {finding['rationale']}",
            f"- Limitation: {finding['limitations']}",
        ]

    lines += ["", "## Parser and Lexer Diagnostics"]
    has_diagnostics = False

    for record in report["files"]:
        for diagnostic in record["diagnostics"]:
            has_diagnostics = True
            lines += [
                "",
                f"### [{diagnostic['severity'].upper()}] {diagnostic['code']}",
                f"- File: `{record['path']}:{diagnostic['line']}:{diagnostic['column']}`",
                f"- Analysis status: {record['analysis_status']}",
                f"- Message: {diagnostic['message']}",
            ]

    if not has_diagnostics:
        lines.append("No parser or lexer diagnostics.")

    lines += ["", "## Known limitations"]
    lines += ["- " + item for item in report["coverage"]["limitations"]]

    (out / "ton_raw.md").write_text(
        "\\n".join(lines),
        encoding="utf-8",
    )
    return str(out)
