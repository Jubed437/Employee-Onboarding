from fastapi import APIRouter, HTTPException

from app.core.security import CurrentUser, create_token
from app.domain.api_schemas import LoginRequest, LoginResponse, Persona
from app.domain.enums import Role

router = APIRouter(prefix="/auth", tags=["auth"])

PERSONAS = (
    Persona(id="admin-1", display_name="Admin", role=Role.ADMIN, team_id="platform"),
    Persona(id="hr-1", display_name="HR Partner", role=Role.HR, team_id="people"),
    Persona(
        id="manager-1",
        display_name="Hiring Manager",
        role=Role.MANAGER,
        team_id="engineering",
    ),
    Persona(id="payroll-1", display_name="Payroll Owner", role=Role.PAYROLL, team_id="payroll"),
)


@router.get("/personas", response_model=list[Persona])
def list_personas() -> list[Persona]:
    return list(PERSONAS)


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    persona = next((item for item in PERSONAS if item.id == request.user_id), None)
    if persona is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNKNOWN_PERSONA", "message": "Unknown persona"},
        )
    user = CurrentUser(id=persona.id, role=persona.role, team_id=persona.team_id)
    return LoginResponse(token=create_token(user), user=persona)
