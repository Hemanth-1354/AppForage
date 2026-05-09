"""
AppForge Schema Contracts
Strict Pydantic models that enforce the output shape of every pipeline stage.
Acts as the type-safe boundary between LLM output and system consumption.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Any, Literal
import re


# ── INTENT SCHEMA ─────────────────────────────────────────────────────────────

class CoreEntity(BaseModel):
    name: str
    description: str

class IntentSchema(BaseModel):
    app_name: str
    app_type: str
    core_entities: list[CoreEntity] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    auth_required: bool = True
    payment_required: bool = False
    premium_features: list[str] = Field(default_factory=list)
    admin_features: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    @field_validator("roles")
    @classmethod
    def ensure_roles_not_empty(cls, v):
        if not v:
            return ["admin", "user"]
        return v

    @field_validator("app_name")
    @classmethod
    def sanitize_app_name(cls, v):
        return v.strip() if v else "Unnamed App"


# ── ARCHITECTURE SCHEMA ────────────────────────────────────────────────────────

class PageDef(BaseModel):
    name: str
    route: str
    auth_required: bool = True
    roles_allowed: list[str] = Field(default_factory=list)
    description: str = ""
    components: list[str] = Field(default_factory=list)

class ApiGroup(BaseModel):
    resource: str
    base_path: str
    operations: list[str] = Field(default_factory=list)

class FieldDef(BaseModel):
    name: str
    type: str
    required: bool = True
    unique: bool = False

class RelationDef(BaseModel):
    type: str  # "belongs_to", "has_many", "many_to_many"
    target: str
    field: str

class DataEntity(BaseModel):
    name: str
    fields: list[FieldDef] = Field(default_factory=list)
    relations: list[RelationDef] = Field(default_factory=list)

class AuthModel(BaseModel):
    strategy: str = "jwt"
    roles: list[str] = Field(default_factory=list)
    permissions: dict[str, list[str]] = Field(default_factory=dict)

class ArchitectureSchema(BaseModel):
    pages: list[PageDef] = Field(default_factory=list)
    api_groups: list[ApiGroup] = Field(default_factory=list)
    data_entities: list[DataEntity] = Field(default_factory=list)
    auth_model: AuthModel = Field(default_factory=AuthModel)
    business_rules: list[str] = Field(default_factory=list)


# ── UI SCHEMA ─────────────────────────────────────────────────────────────────

class UIComponent(BaseModel):
    id: str
    type: str
    label: str
    props: dict[str, Any] = Field(default_factory=dict)
    data_source: str = ""
    actions: list[str] = Field(default_factory=list)

class UIPage(BaseModel):
    id: str
    name: str
    route: str
    layout: str = "dashboard"
    auth_required: bool = True
    roles_allowed: list[str] = Field(default_factory=list)
    components: list[UIComponent] = Field(default_factory=list)

class UISchema(BaseModel):
    pages: list[UIPage] = Field(default_factory=list)
    global_components: list[str] = Field(default_factory=list)


# ── API SCHEMA ────────────────────────────────────────────────────────────────

class APIEndpoint(BaseModel):
    id: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    path: str
    auth_required: bool = True
    roles_allowed: list[str] = Field(default_factory=list)
    request_body: dict[str, Any] = Field(default_factory=dict)
    response_body: dict[str, Any] = Field(default_factory=dict)
    query_params: list[str] = Field(default_factory=list)
    description: str = ""

    @field_validator("method", mode="before")
    @classmethod
    def normalize_method(cls, v):
        return str(v).upper() if v else "GET"

class APISchema(BaseModel):
    base_url: str = "/api/v1"
    auth_header: str = "Authorization: Bearer <token>"
    endpoints: list[APIEndpoint] = Field(default_factory=list)


# ── DB SCHEMA ─────────────────────────────────────────────────────────────────

class ForeignKey(BaseModel):
    table: str
    column: str = "id"

class DBColumn(BaseModel):
    name: str
    type: str
    primary_key: bool = False
    nullable: bool = True
    unique: bool = False
    default: Optional[str] = None
    foreign_key: Optional[ForeignKey] = None

class DBTable(BaseModel):
    name: str
    columns: list[DBColumn] = Field(default_factory=list)
    indexes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def ensure_primary_key(self):
        has_pk = any(c.primary_key for c in self.columns)
        if not has_pk and self.columns:
            # Inject id column at front
            pk = DBColumn(
                name="id",
                type="uuid",
                primary_key=True,
                nullable=False,
                unique=True
            )
            self.columns.insert(0, pk)
        return self

class DBSchema(BaseModel):
    tables: list[DBTable] = Field(default_factory=list)


# ── AUTH SCHEMA ───────────────────────────────────────────────────────────────

class RoleDef(BaseModel):
    name: str
    permissions: list[str] = Field(default_factory=list)
    is_premium: bool = False

class MiddlewareRule(BaseModel):
    path_pattern: str
    roles_required: list[str]

class AuthSchema(BaseModel):
    strategy: str = "jwt"
    token_expiry: str = "24h"
    refresh_token: bool = True
    roles: list[RoleDef] = Field(default_factory=list)
    middleware_rules: list[MiddlewareRule] = Field(default_factory=list)


# ── FULL SCHEMA ───────────────────────────────────────────────────────────────

class FullSchema(BaseModel):
    ui_schema: UISchema
    api_schema: APISchema
    db_schema: DBSchema
    auth_schema: AuthSchema


# ── VALIDATION RESULT ─────────────────────────────────────────────────────────

class ValidationIssue(BaseModel):
    layer: str
    field: str
    message: str

class RepairableIssue(BaseModel):
    layer: str
    field: str
    fix: str

class ValidationResult(BaseModel):
    valid: bool
    score: int = Field(ge=0, le=100)
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    repairables: list[RepairableIssue] = Field(default_factory=list)


# ── SCHEMA COERCION UTILITIES ─────────────────────────────────────────────────

def coerce_full_schema(raw: dict) -> dict:
    """
    Attempt to coerce and validate raw LLM output into the FullSchema contract.
    Returns the validated dict, raising ValueError on unrecoverable issues.
    """
    try:
        validated = FullSchema(**raw)
        return validated.model_dump()
    except Exception as e:
        raise ValueError(f"Schema contract violation: {e}")


def coerce_intent(raw: dict) -> dict:
    """Validate and coerce intent extraction output."""
    try:
        return IntentSchema(**raw).model_dump()
    except Exception as e:
        # Graceful fallback with defaults
        return IntentSchema(
            app_name=raw.get("app_name", "App"),
            app_type=raw.get("app_type", "Generic"),
            features=raw.get("features", []),
            roles=raw.get("roles", ["admin", "user"]),
            ambiguities=raw.get("ambiguities", []),
            assumptions=raw.get("assumptions", [str(e)])
        ).model_dump()


def coerce_validation(raw: dict) -> dict:
    """Validate and coerce validation output."""
    try:
        return ValidationResult(**raw).model_dump()
    except Exception:
        return ValidationResult(
            valid=False,
            score=0,
            errors=[ValidationIssue(layer="system", field="validation", message="Validation output was malformed")]
        ).model_dump()
