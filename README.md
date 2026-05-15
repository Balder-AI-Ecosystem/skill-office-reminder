# skill-office-reminder

Standalone office reminder skill repo for reminder creation and reminder listing.

## Responsibility

This repo owns the office reminder boundary. Core should interact with it only through the shared skill contract.

Capabilities declared in `skill.yaml`:

- `office_reminder.create_reminder`
- `office_reminder.list_reminders`

## Contract

- Mode: `local_plugin`
- Entrypoint: `src.skill_office_reminder.main:Skill`
- Healthcheck: `src.skill_office_reminder.main:healthcheck`
- Core API compatibility: `>=1.0,<2.0`

## Permissions

- `external_actions: false`
- `internet_access: false`
- `file_write: true`
- `read_memory: false`
- `write_memory: false`

## Integration rule

Core integration must stay at the skill boundary defined by `skill.yaml`. Core should not reach into reminder storage or helper modules directly.
## Verification

- Recommended command: `python -m pytest -q`
- Current minimum coverage: manifest and contract smoke tests inside `tests/`

## Implementation status

This repo is still in bridge mode around legacy reminder behavior. The extraction is valid as long as the public contract remains stable and the bridge stays isolated behind the plugin entrypoint.

Current dependency note: the runtime path still resolves the core repo location, so implementation independence is not complete yet.