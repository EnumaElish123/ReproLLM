# nvidia_smi corpus

Canned `nvidia-smi` outputs for M5-T02 hardware capture tests: two-GPU query
CSV, driver query, header text with the CUDA version line, and a `missing`
case used with exit code 127. UUIDs are synthetic; tests verify that only
their SHA-256 hashes enter records. No GPU command is executed by tests.
