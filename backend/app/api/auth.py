import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.models.sql_models import AcademicLevelEnum, User

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "exp": expire}, settings.SECRET_KEY, algorithm="HS256"
    )


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token subject")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    logger.info(f"Registering user {body.email} with academic_level: {body.academic_level}")
    
    # Mapping for permissive validation (supports labels and enum values)
    level_map = {
        "PHD": AcademicLevelEnum.PHD,
        "DOUTORAMENTO": AcademicLevelEnum.PHD,
        "MASTERS": AcademicLevelEnum.MASTERS,
        "MESTRADO": AcademicLevelEnum.MASTERS,
        "BACHELORS": AcademicLevelEnum.BACHELORS,
        "LICENCIATURA": AcademicLevelEnum.BACHELORS,
        "HIGHSCHOOL": AcademicLevelEnum.HIGHSCHOOL,
        "ENSINO SECUNDARIO": AcademicLevelEnum.HIGHSCHOOL,
        "ENSINO SECUNDÁRIO": AcademicLevelEnum.HIGHSCHOOL,
    }
    
    level_key = body.academic_level.upper().strip()
    if level_key in level_map:
        level = level_map[level_key]
    else:
        try:
            level = AcademicLevelEnum(body.academic_level)
        except ValueError:
            logger.warning(f"Invalid academic_level received: {body.academic_level}")
            raise HTTPException(status_code=400, detail=f"Invalid academic_level: {body.academic_level}")

    try:
        user = User(
            email=body.email,
            password_hash=hash_password(body.password),
            full_name=body.full_name,
            academic_level=level,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return TokenResponse(access_token=create_token(str(user.id)))
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        # Re-raise as HTTPException(500) so FastAPI handles it and adds CORS headers
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        ) from e


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        print(f"DEBUG: User not found for email {body.email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    is_valid = verify_password(body.password, user.password_hash)
    if not is_valid:
        print(f"DEBUG: Password mismatch for user {body.email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    return TokenResponse(access_token=create_token(str(user.id)))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
