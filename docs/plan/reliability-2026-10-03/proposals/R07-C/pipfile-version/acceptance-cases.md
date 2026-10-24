# P-B 未来验收（45组，全部未执行）

本表先于候选实现，由源码合同与官方类型边界独立准备。P-A 当前观察通过不算本表 PASS。每组须参数化展开所列情形，先确认 RED，再最小实现 GREEN；比较完整内部 record 和 finding，不只数量。

| ID | 情形 | 独立预期 |
|---|---|---|
| A01 | both sections / bool | Run packages and dev-packages separately with version=false and true; only file-level invalid_structure is added, including false before fallback. |
| A02 | integers | version=0 and a nonzero integer trigger in a traversed dict; no string coercion/exact credit. |
| A03 | floating point | Finite, inf and nan TOML version values trigger; preserve typed lossless strict-JSON evidence if observed. |
| A04 | lists | Empty, singleton-string and mixed version arrays trigger; no recursive extraction. |
| A05 | mapping | Empty and nested version mappings trigger; no recursive version search. |
| A06 | temporal | Actual TOML date, local time, local datetime and offset datetime are non-str triggers, not manually fabricated TOML null. |
| A07 | absent version | Empty package dict or other-options-only dict without exact raw version key does not trigger; original tuple remains. |
| A08 | all strings | Empty, whitespace, ranges, wildcard, caret, compound and malformed-looking strings add no issue; keep existing stripped specifier/exact. |
| A09 | Pipfile exact contract | Single non-wildcard valid == string keeps exact; bare PEP440 string remains nonexact under allow_bare=False, unlike Poetry. |
| A10 | special exact forms | Existing local/pre/post/dev/epoch == strings remain exact; ===, wildcard == and multiple distinct clauses remain nonexact without a new issue. |
| A11 | direct values | Direct str/int/float/bool/date/list package values do not trigger; preserve existing extractor even where manager accepts direct numeric TOML values. |
| A12 | nested alternative | Package list containing version=false mapping does not trigger because loop value itself is not dict; no descent. |
| A13 | transport without version | url/git/path/file/hg/svn/bzr key plus no version creates no field issue; no source validation. |
| A14 | transport with string | Each recognized extractor transport key plus == or bare string retains exact=None and no new issue, including false/empty transport values. |
| A15 | transport with nonstring | Transport plus present non-str version triggers the field predicate; does not assert installer rejection/precedence/hidden pin. |
| A16 | key identity and extra fields | Only raw lowercase version checked; Version and unrelated unknown extra keys/options are not validated. |
| A17 | section order | Visit packages then dev-packages regardless of physical TOML order; retain each mapping insertion order and declaration count. |
| A18 | section deduplication | Repeated malformed version entries across both sections yield one file issue and no duplicate file evidence; append all original named declarations. |
| A19 | valid sibling section | Wrong-shaped packages with usable dev-packages, and inverse, preserve original parent invalid_structure and uncertain barrier; retain usable siblings. |
| A20 | valid exact sibling | Same-file surviving exact declaration in either section wins for its package; malformed sibling grants no credit and drops nothing. |
| A21 | crossfile exact credit | Captured exact requirements/PEP621/environment/Poetry/Pipfile declaration anywhere retains existential credit before uncertainty, without new origins. |
| A22 | qualified lock credit | Existing qualified same-directory Pipfile.lock package/origin credit wins; default/develop membership and nearest-parent boundaries unchanged. |
| A23 | nonqualifying lock | Wrong-directory/unpaired/wrong-format/missing-package lock stays noncredit; new field cause does not establish a project/lock origin. |
| A24 | no new uncertain barrier | New entry predicate only adds issue; does not add _uncertain_directories. Test child malformed entry versus existing qualified parent lock to preserve association. |
| A25 | DF and DS priority | Associated format-lock failure retains entire prior finding/message/hint/evidence before new DM issue. |
| A26 | DL priority | Incomplete Python/possible-lock DL retains entire prior finding and does not append DM source paths. |
| A27 | DG priority | Existing DM precedes depth-frontier DG; new DM uses only existing DM evidence paths, never lower DG paths. |
| A28 | prior DM cause | New setdefault leaves any prior cause at that path after existing parent checks unchanged; do not alter pre-existing parser assignments. |
| A29 | read/decode returns | Unreadable and invalid syntax stop before value checks, preserve old issue/diagnostics and do not retry/read rejected bytes. |
| A30 | empty and missing sections | Shape-compatible absent/empty tables retain zero declarations, current manifest qualification and existing applicability; not completeness proof. |
| A31 | custom categories | Pipfile docs/tests/other custom categories are not traversed; even version=false there alone does not create a new issue. |
| A32 | line fallback | Inline and expanded package table forms, duplicate names across both sections, and reversed headers preserve exact existing _TomlLineIndex line values; no inferred physical version location. |
| A33 | noncritical trigger with independent use | Unrelated requests version=false with independently imported torch records cause and can change torch warning to SKIPPED/INFO globally. |
| A34 | critical declaration without import | A malformed critical package value already creates same in-use name under old declaration inventory; do not change that current use, only remaining missing-pin outcome. |
| A35 | no critical use and Python veto | Noncritical-only input records issue but adds no critical-use applicability; retain current no-use and empty-result primary-Python veto. |
| A36 | global conservative cost | Unrelated nested source can replace every remaining currently used uncredited critical warning, including promoted critical, with SKIPPED/INFO. Assert complete findings, not counts. |
| A37 | sorted evidence | Keep first matching declaration else first import and every distinct failing logical source in lexical order; already DM-skipped finding may gain a source path. |
| A38 | accepted Poetry isolation | Poetry non-str version remains accepted DM-V trigger with allow_bare=True; Pipfile bare string remains nonexact. PEP621/environment/requirements/Conda prior policies unchanged. |
| A39 | internal record equality | Compare all declaration fields/order, lock package sets/origins, manifest/lock presence, roots/barriers, graph, unparsed, reads, helper/Requirement traces; only allowed new issue differs. |
| A40 | public presentation | Full audit JSON retains SKIP; text may show Findings PASS and skipped count; default export can lose former notable warning. No renderer/export change. |
| A41 | overrides and exits | FAIL-only override does not promote SKIP; suppression/threshold unchanged; isolated warning/promoted critical may exit1->0; independent warning still exits1; exit2/3 unaffected. |
| A42 | consumer stability | Same inventory preserves profile detection, hints, init generated manifest; verify complete outputs in affected future PB matrix. |
| A43 | determinism privacy compatibility | Repeated identical logical inputs produce identical records; no raw malformed value/absolute path/host/user/secret added; legacy/manual default dict empty and old records unchanged. |
| A44 | five sources and local gate | Fresh independent source inventory precedes conditional five-project forecast; no Pipfile means zero applicability, not trigger validation. Future accepted PB requires test-first plus final full quality/Gate A/affected checks. |
| A45 | boundary and resources | No engine/redaction/schema/dependencies/scanner/new sources/groups/solver/version/gold edits; D41 not crossed. PA gates explicit documentation-only NA; GPU/provider/credential/budget/adoption/release blockers stay historical, never PASS. |

既有跨管理器政策、先因、信用、line fallback 必须保持。最终适用质量门一次、fresh 五项目 Gate A 和受影响扩展均按验证流程执行；Gate B 依里程碑/发布激活，资源不足只能 BLOCKED。未接受 A、精确补丁及成本前不得把这些预期写成已执行结果。
