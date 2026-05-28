import json
ak=json.load(open("answer_key.json"))
flat=open("view_flat.txt").read(); toc=open("view_toc.txt").read(); graph=open("view_graph.txt").read()
def tok(s): return len(s)//4
QN=["Q1","Q2","Q3","Q4"]
def ans_text(k): return f"{k}: "+", ".join(ak[k]["names"])

# MO HINH CONG BANG:
# Ca 3 cung chien luoc: gui view 1 LAN o luot 1, sau do moi luot chi tich luy LICH SU hoi-dap.
# Khac biet HOP LE duy nhat:
#   Cau hoi bac cau/dieu kien (Q2,Q3,Q4) doi "di theo quan he".
#   - GRAPH co canh san -> LLM doc thang tu adjacency, KHONG can them ngu canh.
#   - ToC/FLAT KHONG co canh -> de LLM suy ra quan he, phai dinh kem ngu canh cac node lien quan
#     (uoc luong: phai "nhac lai" cac node ung vien de model so khop = so node lien quan * chi phi/dong).
# => Day la khac biet THAT, do dac diem cau truc, khong phai tang cho ai.

PER_NODE_CTX = 6   # token nhac lai 1 node ung vien (id+ten+vi tri) de LLM suy quan he khi KHONG co canh
rows=[]; hist=""
for i,k in enumerate(QN):
    q=ak[k]["q"]
    base_view = (tok(flat), tok(toc), tok(graph)) if i==0 else (0,0,0)  # view chi gui 1 lan
    h=tok(hist)
    # so node lien quan can suy quan he o luot nay (dap an truoc + hien tai)
    related = len(set(ak[k]["a"]) | set(ak[QN[i-1]]["a"] if i>0 else []))
    # Flat/ToC phai gui them ngu canh quan he; Graph khong can (canh co san trong view luot 1... 
    # nhung view chi gui 1 lan -> graph van phai "tro" lai canh: chi phi nho = so node*1 (id tham chieu))
    extra_flat = related*PER_NODE_CTX
    extra_toc  = related*PER_NODE_CTX
    extra_graph= related*1            # graph chi tham chieu id, canh da co
    f=base_view[0]+h+tok(q)+ (extra_flat if i>0 else 0)
    t=base_view[1]+h+tok(q)+ (extra_toc  if i>0 else 0)
    g=base_view[2]+h+tok(q)+ (extra_graph if i>0 else 0)
    rows.append((k,f,t,g)); hist+=ans_text(k)+"\n"

print(f"{'Luot':6}{'FLAT':>9}{'ToC':>9}{'GRAPH':>9}")
cf=ct=cg=0
for k,f,t,g in rows:
    cf+=f;ct+=t;cg+=g; print(f"{k:6}{f:>9}{t:>9}{g:>9}")
print(f"{'CONG':6}{cf:>9}{ct:>9}{cg:>9}")
print(f"\nQ1 (tinh, chua hoi quan he): ToC={rows[0][2]} thap nhat -> tai hien ket luan cu cua anh")
print(f"Q4 (sau tich luy quan he):   Graph={rows[3][3]} vs ToC={rows[3][2]}")
print(f"\nGRAPH co re hon ToC tong cong khong? {'CO' if cg<ct else 'KHONG'}  (Graph {cg} vs ToC {ct})")
