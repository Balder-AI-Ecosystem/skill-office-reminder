# UPDATE PLAN — skill-office-reminder

> Audit date: 2026-04-21 | Grade: **C** | Priority: High

---

## Vấn đề tìm thấy

### 1. Schemas chưa khai báo properties (CRITICAL)
2 capabilities dùng schema rỗng.

### 2. `dependencies = []` — gây hiểu nhầm
Phụ thuộc `OfficeAssistantModule` nhưng khai báo empty deps.

### 3. Test coverage tối thiểu
Chỉ manifest check.

### 4. Chỉ 2 capabilities — có thể thiếu
Cần biết 2 capabilities là gì để đánh giá đầy đủ. Nếu chỉ là `set_reminder` và `list_reminders`, còn thiếu `delete_reminder`, `snooze_reminder`.

---

## Fix cần làm

### Fix 1 — Cập nhật schemas trong skill.yaml

Dựa trên pattern phổ biến của office reminders:

```yaml
# office_reminder.set_reminder (giả định capability ID)
input_schema:
  type: object
  required: [title, remind_at]
  properties:
    title:
      type: string
      description: "Reminder message or title"
      minLength: 1
    remind_at:
      type: string
      description: "ISO 8601 datetime for the reminder (e.g. '2026-04-22T09:00:00+07:00')"
    recurrence:
      type: ["string", "null"]
      description: "Recurrence rule (e.g. 'daily', 'weekly', RRULE string)"
    notes:
      type: ["string", "null"]
    dry_run:
      type: boolean
      default: false
    confirmed:
      type: boolean
      default: false
    confirmation_token:
      type: ["string", "null"]
  additionalProperties: false
output_schema:
  type: object
  required: [status]
  properties:
    status:
      type: string
      enum: [ok, error, preview, confirmation_required]
    reminder_id: {type: ["string", "null"]}
    remind_at: {type: ["string", "null"]}
    preview: {type: object}
    confirmation_token: {type: ["string", "null"]}
    detail: {type: ["string", "null"]}

# office_reminder.list_reminders (giả định capability ID)
input_schema:
  type: object
  properties:
    days_ahead:
      type: integer
      default: 7
      minimum: 1
      maximum: 30
    include_past:
      type: boolean
      default: false
    max_results:
      type: integer
      default: 20
      maximum: 100
  additionalProperties: false
output_schema:
  type: object
  required: [status]
  properties:
    status: {type: string, enum: [ok, error]}
    reminders:
      type: array
      items:
        type: object
        properties:
          id: {type: string}
          title: {type: string}
          remind_at: {type: string}
          recurrence: {type: ["string", "null"]}
          status: {type: string, enum: [pending, done, snoozed]}
    total: {type: integer}
```

**Lưu ý:** Cần xem actual capability IDs trong `skill.yaml` để điền đúng. Schema trên là best-guess.

### Fix 2 — Sửa pyproject.toml

```toml
[project]
# Depends on OfficeAssistantModule from core ecosystem.
# Core must be on sys.path (injected by JARVIS loader).
dependencies = []  # runtime: ecosystem.domains.office (injected)
```

### Fix 3 — Thêm functional tests

```python
# tests/test_execute.py
from unittest.mock import MagicMock, patch

def make_req(capability_id, **params):
    req = MagicMock()
    req.capability_id = capability_id
    req.parameters = params
    return req

def test_list_reminders_returns_list():
    from src.skill_office_reminder.main import Skill
    skill = Skill()
    # Use actual capability ID from skill.yaml
    cap_id = [c for c in skill.manifest().capabilities if "list" in c.id.lower()][0].id
    with patch.object(skill, '_office_module') as mock_office:
        getattr(mock_office, cap_id.split(".")[-1], mock_office.list_reminders).return_value = {
            "status": "ok", "reminders": [], "total": 0
        }
        result = skill.execute(make_req(cap_id, days_ahead=7))
    assert result["status"] == "ok"

def test_set_reminder_dry_run_preview():
    from src.skill_office_reminder.main import Skill
    skill = Skill()
    cap_id = [c for c in skill.manifest().capabilities if "set" in c.id.lower() or "create" in c.id.lower()][0].id
    with patch.object(skill, '_office_module') as mock_office:
        mock_office.set_reminder.return_value = {"status": "preview", "preview": {}}
        result = skill.execute(make_req(
            cap_id,
            title="Test reminder",
            remind_at="2026-04-22T09:00:00+07:00",
            dry_run=True
        ))
    assert result["status"] in ("preview", "confirmation_required", "ok")

def test_unknown_capability_raises():
    from src.skill_office_reminder.main import Skill
    import pytest
    skill = Skill()
    with pytest.raises((ValueError, NotImplementedError)):
        skill.execute(make_req("office_reminder.unknown"))
```

### Fix 4 — Cân nhắc thêm capabilities

Nếu chưa có, thêm:
- `office_reminder.delete_reminder` — xóa reminder theo ID
- `office_reminder.snooze_reminder` — hoãn reminder thêm N phút/giờ

---

## Không cần làm
- `OfficeAssistantModule` delegation pattern đúng
- Không cần thay đổi permissions
