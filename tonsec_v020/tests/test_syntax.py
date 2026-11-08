import unittest

from tonsec.syntax import (
    ContractDecl, Diagnostic, DiagnosticSeverity, FunctionDecl,
    Language, Module, ParameterDecl, SourcePosition, SourceSpan,
    Token, TokenKind,
)


class SyntaxModelTests(unittest.TestCase):
    def setUp(self):
        self.span = SourceSpan(
            SourcePosition(0, 1, 1),
            SourcePosition(12, 1, 13),
        )

    def test_source_positions(self):
        self.assertEqual(self.span.start.offset, 0)
        self.assertEqual(self.span.end.offset, 12)
        self.assertEqual(self.span.start.column, 1)

    def test_token_model(self):
        token = Token(TokenKind.IDENTIFIER, "transfer", self.span)
        self.assertEqual(token.kind, TokenKind.IDENTIFIER)
        self.assertEqual(token.value, "transfer")

    def test_function_and_parameter_models(self):
        parameter = ParameterDecl("amount", "Int", self.span)
        function = FunctionDecl(
            name="transfer",
            language=Language.TACT,
            parameters=(parameter,),
            span=self.span,
            return_type="Bool",
            modifiers=("public",),
        )
        self.assertEqual(function.parameters[0].name, "amount")
        self.assertEqual(function.language, Language.TACT)
        self.assertEqual(function.return_type, "Bool")

    def test_module_and_contract_models(self):
        function = FunctionDecl("recv", Language.FUNC, (), self.span)
        contract = ContractDecl(
            "Wallet", Language.TACT, self.span, (function,)
        )
        module = Module(
            Language.TACT, self.span, contracts=(contract,)
        )
        self.assertEqual(module.contracts[0].functions[0].name, "recv")

    def test_diagnostic_model(self):
        diagnostic = Diagnostic(
            "PARSE001",
            "Expected closing brace",
            DiagnosticSeverity.ERROR,
            self.span,
        )
        module = Module(
            Language.TOLK, self.span, diagnostics=(diagnostic,)
        )
        self.assertEqual(module.diagnostics[0].code, "PARSE001")
        self.assertEqual(
            module.diagnostics[0].severity,
            DiagnosticSeverity.ERROR,
        )


if __name__ == "__main__":
    unittest.main()
