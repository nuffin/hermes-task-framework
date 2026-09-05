# On-Demand Interactive Task Windows

Use this convention only when an explicitly named remote task needs a human to
complete an interactive prerequisite, such as GPG pinentry, MFA, browser login,
or a hardware confirmation.

## Creation rule

Do not create an interactive window for ordinary automated work. Create or reuse
one only after the task identifies a concrete interaction requirement.

The cluster runtime owns SSH and tmux lifecycle. Task-framework supplies this
reference as the task-operation convention; it does not create sessions itself.

## Window identity

On the selected executor, use exactly:

```text
hermes-runtime:task-<hash6>
```

`<hash6>` is the first six characters of the canonical task hash. Reuse the
existing window for the same task. Never substitute a generic shell window or
create a second window for a different task identity.

## Operator handoff

1. Verify the selected executor, canonical task hash, and reason for interaction.
2. Create/reuse `hermes-runtime:task-<hash6>`.
3. Start an interactive shell or the minimal required command in that window.
4. Tell the operator the exact SSH attach command and the exact prompt they should
   expect. Never request, capture, or transmit a secret.
5. After the operator completes the interaction, run a noninteractive readiness
   probe from the same executor. For GPG, use cache-only signing so an absent cache
   fails rather than opening an unattended pinentry.
6. Preserve the window for task audit and later operator attachment until the task
   reaches a terminal state or the operator explicitly asks to close it.

## GPG example

For task `abcdef...` on `ms-a2`, use `hermes-runtime:task-abcdef`. Start a new
interactive shell there. If the GPG key is not cached, pinentry-curses appears in
that pane; the operator attaches, enters the passphrase locally, and returns to
the shell prompt. The scheduled worker then verifies the existing agent cache
without accepting a passphrase or falling back to unsigned commits.
