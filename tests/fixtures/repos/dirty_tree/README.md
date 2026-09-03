# fixture: dirty_tree

Repository with post-commit modifications (appended `configs/run.yaml`) and an
untracked `scratch.txt` — triggers `code.clean_tree` and `code.no_untracked`
WARNINGs. The dirty patch feeds `run` capture tests in M5.
