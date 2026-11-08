import json
from pathlib import Path
CATS={'TON-AUTH-001':'authorization/outbound','TON-EXT-001':'authorization/extension','TON-REPLAY-001':'replay/signature','TON-REPLAY-002':'replay/sequence','TON-TIME-001':'replay/expiry','TON-ASSET-001':'asset/jetton','TON-ASSET-002':'asset/nft','TON-CLIENT-001':'client/ton-connect'}
def compare(sentinel_path,ton_path):
    s=json.loads(Path(sentinel_path).read_text(encoding='utf-8')); t=json.loads(Path(ton_path).read_text(encoding='utf-8'))
    def key(f): return (CATS.get(f.get('rule_id'),f.get('rule_id')),Path(f.get('file','')).name,f.get('function',''))
    sm={}; tm={}
    for f in s.get('findings',[]): sm.setdefault(key(f),[]).append(f)
    for f in t.get('findings',[]): tm.setdefault(key(f),[]).append(f)
    overlap=[]; so=[]; to=[]
    for k in sorted(set(sm)|set(tm)):
        if k in sm and k in tm: overlap.append({'match_key':k,'sentinel':sm[k],'ton':tm[k]})
        elif k in sm: so.extend(sm[k])
        else: to.extend(tm[k])
    return {'schema':'dual-audit.comparison.v1','stage':'POST_ANALYSIS_ONLY','summary':{'sentinel_findings':sum(map(len,sm.values())),'ton_findings':sum(map(len,tm.values())),'overlap_groups':len(overlap),'sentinel_only':len(so),'ton_only':len(to)},'overlap':overlap,'sentinel_only':so,'ton_only':to,'limitations':['Matching is heuristic, not proof of semantic equivalence.','Basename/function matching can collide across directories.','Engines may differ in source normalization and coverage.']}
