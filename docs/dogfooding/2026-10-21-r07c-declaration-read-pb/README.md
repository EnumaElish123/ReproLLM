# 2026-10-21 · R07-C D-M / P-B

状态：**具体 D-M 已接受并应用；正式验收正在执行，尚未完成**。
完整质量门和新鲜五项目 Gate A／affected 扩展为 NOT_RUN；不宣称会话已验收或当前最终HEAD CI通过。

基线 aee6488078c3435dcc33b20a68cca8bda0d0ec57；P-A快照34eaea23fc98aceab88681a82e4750e0f907b3bb。
[具体接受](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-read/decision-accepted.json)另立记录；
[原提案](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-read/R07-C_declaration_body_failures.md)及449文件PROPOSED快照保持。

产品只按接受范围修改deps和env规则；先保留exact/qualified信用及D-F/D-S、D-L，再按全仓已知声明正文失败逐包SKIP。
不改engine、scanner、redaction、schema、依赖、presence、旧gold或原资源记录。
未知use、可读但不支持的grammar/结构/include图、listing/framework和充分证书继续OPEN。

真实RED为116failed／19passed，pytest6.93秒，命令7.866499秒；原产品字节前后相同，无收集错误。
首轮七模块GREEN实际2failed／529passed，pytest40.45秒，命令41.380809秒，失败记录完整保留。
两处是测试预期路径错误：恢复loose pyproject后按既有采集顺序优先于requirements；ignore证据路径应为既有配置路径。
只更正这两处断言并另立差异和来源元数据，原接受补丁／产品实现／规范不变。
最终七完整模块GREEN为531passed，pytest42.14秒、命令43.146334秒，零错误／失败。
六个受影响文件Ruff／format及两个产品源Mypy通过，纠正后两测试另作Ruff／format通过。

普通规则政策不激活GPU、Hub、付费或原生GateB；NOT_APPLICABLE，不发布tag/PyPI。
后续在最终相同已提交输入执行一次完整质量门→全部五项目GateA→init/L1/default export和正文失败专项，再记录后推送main并确认精确HEAD五项CI。
