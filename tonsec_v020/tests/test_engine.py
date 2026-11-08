import tempfile,unittest
from pathlib import Path
from tonsec.parser import extract_functions
from tonsec.engine import scan,write_report,scan_source
class Tests(unittest.TestCase):
 def test_function_extraction(self): self.assertEqual([f.name for f in extract_functions('contract A { fun transfer() { send_raw_message(x,0); } }')],['transfer'])

 def test_nested_function_like_text_is_not_extracted(self):
  source = """
contract Wallet {
    fun withdraw() {
        fun fake() {
            send_raw_message(x,0);
        }
        val text = "fun also_fake() { }";
        // fun comment_fake() { }
    }
}
"""
  self.assertEqual(
   [f.name for f in extract_functions(source)],
   ["withdraw"]
  )

 def test_file_and_contract_level_functions_are_extracted(self):
  source = """
fun top_level() {
    return;
}
contract Wallet {
    fun transfer() {
        return;
    }
    receive() {
        return;
    }
}
"""
  self.assertEqual(
   [f.name for f in extract_functions(source)],
   ["top_level", "transfer", "receive"]
  )
 def test_unprotected_send_flagged(self): self.assertIn('TON-AUTH-001',[f['rule_id'] for f in scan_source('x.tolk','fun withdraw(){ send_raw_message(x,0); }')[0]])
 def test_guarded_send_not_flagged_by_simple_rule(self): self.assertNotIn('TON-AUTH-001',[f['rule_id'] for f in scan_source('x.tolk','fun withdraw(){ require(sender == owner); send_raw_message(x,0); }')[0]])
 def test_unrelated_require_does_not_hide_unauthorized_send(self):
  source = 'fun withdraw(){ require(amount > 0); send_raw_message(x,0); }'
  self.assertIn('TON-AUTH-001', [f['rule_id'] for f in scan_source('x.tolk',source)[0]])

 def test_helper_call_is_not_assumed_to_be_authorization(self):
  source = 'fun withdraw(){ check_owner(); send_raw_message(x,0); }'
  self.assertIn('TON-AUTH-001', [f['rule_id'] for f in scan_source('x.tolk',source)[0]])


 def test_guarded_helper_before_send_is_recognized(self):
  source = """
fun check_owner() {
    require(sender == owner);
}
fun withdraw() {
    check_owner();
    send_raw_message(x,0);
}
"""
  self.assertNotIn('TON-AUTH-001', [f['rule_id'] for f in scan_source('x.tolk',source)[0]])

 def test_guard_after_send_does_not_protect_send(self):
  source = 'fun withdraw(){ send_raw_message(x,0); require(sender == owner); }'
  self.assertIn('TON-AUTH-001', [f['rule_id'] for f in scan_source('x.tolk',source)[0]])

 def test_each_unprotected_send_gets_a_finding(self):
  source = 'fun withdraw(){ send_raw_message(a,0); send_raw_message(b,0); }'
  findings = [f for f in scan_source('x.tolk',source)[0] if f['rule_id']=='TON-AUTH-001']
  self.assertEqual(len(findings), 2)

 def test_guard_between_sends_only_protects_later_send(self):
  source = """
fun withdraw() {
    send_raw_message(a,0);
    require(sender == owner);
    send_raw_message(b,0);
}
"""
  findings = [f for f in scan_source('x.tolk',source)[0] if f['rule_id']=='TON-AUTH-001']
  self.assertEqual(len(findings), 1)

 def test_helper_send_before_guard_is_not_trusted(self):
  source = """
fun check_owner() {
    send_raw_message(x,0);
    require(sender == owner);
}
fun withdraw() {
    check_owner();
    send_raw_message(y,0);
}
"""
  findings = [f for f in scan_source('x.tolk',source)[0] if f['rule_id']=='TON-AUTH-001']
  self.assertEqual(len(findings), 2)

 def test_ambiguous_same_name_helpers_are_not_trusted(self):
  source = """
fun check_owner() {
    require(sender == owner);
}
fun check_owner() {
    return;
}
fun withdraw() {
    check_owner();
    send_raw_message(x,0);
}
"""
  findings = [f for f in scan_source('x.tolk',source)[0] if f['rule_id']=='TON-AUTH-001']
  self.assertEqual(len(findings), 1)
 def test_jetton_is_info(self):
  f=[x for x in scan_source('x.fc','const op=0x0f8a7ea5;')[0] if x['rule_id']=='TON-ASSET-001'][0]; self.assertEqual(f['severity'],'INFO')
 def test_reports_and_overwrite_protection(self):
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/'src'; src.mkdir(); (src/'a.tolk').write_text('fun f(){send_raw_message(x,0);}')
   r=scan(str(src)); out=Path(d)/'out'; write_report(r,str(out)); self.assertTrue((out/'ton_raw.json').exists())
   with self.assertRaises(FileExistsError): write_report(r,str(out))
if __name__=='__main__': unittest.main()
