# 未提交的 spec issue 草稿：R07-C D-M-V

状态：本地草稿，未对外提交。建议 label：spec。当前现行规格有意排除此边界，实现与规格无冲突。

建议选择 A，具体是已遍历 Poetry dict value 显式 version 非str 时，在原caller setdefault invalid_structure，
保留所有已提取声明、既有原因和信用，复用D-M。缺失、str、整个非dict、多约束数组、groups和Pipfile不opt in。
官方schema的string字段支持范围界定；全仓SKIP是保守政策选择，不代表隐藏exact存在或Poetry安装失败。
完整A/B、兼容性、未来验收、五项目零适用源证据及精确未应用补丁均见本目录。
须裁决具体predicate/放置、补丁与全仓WARNING→SKIP/孤立exit1→0成本后才执行P-B；当前未实施。
