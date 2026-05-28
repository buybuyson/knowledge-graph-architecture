#!/usr/bin/env python3
"""
score.py — Cham output cua LLM voi dap an MAY SINH (khong phai dap an viet san).
Cach chay:
  1) python3 scripts/build_answers.py data/graph.json   # sinh answer_key.GENERATED.json
  2) Cho LLM tra loi 4 cau, luu vao 1 file JSON dang:
     {"Q1":["ten1","ten2"], "Q2":[...], "Q3":[...], "Q4":[...]}
  3) python3 scripts/score.py llm_output.json
Ket qua: precision/recall/F1 tung cau + co dat PASS khong.
LLM khong the bia: dap an doi chieu duoc may tinh lai tu graph moi lan chay.
"""
import json, sys
ak = json.load(open("answer_key.GENERATED.json"))
out = json.load(open(sys.argv[1] if len(sys.argv)>1 else "llm_output.json"))

def norm(xs): return set(x.strip().lower() for x in xs)
print(f"{'Cau':5}{'Precision':>11}{'Recall':>9}{'F1':>7}  Verdict")
allpass=True
for q in ["Q1","Q2","Q3","Q4"]:
    gold = norm(ak[q]["answer_names"])
    pred = norm(out.get(q, []))
    if not pred:
        print(f"{q:5}{'—':>11}{'—':>9}{'—':>7}  THIEU output"); allpass=False; continue
    tp=len(gold&pred); p=tp/len(pred) if pred else 0; r=tp/len(gold) if gold else 0
    f1=2*p*r/(p+r) if (p+r) else 0
    v = "PASS" if f1>=0.9 else ("WEAK" if f1>=0.6 else "FAIL")
    if f1<0.9: allpass=False
    print(f"{q:5}{p:>11.2f}{r:>9.2f}{f1:>7.2f}  {v}")
print("\nTONG:", "PASS — LLM doc dung quan he" if allpass else "CHUA DAT — co cau LLM suy sai")
print("Doi chieu hash:", ak["_integrity_sha256"][:16], "(phai khop EXPECTED_HASH.txt)")
