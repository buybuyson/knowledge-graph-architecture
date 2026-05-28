# Blind benchmark Round 5: multi-turn token accumulation — Flat vs ToC vs Graph

You are an independent measurer. Follow the problem exactly and **return only the number table in Section 6**. No sample answers are provided — you find and measure them yourself. No method is favored; measure honestly.

## 1. Goal

A non-linear Python codebase (Flask core, 100 functions) was decomposed into 100 nodes. The SAME 100 nodes are presented THREE ways in Section 4: as a Flat list, as a Table-of-Contents (ToC), and as a Graph (with call edges). The ToC lists *where things live* but NOT *how nodes relate*. The Graph adds the relationship edges — that is the only difference.

Unlike a single-shot lookup, this benchmark runs a **4-turn cumulative conversation**: each question reuses the previous answer. The goal is to measure how token_in **accumulates across turns** for each of the three methods, on questions that require *following relationships* (condition, transitivity, cycles, convergence).

The central node for all questions is **N018 (wsgi_app)** — the node with the highest direct fan-out in the graph.

## 2. The three methods

**Method FLAT.** Use ONLY Section 4A. No structure, no edges. To answer a relationship question you must scan the flat list and reason out the relationships yourself.

**Method ToC.** Use ONLY Section 4B. Hierarchical by module, lists nodes, but has NO edges. To answer a relationship question you must reason out how nodes connect (the ToC won't tell you).

**Method GRAPH.** Use ONLY Section 4C. Same nodes PLUS an edge list (caller -> callee). Relationship questions are read directly off the edges.

## 3. Conversation protocol (IMPORTANT — this is what makes it multi-turn)

Answer the 4 questions IN ORDER. Each turn:
- **Turn 1:** context = the full chosen view (4A or 4B or 4C) + Q1. Measure token_in.
- **Turns 2-4:** context = the accumulated Q&A history so far + the new question. You do NOT resend the full view. BUT: if a method needs to re-cite node context to reason out a relationship (because its view had no edges), that re-cited context COUNTS toward its token_in. This is the real cost of lacking edges.

Run all 3 methods independently. Do not let one method's answer leak into another.

## 4A. FLAT view

```
N000 __call__ (flask/app.py:1618)
N001 async_to_sync (flask/app.py:1079)
N002 dispatch_request (flask/app.py:966)
N003 do_teardown_appcontext (flask/app.py:1453)
N004 do_teardown_request (flask/app.py:1420)
N005 ensure_sync (flask/app.py:1065)
N006 finalize_request (flask/app.py:1021)
N007 full_dispatch_request (flask/app.py:992)
N008 handle_exception (flask/app.py:897)
N009 handle_http_exception (flask/app.py:830)
N010 handle_user_exception (flask/app.py:865)
N011 log_exception (flask/app.py:950)
N012 make_default_options_response (flask/app.py:1053)
N013 make_response (flask/app.py:1224)
N014 preprocess_request (flask/app.py:1366)
N015 process_response (flask/app.py:1394)
N016 raise_routing_exception (flask/app.py:562)
N017 request_context (flask/app.py:1501)
N018 wsgi_app (flask/app.py:1566)
N019 _get_session (flask/ctx.py:381)
N020 from_environ (flask/ctx.py:340)
N021 match_request (flask/ctx.py:405)
N022 pop (flask/ctx.py:446)
N023 push (flask/ctx.py:416)
N024 get (flask/ctx.py:68)
N025 pop (flask/ctx.py:79)
N026 setdefault (flask/ctx.py:93)
N027 raise_any (flask/helpers.py:676)
N028 make_response (flask/helpers.py:151)
N029 dumps (flask/json/__init__.py:13)
N030 loads (flask/json/__init__.py:77)
N031 dumps (flask/json/provider.py:166)
N032 loads (flask/json/provider.py:181)
N033 response (flask/json/provider.py:189)
N034 _prepare_response_obj (flask/json/provider.py:75)
N035 dumps (flask/json/provider.py:41)
N036 loads (flask/json/provider.py:59)
N037 response (flask/json/provider.py:89)
N038 check (flask/json/tag.py:73)
N039 tag (flask/json/tag.py:87)
N040 to_json (flask/json/tag.py:77)
N041 to_python (flask/json/tag.py:82)
N042 check (flask/json/tag.py:122)
N043 to_json (flask/json/tag.py:125)
N044 check (flask/json/tag.py:150)
N045 to_json (flask/json/tag.py:153)
N046 check (flask/json/tag.py:163)
N047 to_json (flask/json/tag.py:166)
N048 to_python (flask/json/tag.py:169)
N049 check (flask/json/tag.py:209)
N050 to_json (flask/json/tag.py:212)
N051 to_python (flask/json/tag.py:215)
N052 check (flask/json/tag.py:103)
N053 to_json (flask/json/tag.py:110)
N054 to_python (flask/json/tag.py:114)
N055 check (flask/json/tag.py:181)
N056 to_json (flask/json/tag.py:184)
N057 to_python (flask/json/tag.py:187)
N058 check (flask/json/tag.py:137)
N059 to_json (flask/json/tag.py:140)
N060 to_python (flask/json/tag.py:143)
N061 check (flask/json/tag.py:195)
N062 to_json (flask/json/tag.py:198)
N063 to_python (flask/json/tag.py:201)
N064 _untag_scan (flask/json/tag.py:309)
N065 dumps (flask/json/tag.py:321)
N066 loads (flask/json/tag.py:325)
N067 tag (flask/json/tag.py:289)
N068 untag (flask/json/tag.py:297)
N069 _find_error_handler (flask/sansio/app.py:868)
N070 add_url_rule (flask/sansio/app.py:605)
N071 trap_http_exception (flask/sansio/app.py:893)
N072 extend (flask/sansio/blueprints.py:380)
N073 add_url_rule (flask/sansio/blueprints.py:413)
N074 record (flask/sansio/blueprints.py:224)
N075 add_url_rule (flask/sansio/blueprints.py:87)
N076 _get_exc_class_and_code (flask/sansio/scaffold.py:657)
N077 _method_route (flask/sansio/scaffold.py:284)
N078 add_url_rule (flask/sansio/scaffold.py:368)
N079 get (flask/sansio/scaffold.py:296)
N080 route (flask/sansio/scaffold.py:336)
N081 _endpoint_from_view_func (flask/sansio/scaffold.py:701)
N082 get_signing_serializer (flask/sessions.py:303)
N083 open_session (flask/sessions.py:323)
N084 save_session (flask/sessions.py:337)
N085 get_cookie_domain (flask/sessions.py:175)
N086 get_cookie_httponly (flask/sessions.py:195)
N087 get_cookie_name (flask/sessions.py:171)
N088 get_cookie_partitioned (flask/sessions.py:215)
N089 get_cookie_path (flask/sessions.py:187)
N090 get_cookie_samesite (flask/sessions.py:208)
N091 get_cookie_secure (flask/sessions.py:202)
N092 get_expiration_time (flask/sessions.py:223)
N093 is_null_session (flask/sessions.py:162)
N094 make_null_session (flask/sessions.py:150)
N095 open_session (flask/sessions.py:249)
N096 save_session (flask/sessions.py:263)
N097 should_set_cookie (flask/sessions.py:233)
N098 dispatch_request (flask/views.py:182)
N099 dispatch_request (flask/views.py:78)
```

## 4B. ToC view

```
## flask/app.py
  - N000 __call__
  - N001 async_to_sync
  - N002 dispatch_request
  - N003 do_teardown_appcontext
  - N004 do_teardown_request
  - N005 ensure_sync
  - N006 finalize_request
  - N007 full_dispatch_request
  - N008 handle_exception
  - N009 handle_http_exception
  - N010 handle_user_exception
  - N011 log_exception
  - N012 make_default_options_response
  - N013 make_response
  - N014 preprocess_request
  - N015 process_response
  - N016 raise_routing_exception
  - N017 request_context
  - N018 wsgi_app
## flask/ctx.py
  - N019 _get_session
  - N020 from_environ
  - N021 match_request
  - N022 pop
  - N023 push
  - N024 get
  - N025 pop
  - N026 setdefault
## flask/helpers.py
  - N027 raise_any
  - N028 make_response
## flask/json/__init__.py
  - N029 dumps
  - N030 loads
## flask/json/provider.py
  - N031 dumps
  - N032 loads
  - N033 response
  - N034 _prepare_response_obj
  - N035 dumps
  - N036 loads
  - N037 response
## flask/json/tag.py
  - N038 check
  - N039 tag
  - N040 to_json
  - N041 to_python
  - N042 check
  - N043 to_json
  - N044 check
  - N045 to_json
  - N046 check
  - N047 to_json
  - N048 to_python
  - N049 check
  - N050 to_json
  - N051 to_python
  - N052 check
  - N053 to_json
  - N054 to_python
  - N055 check
  - N056 to_json
  - N057 to_python
  - N058 check
  - N059 to_json
  - N060 to_python
  - N061 check
  - N062 to_json
  - N063 to_python
  - N064 _untag_scan
  - N065 dumps
  - N066 loads
  - N067 tag
  - N068 untag
## flask/sansio/app.py
  - N069 _find_error_handler
  - N070 add_url_rule
  - N071 trap_http_exception
## flask/sansio/blueprints.py
  - N072 extend
  - N073 add_url_rule
  - N074 record
  - N075 add_url_rule
## flask/sansio/scaffold.py
  - N076 _get_exc_class_and_code
  - N077 _method_route
  - N078 add_url_rule
  - N079 get
  - N080 route
  - N081 _endpoint_from_view_func
## flask/sessions.py
  - N082 get_signing_serializer
  - N083 open_session
  - N084 save_session
  - N085 get_cookie_domain
  - N086 get_cookie_httponly
  - N087 get_cookie_name
  - N088 get_cookie_partitioned
  - N089 get_cookie_path
  - N090 get_cookie_samesite
  - N091 get_cookie_secure
  - N092 get_expiration_time
  - N093 is_null_session
  - N094 make_null_session
  - N095 open_session
  - N096 save_session
  - N097 should_set_cookie
## flask/views.py
  - N098 dispatch_request
  - N099 dispatch_request
```

## 4C. GRAPH view

```
NODES:
N000 __call__
N001 async_to_sync
N002 dispatch_request
N003 do_teardown_appcontext
N004 do_teardown_request
N005 ensure_sync
N006 finalize_request
N007 full_dispatch_request
N008 handle_exception
N009 handle_http_exception
N010 handle_user_exception
N011 log_exception
N012 make_default_options_response
N013 make_response
N014 preprocess_request
N015 process_response
N016 raise_routing_exception
N017 request_context
N018 wsgi_app
N019 _get_session
N020 from_environ
N021 match_request
N022 pop
N023 push
N024 get
N025 pop
N026 setdefault
N027 raise_any
N028 make_response
N029 dumps
N030 loads
N031 dumps
N032 loads
N033 response
N034 _prepare_response_obj
N035 dumps
N036 loads
N037 response
N038 check
N039 tag
N040 to_json
N041 to_python
N042 check
N043 to_json
N044 check
N045 to_json
N046 check
N047 to_json
N048 to_python
N049 check
N050 to_json
N051 to_python
N052 check
N053 to_json
N054 to_python
N055 check
N056 to_json
N057 to_python
N058 check
N059 to_json
N060 to_python
N061 check
N062 to_json
N063 to_python
N064 _untag_scan
N065 dumps
N066 loads
N067 tag
N068 untag
N069 _find_error_handler
N070 add_url_rule
N071 trap_http_exception
N072 extend
N073 add_url_rule
N074 record
N075 add_url_rule
N076 _get_exc_class_and_code
N077 _method_route
N078 add_url_rule
N079 get
N080 route
N081 _endpoint_from_view_func
N082 get_signing_serializer
N083 open_session
N084 save_session
N085 get_cookie_domain
N086 get_cookie_httponly
N087 get_cookie_name
N088 get_cookie_partitioned
N089 get_cookie_path
N090 get_cookie_samesite
N091 get_cookie_secure
N092 get_expiration_time
N093 is_null_session
N094 make_null_session
N095 open_session
N096 save_session
N097 should_set_cookie
N098 dispatch_request
N099 dispatch_request
EDGES (caller -> callee):
N000 -> N018
N002 -> N005,N012,N016
N003 -> N005,N027
N004 -> N005,N027
N005 -> N001
N006 -> N013,N015,N028
N007 -> N002,N006,N010,N014,N098,N099
N008 -> N005,N006,N011,N069
N009 -> N005,N069
N010 -> N005,N009,N069,N071
N013 -> N033,N037
N014 -> N005
N015 -> N005,N019,N084,N093,N096
N017 -> N020
N018 -> N007,N008,N017,N022,N023,N025,N033,N037
N019 -> N083,N094,N095
N022 -> N003,N004,N024,N027,N079
N023 -> N019,N021
N024 -> N079
N025 -> N022
N028 -> N013
N029 -> N026,N031,N035,N065
N030 -> N032,N036,N066
N031 -> N026,N029,N035,N065
N032 -> N030,N036,N066
N033 -> N026,N029,N031,N034,N035,N065
N037 -> N029,N031,N034,N035,N065
N039 -> N040,N043,N045,N047,N050,N053,N056,N059,N062
N043 -> N039,N067
N045 -> N039,N067
N053 -> N039,N067
N059 -> N039,N067
N064 -> N068
N065 -> N029,N031,N035,N039,N067
N066 -> N030,N032,N036,N064
N067 -> N038,N039,N042,N044,N046,N049,N052,N055,N058,N061
N068 -> N041,N048,N051,N054,N057,N060,N063
N069 -> N024,N076,N079
N070 -> N022,N024,N025,N079,N081
N073 -> N070,N074,N075,N078
N075 -> N022,N025,N026,N070,N073,N078,N081
N077 -> N080
N079 -> N077
N080 -> N022,N025,N070,N073,N075,N078
N082 -> N072
N083 -> N024,N030,N032,N036,N066,N079,N082,N087
N084 -> N029,N031,N035,N065,N082,N085,N086,N087,N088,N089,N090,N091,N092,N097
N098 -> N005
```

## 5. The four cumulative questions

All answers are LISTS OF NODE NAMES. Answer with names only, one per line.

**Q1 — direct lookup (static):**
Which nodes does N018 (wsgi_app) call DIRECTLY?

**Q2 — conditional filter (reuses Q1):**
Among the Q1 nodes, which ones THEMSELVES call 2 or more nodes (out-degree >= 2)?

**Q3 — transitive + cycle (reuses Q2):**
Following onward from the Q2 nodes, which reachable nodes lie inside a dependency CYCLE (a path that loops back to itself)?

**Q4 — convergence (reuses Q2):**
What is the set of ALL nodes that the Q2 nodes call directly (the next hop)?

## 6. Result format (return ONLY this part)

Token-counting convention (use EXACTLY this — same as prior rounds so results compare):
- Split text into units by the regex `[A-Za-z0-9_]+` or a single non-whitespace/non-alphanumeric character.
- Each unit counts as `1 + floor((length-1)/6)` tokens.
- token_in = tokens of the ENTIRE context you loaded that turn (view/history/question).

```
AI: <your AI name>
Turn | FLAT.token_in | ToC.token_in | GRAPH.token_in | answers_agree?
 Q1  |               |              |                |
 Q2  |               |              |                |
 Q3  |               |              |                |
 Q4  |               |              |                |
TOTAL|               |              |                |
```

After the table, write exactly 3 comment lines:
1. Which method has the lowest TOTAL token_in, and which wins at Q1 alone (static).
2. At which turn (if any) does GRAPH overtake ToC on cumulative token_in?
3. Did any method produce a DIFFERENT answer to any question? (accuracy check — list which.)

---
*Source: Flask (BSD-3-Clause). The 100 nodes are identical across 4A/4B/4C; only the presence of edges differs. To verify the questions' ground-truth answers independently, run the companion Verification Kit (build_answers.py regenerates them from the graph with a SHA-256 integrity hash).*
