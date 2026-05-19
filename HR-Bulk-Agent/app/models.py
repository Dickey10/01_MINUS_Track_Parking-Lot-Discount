from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ChangeEvent(str, Enum):
    hire = "hire"
    terminate = "terminate"
    leave_start = "leave_start"
    leave_end = "leave_end"
    promotion = "promotion"
    department_transfer = "department_transfer"
    org_change = "org_change"


class Platform(str, Enum):
    gift24 = "gift24"
    workd = "workd"
    shiftee = "shiftee"
    erp = "erp"
    amaranth = "amaranth"
    inhr = "inhr"


class EmployeePayload(BaseModel):
    employee_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    employment_status: str = "active"
    hire_date: str | None = None
    termination_date: str | None = None
    leave_start_date: str | None = None
    leave_end_date: str | None = None
    department: str | None = None
    rank: str | None = None
    title: str | None = None
    employment_type: str | None = None
    company: str | None = None
    email: str | None = None
    phone: str | None = None
    birth_date: str | None = None

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        digits = "".join(ch for ch in value if ch.isdigit())
        return digits or None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Invalid email format")
        return value


class ChangeRequestCreate(BaseModel):
    event_type: ChangeEvent
    employee: EmployeePayload
    target_platforms: list[Platform] = Field(default_factory=lambda: [Platform.gift24, Platform.workd])
    requested_by: str = "hr 담당자"
    memo: str | None = None


class BulkImportRow(ChangeRequestCreate):
    row_number: int


class ApprovalRequest(BaseModel):
    approver: str = "승인자"
    execute: bool = True


class ConnectorPreview(BaseModel):
    platform: Platform
    action: Literal["create", "update", "deactivate", "noop", "unsupported"]
    identifier: str
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ConnectorResult(BaseModel):
    platform: Platform
    status: Literal["dry_run", "success", "failed", "skipped"]
    message: str
    request_ref: str | None = None
    masked_payload: dict[str, Any] = Field(default_factory=dict)


class AIAssistRequest(BaseModel):
    event_type: ChangeEvent
    employee: EmployeePayload
    question: str | None = None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class AccountCreate(BaseModel):
    username: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    password: str = Field(..., min_length=6)
    role: Literal["admin", "hr_manager", "approver", "viewer"] = "viewer"
    can_create: bool = False
    can_update: bool = False
    can_delete: bool = False
    is_active: bool = True


class AccountUpdate(BaseModel):
    display_name: str | None = None
    password: str | None = None
    role: Literal["admin", "hr_manager", "approver", "viewer"] | None = None
    can_create: bool | None = None
    can_update: bool | None = None
    can_delete: bool | None = None
    is_active: bool | None = None


class AppSettingsUpdate(BaseModel):
    llm_provider: str = "openai"
    llm_model: str = "gpt-5.1"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gift24_client_id: str | None = None
    gift24_client_secret: str | None = None
    workd_base_url: str | None = None
    workd_api_key: str | None = None
    shiftee_base_url: str | None = None
    shiftee_api_key: str | None = None
    google_sheet_url: str | None = None
    local_master_path: str | None = None
    allow_live_connectors: bool = False


class MasterEmployee(BaseModel):
    employee_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    department: str | None = None
    position: str | None = None
    rank: str | None = None
    hire_date: str
    initial_pay_grade: int = 1
    birth_date: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str = "active"


class PromotionCandidate(BaseModel):
    employee_id: str
    name: str
    department: str | None = None
    rank: str | None = None
    hire_date: str
    years_of_service: int
    initial_pay_grade: int
    current_pay_grade: int
    next_rank: str | None = None
    required_pay_grade: int
    eligible: bool
    reason: str


class ChatAnalyzeRequest(BaseModel):
    message: str = Field(..., min_length=1)
    default_platforms: list[Platform] = Field(default_factory=lambda: [Platform.gift24, Platform.workd])


class ChatDraftItem(BaseModel):
    row_number: int
    confidence: float = 0.5
    source_text: str
    change_request: ChangeRequestCreate
    missing_fields: list[str] = Field(default_factory=list)
    followup_questions: list[str] = Field(default_factory=list)


class ChatAnalyzeResponse(BaseModel):
    mode: Literal["local_rules", "openai_masked"]
    summary: str
    strategy: list[str]
    drafts: list[ChatDraftItem]
    global_questions: list[str] = Field(default_factory=list)
