import json
import csv
from io import StringIO
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.ai import assist
from app.config import settings
from app.connectors.registry import connector_registry
from app.importer import preview_import
from app.chat_agent import analyze_chat
from app.master import mask_master_employee, promotion_candidate
from app.models import (
    AIAssistRequest,
    AccountCreate,
    AccountUpdate,
    AppSettingsUpdate,
    ApprovalRequest,
    ChangeRequestCreate,
    ChatAnalyzeRequest,
    LoginRequest,
    MasterEmployee,
    Platform,
)
from app.security import digest, hash_password, make_token, mask_payload, verify_password
from app.storage import audit, connect, init_db, row_to_dict, rows_to_dicts, utc_now
from app.validation import validate_change_request


app = FastAPI(title="HR Bulk Change Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
CONNECTORS = connector_registry()


@app.on_event("startup")
async def startup() -> None:
    init_db()


PUBLIC_DEV_FALLBACK = {"name": "local-hr", "role": "admin", "can_create": True, "can_update": True, "can_delete": True}


def actor_headers(
    authorization: Annotated[str, Header()] = "",
    x_user_name: Annotated[str, Header(alias="X-User-Name")] = "",
    x_user_role: Annotated[str, Header(alias="X-User-Role")] = "",
) -> dict:
    if authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        with connect() as conn:
            row = row_to_dict(
                conn.execute(
                    """
                    SELECT a.username, a.display_name, a.role, a.can_create, a.can_update, a.can_delete, a.is_active
                    FROM sessions s
                    JOIN accounts a ON a.id = s.account_id
                    WHERE s.token = ?
                    """,
                    (token,),
                ).fetchone()
            )
        if row and row["is_active"]:
            return {
                "name": row["display_name"],
                "username": row["username"],
                "role": row["role"],
                "can_create": bool(row["can_create"]),
                "can_update": bool(row["can_update"]),
                "can_delete": bool(row["can_delete"]),
            }
    if x_user_name and x_user_role:
        return {"name": x_user_name, "role": x_user_role, "can_create": True, "can_update": True, "can_delete": True}
    return PUBLIC_DEV_FALLBACK


def require_role(*roles: str):
    def checker(user: dict = Depends(actor_headers)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="권한이 없습니다.")
        return user

    return checker


def require_permission(permission: str):
    def checker(user: dict = Depends(actor_headers)) -> dict:
        if user["role"] == "admin" or user.get(permission):
            return user
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    return checker


def setting_mask(key: str, value: str | None, is_secret: int) -> str | None:
    if not is_secret:
        return value
    if not value:
        return None
    return f"등록됨 (...{value[-4:]})" if len(value) >= 4 else "등록됨"


def upsert_setting(key: str, value: str | None, is_secret: bool) -> None:
    if value is None or value == "":
        return
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value, is_secret, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, is_secret = excluded.is_secret, updated_at = excluded.updated_at
            """,
            (key, value, 1 if is_secret else 0, utc_now()),
        )


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    with connect() as conn:
        row = row_to_dict(conn.execute("SELECT * FROM accounts WHERE username = ?", (request.username,)).fetchone())
        if not row or not row["is_active"] or not verify_password(request.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
        token = make_token()
        conn.execute("INSERT INTO sessions (token, account_id, created_at) VALUES (?, ?, ?)", (token, row["id"], utc_now()))
    return {
        "token": token,
        "user": {
            "username": row["username"],
            "display_name": row["display_name"],
            "role": row["role"],
            "can_create": bool(row["can_create"]),
            "can_update": bool(row["can_update"]),
            "can_delete": bool(row["can_delete"]),
        },
    }


@app.get("/api/auth/me")
async def me(user: dict = Depends(actor_headers)):
    return user


@app.get("/api/accounts")
async def list_accounts(user: dict = Depends(require_role("admin"))):
    with connect() as conn:
        rows = rows_to_dicts(
            conn.execute(
                "SELECT id, username, display_name, role, can_create, can_update, can_delete, is_active, created_at, updated_at FROM accounts ORDER BY id"
            ).fetchall()
        )
    return rows


@app.post("/api/accounts")
async def create_account(request: AccountCreate, user: dict = Depends(require_role("admin"))):
    now = utc_now()
    with connect() as conn:
        try:
            cursor = conn.execute(
                """
                INSERT INTO accounts
                (username, display_name, password_hash, role, can_create, can_update, can_delete, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.username,
                    request.display_name,
                    hash_password(request.password),
                    request.role,
                    int(request.can_create),
                    int(request.can_update),
                    int(request.can_delete),
                    int(request.is_active),
                    now,
                    now,
                ),
            )
        except Exception as exc:
            raise HTTPException(status_code=409, detail="이미 존재하는 사용자 ID입니다.") from exc
    audit(user["name"], "account_created", None, "accounts", request.model_dump(exclude={"password"}))
    return {"id": cursor.lastrowid, "username": request.username}


@app.patch("/api/accounts/{account_id}")
async def update_account(account_id: int, request: AccountUpdate, user: dict = Depends(require_role("admin"))):
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        return {"ok": True}
    fields = []
    values = []
    for key, value in updates.items():
        if key == "password":
            fields.append("password_hash = ?")
            values.append(hash_password(value))
        else:
            fields.append(f"{key} = ?")
            values.append(int(value) if isinstance(value, bool) else value)
    fields.append("updated_at = ?")
    values.extend([utc_now(), account_id])
    with connect() as conn:
        conn.execute(f"UPDATE accounts SET {', '.join(fields)} WHERE id = ?", values)
    audit(user["name"], "account_updated", None, "accounts", {"account_id": account_id, "fields": list(updates.keys())})
    return {"ok": True}


@app.get("/api/settings")
async def get_settings(user: dict = Depends(require_role("admin"))):
    with connect() as conn:
        rows = rows_to_dicts(conn.execute("SELECT key, value, is_secret, updated_at FROM app_settings ORDER BY key").fetchall())
    values = {row["key"]: setting_mask(row["key"], row["value"], row["is_secret"]) for row in rows}
    return {
        "values": values,
        "notes": [
            "API 키와 비밀번호는 로컬 DB에 저장되며 조회 시 원문을 반환하지 않습니다.",
            "Google Sheets는 공유 제한/권한 설정 후 URL 또는 로컬 export 파일 경로를 등록하는 방식으로 시작합니다.",
            "실제 외부 API 반영은 allow_live_connectors가 true일 때만 허용합니다.",
        ],
    }


@app.post("/api/settings")
async def save_settings(request: AppSettingsUpdate, user: dict = Depends(require_role("admin"))):
    plain_keys = ["llm_provider", "llm_model", "workd_base_url", "shiftee_base_url", "google_sheet_url", "local_master_path"]
    secret_keys = ["openai_api_key", "anthropic_api_key", "gift24_client_id", "gift24_client_secret", "workd_api_key", "shiftee_api_key"]
    payload = request.model_dump()
    for key in plain_keys:
        upsert_setting(key, payload.get(key), False)
    for key in secret_keys:
        upsert_setting(key, payload.get(key), True)
    upsert_setting("allow_live_connectors", "true" if request.allow_live_connectors else "false", False)
    audit(user["name"], "settings_updated", None, "settings", {"keys": plain_keys + [key for key in secret_keys if payload.get(key)]})
    return await get_settings(user)


def _decode_request(row: dict) -> dict:
    item = dict(row)
    item["payload"] = json.loads(item.pop("payload_json"))
    item["target_platforms"] = json.loads(item.pop("target_platforms_json"))
    item["validation_errors"] = json.loads(item.pop("validation_errors_json"))
    item["previews"] = json.loads(item.pop("previews_json"))
    return item


async def build_previews(request: ChangeRequestCreate) -> list[dict]:
    previews = []
    for platform in request.target_platforms:
        connector = CONNECTORS[platform]
        preview = await connector.preview(request.event_type, request.employee)
        previews.append(preview.model_dump(mode="json"))
    return previews


@app.get("/")
async def root():
    return RedirectResponse("/static/index.html")


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "service": "HR Bulk Change Agent",
        "live_connectors": settings.allow_live_connectors,
    }


@app.get("/api/connectors")
async def connectors():
    return [
        {
            "platform": platform.value,
            "live_apply_supported": connector.supports_live_apply,
            "live_apply_enabled": settings.allow_live_connectors and connector.supports_live_apply,
        }
        for platform, connector in CONNECTORS.items()
    ]


@app.get("/api/master-employees")
async def list_master_employees(user: dict = Depends(require_role("viewer", "hr_manager", "approver", "admin"))):
    with connect() as conn:
        rows = rows_to_dicts(conn.execute("SELECT * FROM employee_master ORDER BY employee_id").fetchall())
    employees = []
    for row in rows:
        payload = json.loads(row["payload_json"])
        employees.append(mask_master_employee(payload))
    return employees


@app.post("/api/master-employees")
async def upsert_master_employee(
    request: MasterEmployee,
    user: dict = Depends(require_permission("can_create")),
):
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO employee_master (employee_id, payload_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(employee_id) DO UPDATE SET payload_json = excluded.payload_json, updated_at = excluded.updated_at
            """,
            (request.employee_id, json.dumps(request.model_dump(mode="json"), ensure_ascii=False), now, now),
        )
    audit(user["name"], "master_employee_upserted", request.employee_id, "employee_master", request.model_dump(mode="json"))
    return mask_master_employee(request.model_dump(mode="json"))


@app.delete("/api/master-employees/{employee_id}")
async def delete_master_employee(employee_id: str, user: dict = Depends(require_permission("can_delete"))):
    with connect() as conn:
        conn.execute("DELETE FROM employee_master WHERE employee_id = ?", (employee_id,))
    audit(user["name"], "master_employee_deleted", employee_id, "employee_master", {"employee_id": employee_id})
    return {"ok": True}


@app.post("/api/master-employees/import-csv")
async def import_master_csv(request: Request, user: dict = Depends(require_permission("can_create"))):
    form = await request.form()
    file = form.get("file")
    if file is None or not hasattr(file, "filename"):
        raise HTTPException(status_code=400, detail="업로드 파일이 없습니다.")
    content = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(StringIO(content))
    count = 0
    now = utc_now()
    with connect() as conn:
        for row in reader:
            employee = MasterEmployee(
                employee_id=row.get("employee_id") or row.get("사번") or "",
                name=row.get("name") or row.get("이름") or "",
                department=row.get("department") or row.get("부서"),
                position=row.get("position") or row.get("직책"),
                rank=row.get("rank") or row.get("직급"),
                hire_date=row.get("hire_date") or row.get("입사일") or "",
                initial_pay_grade=int(row.get("initial_pay_grade") or row.get("입사호봉") or 1),
                birth_date=row.get("birth_date") or row.get("생년월일"),
                phone=row.get("phone") or row.get("전화번호"),
                email=row.get("email") or row.get("이메일"),
                status=row.get("status") or row.get("상태") or "active",
            )
            conn.execute(
                """
                INSERT INTO employee_master (employee_id, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(employee_id) DO UPDATE SET payload_json = excluded.payload_json, updated_at = excluded.updated_at
                """,
                (employee.employee_id, json.dumps(employee.model_dump(mode="json"), ensure_ascii=False), now, now),
            )
            count += 1
    audit(user["name"], "master_employee_csv_imported", None, "employee_master", {"filename": file.filename, "count": count})
    return {"count": count}


@app.get("/api/master-employees/template.csv")
async def master_template_csv():
    content = "employee_id,name,department,position,rank,hire_date,initial_pay_grade,birth_date,phone,email,status\n"
    return Response(content=content, media_type="text/csv; charset=utf-8")


@app.get("/api/promotion-candidates")
async def promotion_candidates(eligible_only: bool = True, user: dict = Depends(require_role("viewer", "hr_manager", "approver", "admin"))):
    with connect() as conn:
        rows = rows_to_dicts(conn.execute("SELECT payload_json FROM employee_master ORDER BY employee_id").fetchall())
    candidates = []
    for row in rows:
        employee = MasterEmployee(**json.loads(row["payload_json"]))
        candidate = promotion_candidate(employee).model_dump(mode="json")
        if not eligible_only or candidate["eligible"]:
            candidates.append(candidate)
    return candidates


@app.post("/api/change-requests")
async def create_change_request(
    request: ChangeRequestCreate,
    user: dict = Depends(require_role("hr_manager", "admin")),
):
    validation_errors = validate_change_request(request)
    for platform in request.target_platforms:
        validation_errors.extend(await CONNECTORS[platform].validate(request.event_type, request.employee))
    previews = await build_previews(request)
    now = utc_now()
    payload = request.employee.model_dump(mode="json")
    status = "needs_fix" if validation_errors else "draft"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO employees (employee_id, employee_hash, payload_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(employee_id) DO UPDATE SET payload_json = excluded.payload_json, updated_at = excluded.updated_at
            """,
            (
                request.employee.employee_id,
                digest(request.employee.employee_id),
                json.dumps(payload, ensure_ascii=False),
                now,
                now,
            ),
        )
        cursor = conn.execute(
            """
            INSERT INTO change_requests
            (event_type, employee_id, payload_json, target_platforms_json, requested_by, status, memo,
             validation_errors_json, previews_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.event_type.value,
                request.employee.employee_id,
                json.dumps(payload, ensure_ascii=False),
                json.dumps([platform.value for platform in request.target_platforms], ensure_ascii=False),
                request.requested_by or user["name"],
                status,
                request.memo,
                json.dumps(validation_errors, ensure_ascii=False),
                json.dumps(previews, ensure_ascii=False),
                now,
                now,
            ),
        )
        change_id = cursor.lastrowid
    audit(user["name"], "change_request_created", request.employee.employee_id, "change_requests", request.model_dump(mode="json"))
    return await get_change_request(change_id)


@app.get("/api/change-requests")
async def list_change_requests(user: dict = Depends(require_role("viewer", "hr_manager", "approver", "admin"))):
    with connect() as conn:
        rows = rows_to_dicts(
            conn.execute("SELECT * FROM change_requests ORDER BY id DESC LIMIT 100").fetchall()
        )
    return [_decode_request(row) for row in rows]


@app.get("/api/change-requests/{change_id}")
async def get_change_request(
    change_id: int,
    user: dict = Depends(require_role("viewer", "hr_manager", "approver", "admin")),
):
    with connect() as conn:
        row = row_to_dict(conn.execute("SELECT * FROM change_requests WHERE id = ?", (change_id,)).fetchone())
        results = rows_to_dicts(
            conn.execute(
                "SELECT * FROM platform_results WHERE change_request_id = ? ORDER BY id",
                (change_id,),
            ).fetchall()
        )
    if not row:
        raise HTTPException(status_code=404, detail="변경 요청을 찾을 수 없습니다.")
    decoded = _decode_request(row)
    decoded["platform_results"] = [
        {
            **result,
            "masked_payload": json.loads(result.pop("masked_payload_json")),
        }
        for result in results
    ]
    decoded["payload_masked"] = mask_payload(decoded["payload"])
    return decoded


@app.post("/api/change-requests/{change_id}/approve")
async def approve_change_request(
    change_id: int,
    approval: ApprovalRequest,
    user: dict = Depends(require_role("approver", "admin")),
):
    current = await get_change_request(change_id, user)
    if current["validation_errors"]:
        raise HTTPException(status_code=409, detail="검증 오류가 있는 요청은 승인/실행할 수 없습니다.")
    if current["status"] in {"approved", "completed", "partial_failed"}:
        raise HTTPException(status_code=409, detail="이미 처리된 요청입니다.")
    request = ChangeRequestCreate(
        event_type=current["event_type"],
        employee=current["payload"],
        target_platforms=[Platform(item) for item in current["target_platforms"]],
        requested_by=current["requested_by"],
        memo=current["memo"],
    )
    now = utc_now()
    results = []
    if approval.execute:
        for platform in request.target_platforms:
            result = await CONNECTORS[platform].apply(request.event_type, request.employee)
            results.append(result)
            with connect() as conn:
                conn.execute(
                    """
                    INSERT INTO platform_results
                    (change_request_id, platform, status, message, request_ref, masked_payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        change_id,
                        platform.value,
                        result.status,
                        result.message,
                        result.request_ref,
                        json.dumps(result.masked_payload, ensure_ascii=False),
                        now,
                    ),
                )
    statuses = {result.status for result in results}
    final_status = "completed"
    if "failed" in statuses:
        final_status = "partial_failed"
    elif statuses == {"dry_run"} or not settings.allow_live_connectors:
        final_status = "approved_dry_run"
    with connect() as conn:
        conn.execute(
            """
            UPDATE change_requests
            SET approved_by = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (approval.approver or user["name"], final_status, now, change_id),
        )
    audit(user["name"], "change_request_approved", request.employee.employee_id, "connectors", {"results": [r.model_dump(mode="json") for r in results]})
    return await get_change_request(change_id, user)


@app.post("/api/import/preview")
async def import_preview(
    request: Request,
    user: dict = Depends(require_role("hr_manager", "admin")),
):
    form = await request.form()
    file = form.get("file")
    if file is None or not hasattr(file, "filename"):
        raise HTTPException(status_code=400, detail="업로드 파일이 없습니다.")
    rows = await preview_import(file)
    audit(user["name"], "bulk_import_previewed", None, "import", {"filename": file.filename, "rows": len(rows)})
    return {"rows": rows}


@app.post("/api/ai/assist")
async def ai_assist(
    request: AIAssistRequest,
    user: dict = Depends(require_role("hr_manager", "approver", "admin")),
):
    result = await assist(request)
    audit(user["name"], "ai_assist_requested", request.employee.employee_id, "ai", result)
    return result


@app.post("/api/chat/analyze")
async def chat_analyze(
    request: ChatAnalyzeRequest,
    user: dict = Depends(require_role("hr_manager", "approver", "admin")),
):
    result = await analyze_chat(request)
    audit(user["name"], "chat_analyze_requested", None, "chat", result.model_dump(mode="json"))
    return result
