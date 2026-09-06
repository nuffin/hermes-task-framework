# On-Demand Interactive Task Windows

Use this convention only when an explicitly named remote task needs a human to
complete an interactive prerequisite, such as GPG pinentry, MFA, browser login,
or a hardware confirmation.

## Creation rule

Do not create an interactive window for ordinary automated work. Create or reuse
one only after the task identifies a concrete interaction requirement.

A remote runtime adapter owns SSH and tmux lifecycle. This task-framework
reference defines task-operation requirements only; it does not create sessions
itself and does not prescribe a role, suite, or external coordinator.

## Window identity

The task overlay derives one deterministic window identity from the canonical
task hash. Reuse the existing window for the same task. Never substitute a
generic shell window or create a second window for a different task identity.

## Operator handoff

1. Verify the selected executor, canonical task hash, and reason for interaction.
2. Resolve or reuse the receipt-derived task window.
3. Start an interactive shell or the minimal required command in that window.
4. Tell the operator the exact SSH attach command and the exact prompt they should
   expect. Never request, capture, or transmit a secret.
5. After the operator completes the interaction, run a noninteractive readiness
   probe from the same executor. For GPG, use cache-only signing so an absent cache
   fails rather than opening an unattended pinentry.
6. Preserve the window for task audit and later operator attachment until the task
   reaches a terminal state or the operator explicitly asks to close it.
