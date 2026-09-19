# fixture: privacy_custom_params

Privacy experiments with custom parameters (`configs/privacy.yaml`) and a
deliberately tracked `.env` containing an obviously fake OpenAI key — triggers
`env.secret_files_ignored` CRITICAL at Level 0. `trust_remote_code=True` and the
gated `meta-llama` model exercise detection hints and 403 lock paths.

All tokens in this fixture tree are fake and exist only for tests.

M4 Level 2 uses the complete manifest and a mocked HTTP 403 for the primary
model. Its revision yields CRITICAL; tokenizer and chat-template resolution
yield WARNING. The fix hint names `HF_TOKEN`. The dataset resolves exactly and
local hashes pass. Summary (C/W/I/P/S): `1/2/3/43/9`.
