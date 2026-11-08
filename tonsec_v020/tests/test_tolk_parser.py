import unittest
from tonsec.tolk_parser import parse_tolk

class TolkParserTests(unittest.TestCase):
    def test_regular_functions(self):
        source = "fun onInternalMessage(in: InMessage) { val x = 1; }\nfun onBouncedMessage(msg: InMessageBounced) {}"
        m = parse_tolk(source)
        self.assertEqual([f.name for f in m.functions], ["onInternalMessage", "onBouncedMessage"])
        self.assertEqual(m.functions[0].parameters[0].type_text, "InMessage")

    def test_getters(self):
        m = parse_tolk("get fun currentCounter(): int { return 1; }\nget fun owner(): address { return null; }")
        self.assertEqual([f.name for f in m.functions], ["currentCounter", "owner"])
        self.assertTrue(all(f.is_getter for f in m.functions))
        self.assertEqual(m.functions[0].return_type, "int")

    def test_qualified_names(self):
        m = parse_tolk("fun Storage.load(): Storage { return Storage.fromCell(contract.getData()); }\nfun Storage.save(self) { contract.setData(self.toCell()); }")
        self.assertEqual([f.name for f in m.functions], ["Storage.load", "Storage.save"])

    def test_nested_blocks(self):
        m = parse_tolk('fun outer() { if (true) { val text = "fun fake() {}"; } }')
        self.assertEqual([f.name for f in m.functions], ["outer"])

    def test_contract_functions(self):
        m = parse_tolk("contract Counter { fun increment() { val x = 1; } get fun current(): int { return 1; } }")
        self.assertEqual([f.name for f in m.functions], ["increment", "current"])

    def test_unclosed_body(self):
        m = parse_tolk("fun broken() {")
        self.assertIn("TOLK-PARSE-003", [d.code for d in m.diagnostics])

if __name__ == "__main__":
    unittest.main()
