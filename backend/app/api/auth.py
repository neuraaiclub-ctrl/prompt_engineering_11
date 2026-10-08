from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.database import get_db
from app.models.user import User, Role
from app.models.team import Team, TeamMember
from app.models.registration import Registration
from app.core.security import hash_password, verify_password, create_access_token, revoke_token, is_legacy_hash
from app.core.audit import log_audit_event
from app.core.rate_limiter import enforce_rate_limit

from app.schemas.auth import RegisterSchema, LoginSchema

router = APIRouter(prefix="/auth", tags=["Authentication"])
security_scheme = HTTPBearer(auto_error=False)

@router.post("/register", status_code=status.HTTP_403_FORBIDDEN)
def register(request: Request, payload: RegisterSchema, db: Session = Depends(get_db)):
    """
    Direct participant registration is disabled.
    All participants must register externally via the official Google Form registration process.
    """
    enforce_rate_limit(request, "auth_register", limit=10, window_seconds=60)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Participant registration is managed through the official registration form."
    )

@router.post("/login")
def login(request: Request, payload: LoginSchema, db: Session = Depends(get_db)):
    enforce_rate_limit(request, "auth_login", limit=20, window_seconds=60, identifier=payload.email.lower())
    
    email_lower = payload.email.lower().strip()
    user = db.query(User).filter(func.lower(User.email) == email_lower).first() if hasattr(User, 'email') else None
    
    # Fallback search if exact case differed
    if not user:
        user = db.query(User).filter(User.email == email_lower).first()

    # Fallback search by Team invite_code
    if not user:
        team = db.query(Team).filter(func.lower(Team.invite_code) == email_lower).first()
        if team:
            member = db.query(TeamMember).filter(TeamMember.team_id == team.id).first()
            if member:
                user = db.query(User).filter(User.id == member.user_id).first()

    if not user or not verify_password(payload.password, user.password_hash):
        log_audit_event(
            db,
            action="auth.login_failed",
            target_type="User",
            target_id="unauthenticated",
            actor_user_id=None,
            metadata={"attempted_email": email_lower}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or account is not active."
        )

    # Check User account status
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid credentials or account is not active."
        )

    roles = [r.name for r in user.roles]

    # Check registration status for participant accounts
    if "participant" in roles or "team_leader" in roles:
        reg = db.query(Registration).filter(func.lower(Registration.email) == email_lower).first()
        if reg:
            if reg.registration_status in ["REJECTED", "DISABLED", "WITHDRAWN"] or reg.account_status in ["DISABLED", "LOCKED"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid credentials or account is not active."
                )
            if reg.registration_status != "VERIFIED" and reg.account_status != "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid credentials or account is not active."
                )

    # Resolve Team Membership
    team_member = db.query(TeamMember).filter(TeamMember.user_id == user.id).first()
    team_id = team_member.team_id if team_member else None
    team_name = None
    if team_id:
        team = db.query(Team).filter(Team.id == team_id).first()
        if team:
            team_name = team.name

    # Transparently upgrade legacy password hash to salted PBKDF2
    if is_legacy_hash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.commit()

    token_data = {
        "sub": user.id,
        "email": user.email,
        "roles": roles,
        "team_id": team_id
    }
    token = create_access_token(data=token_data)

    log_audit_event(db, action="auth.login", target_type="User", target_id=user.id, actor_user_id=user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "roles": roles,
            "team_id": team_id,
            "team_name": team_name
        }
    }

@router.post("/logout")
def logout(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)):
    if credentials and credentials.credentials:
        revoke_token(credentials.credentials)
    return {"message": "Successfully logged out"}

@router.get("/fix-61")
def fix_61_users(db: Session = Depends(get_db)):
    from app.models.team import Team, TeamMember
    import uuid
    raw_data = """
shaikhjoya702@gmail.com	shai9395
krutikakokate2025.ainds@mmcoe.edu.in	krut0636
sakshamyadav2024.it@mmcoe.edu.in	saks1977
kartiktikhe2025.it@mmcoe.edu.in	kart7816
rushikeshchadekar2025.it@mmcoe.edu.in	rush6977
piyushsonawane2025.ainds@mmcoe.edu.in	piyu0358
sahebmule7@gmail.com	sahe6924
sohamdegaonkar2025.it@mmcoe.edu.in	soha8590
atharvamangalgi2025.ainds@mmcoe.edu.in	Atha4890
sakshikamble2025.comp@mmcoe.edu.in	saks9007
vedantchandgude2026.it@mmcoe.edu.in	veda0445
virajtarade2024.ainds@mmcoe.edu.in	vira3899
mrunmayidhuldhar2025.it@mmcoe.edu.in	mrun7616
parthdahiphale2025.it@mmcoe.edu.in	part9577
aryanwaghre2025.it@mmcoe.edu.in	arya1542
srujanperkunde2024.ainds@mmcoe.edu.in	sruj0595
machalesamruddhi@gmail.com	mach0144
swarajkavthekar2025.etc@mmcoe.edu.in	swar7974
divyatakhatdeo2025.ainds@mmcoe.edu.in	divy7640
sanikadhore2025.ainds@mmcoe.edu.in	sani9752
rukminiraut444@gmail.com	rukm4323
tanayvidhate2025.ainds@mmcoe.edu.in	tana7448
sohambhopale2025.it@mmcoe.edu.in	soha9385
abhishekmadke2025.ainds@mmcoe.edu.in	abhi6988
likhitrakhade2025.comp@mmcoe.edu.in	likh5977
shivrajtakkalaki2025.etc@mmcoe.edu.in	shiv0376
abdulmerchant2025.ainds@mmcoe.edu.in	abdu5151
atharvaraut2025.elect@mmcoe.edu.in	atha1577
sarthakdeshmukh2024.ainds@mmcoe.edu.in	sart8216
chinmaygade2024.ainds@mmcoe.edu.in	chin9184
shreerajkondedeshmukh@2023.ainds@mmcoe.edu.in	Shre9028
yashkharabe2025.comp@mmcoe.edu.in	yash2732
vedantsuryawanshi2025.elect@mmcoe.edu.in	veda3868
abhishekgodbole2025.comp@mmcoe.edu.in	abhi6905
ojaskute2025.comp@mmcoe.edu.in	ojas9041
aparnabhamare2025.comp@mmcoe.edu.in	apar6801
pratikshachavan2024.comp@mmcoe.edu.in	prat6918
prachimorkhade07@gmail.com	prac8578
sammrudhikulkarni2024.comp@mmcoe.edu.in	samm8191
suyashkolhe2025.etc@mmcoe.edu.in	suya6528
vidhikabra2024.ainds@mmcoe.edu.in	vidh8988
yugantvarekar2024.comp@mmcoe.edu.in	yuga9646
shrutijadhav2025.comp@mmcoe.edu.in	shru8057
radhikasuryatal2024.it@mmcoe.edu.in	radh9205
ishakamthe2025.it@mmcoe.edu.in	isha9527
mrunaldoifode2025.ainds@mmcoe.edu.in	mrun9134
swarakulkarni2025.etc@mmcoe.edu.in	swar1875
atharvapardeshi992@gmail.com	atha0668
utkarshgedam2024.ainds@mmcoe.edu.in	utka6916
krishnamarne2025.ainds@mmcoe.edu.in	kris9073
tusharbarve2025.etc@mmcoe.edu.in	tush1488
sohambhoir2024.etc@mmcoe.edu.in	soha8103
adinathshinde2025.it@mmcoe.edu.in	adin2058
pritideshmukh2026.it@mmcoe.edu.in	prit9121
tejaswinikor2025.ainds@mmcoe.edu.in	teja9574
adityajathar2024.elect@mmcoe.edu.in	adit3358
shreyarathod2024.comp@mmcoe.edu.in	shre9195
shrutishelar2025.it@mmcoe.edu.in	shru9698
shrutimanval104@gmail.com	shru5383
pradeepkawade2024.it@mmcoe.edu.in	prad5627
sanikabobade2026.it@mmcoe.edu.in	sani9138
"""
    lines = [x.strip() for x in raw_data.strip().split("\n") if x.strip()]
    count = 0
    for line in lines:
        parts = line.split()
        if len(parts) != 2: continue
        email, raw_password = parts[0].strip().lower(), parts[1].strip()
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                name=email.split('@')[0],
                password_hash=hash_password(raw_password),
                status="active"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            count += 1
        else:
            user.password_hash = hash_password(raw_password)
            user.status = "active"
            db.commit()
            count += 1
            
        member = db.query(TeamMember).filter(TeamMember.user_id == user.id).first()
        if not member:
            team = Team(
                id=str(uuid.uuid4()),
                name=f"Team {user.name}",
                college="MMCOE",
                hackathon_id="hk-2026",
                invite_code=str(uuid.uuid4())[:8],
                status="active"
            )
            db.add(team)
            db.commit()
            db.refresh(team)
            tm = TeamMember(team_id=team.id, user_id=user.id, role="leader")
            db.add(tm)
            db.commit()
            
    return {"status": "ok", "fixed": count}

