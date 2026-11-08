"""Shared language-neutral syntax model."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class Language(str, Enum):
    FUNC = "func"
    TOLK = "tolk"
    TACT = "tact"
    UNKNOWN = "unknown"


class TokenKind(str, Enum):
    IDENTIFIER = "identifier"
    KEYWORD = "keyword"
    NUMBER = "number"
    STRING = "string"
    OPERATOR = "operator"
    PUNCTUATION = "punctuation"
    EOF = "eof"
    UNKNOWN = "unknown"


class DiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, order=True)
class SourcePosition:
    offset: int
    line: int
    column: int


@dataclass(frozen=True)
class SourceSpan:
    start: SourcePosition
    end: SourcePosition


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    value: str
    span: SourceSpan


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    severity: DiagnosticSeverity
    span: SourceSpan


@dataclass(frozen=True)
class ParameterDecl:
    name: str
    type_text: Optional[str]
    span: SourceSpan


@dataclass(frozen=True)
class FunctionDecl:
    name: str
    language: Language
    parameters: Tuple[ParameterDecl, ...]
    span: SourceSpan
    body_span: Optional[SourceSpan] = None
    return_type: Optional[str] = None
    modifiers: Tuple[str, ...] = ()
    is_getter: bool = False


@dataclass(frozen=True)
class ContractDecl:
    name: str
    language: Language
    span: SourceSpan
    functions: Tuple[FunctionDecl, ...] = ()


@dataclass(frozen=True)
class Module:
    language: Language
    span: SourceSpan
    functions: Tuple[FunctionDecl, ...] = ()
    contracts: Tuple[ContractDecl, ...] = ()
    diagnostics: Tuple[Diagnostic, ...] = ()
