# Triton-RISCV Operator Skills

For an existing operator:

1. Call `mcp__triton_riscv__discover_operator`.
2. For risky changes, consult current evidence or call `mcp__triton_riscv__retrieve_operator_memory`.
3. Call `mcp__triton_riscv__check_validation_environment` before live validation.
4. Call `mcp__triton_riscv__validate_operator` with `execute=false` to plan.
5. Call `mcp__triton_riscv__execute_approved_validation` with the exact plan's `run_id` to request host approval and execution.

For a new operator:

1. Obtain name, semantics, PyTorch reference, input/output contract, shapes, dtypes, tolerances and backward requirement.
2. Call `mcp__triton_riscv__prepare_operator_development`.
3. Consult history; if needed call `mcp__triton_riscv__retrieve_operator_memory` with semantics and reference.
4. Generate implementation and independent acceptance-test source using the contract and repository references.
5. Call `mcp__triton_riscv__propose_operator_implementation`; do not directly create tracked files with generic shell/filesystem tools.
6. Call `mcp__triton_riscv__apply_development_proposal` to request approval, then use the validation lifecycle.
