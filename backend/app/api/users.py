from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, Role
from app.core.rbac import get_current_user, require_roles
from app.core.audit import log_audit_event

router = APIRouter(prefix="/users", tags=["Users"])

class RoleGrantSchema(BaseModel):
    role_name: str # participant, team_leader, judge, admin

@router.get("/me")
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    roles = [r.name for r in current_user.roles]
    team_id = current_user.team_membership.team_id if current_user.team_membership else None
    
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "roles": roles,
        "team_id": team_id,
        "affiliation": current_user.affiliation,
        "status": current_user.status
    }

@router.post("/{user_id}/roles", status_code=status.HTTP_201_CREATED)
def grant_role(
    user_id: str,
    payload: RoleGrantSchema,
    admin_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.role_name not in ["participant", "team_leader", "judge", "admin"]:
        raise HTTPException(status_code=422, detail="Invalid role name")

    existing_role = db.query(Role).filter(Role.user_id == user_id, Role.name == payload.role_name).first()
    if existing_role:
        return {"message": "User already holds this role"}

    new_role = Role(user_id=user_id, name=payload.role_name)
    db.add(new_role)
    db.commit()

    log_audit_event(
        db,
        action="role.grant",
        target_type="Role",
        target_id=new_role.id,
        actor_user_id=admin_user.id,
        metadata={"target_user_id": user_id, "role": payload.role_name}
    )

    return {"message": f"Role '{payload.role_name}' granted successfully to user {user_id}"}
