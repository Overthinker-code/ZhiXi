from datetime import timedelta
import logging
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.core import security
from app.core.auth_rate_limit import auth_attempt_limiter
from app.core.config import settings
from app.core.request_ids import error_detail, request_id_headers, resolve_request_id
from app.core.security import get_password_hash
from app.models import Log, Token, UserPublic
from app.schemas.common import MessageResponse
from app.schemas.token import PasswordResetRequest
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)

router = APIRouter(tags=["login"])
logger = logging.getLogger(__name__)

_RECOVERY_MESSAGE = "如果该邮箱已注册，我们会发送密码重置说明。"


def _client_host(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _rate_limit_error(*, request_id: str, retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=error_detail(
            code="AUTH_RATE_LIMITED",
            message="尝试次数过多，请稍后再试。",
            request_id=request_id,
        ),
        headers={
            **request_id_headers(request_id),
            "Retry-After": str(retry_after),
        },
    )


def _auth_error(
    *, request_id: str, status_code: int, code: str, message: str
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=error_detail(code=code, message=message, request_id=request_id),
        headers=request_id_headers(request_id),
    )


def _deliver_password_recovery(email: str | None, *, request_id: str) -> None:
    if not email:
        return
    try:
        password_reset_token = generate_password_reset_token(email=email)
        email_data = generate_reset_password_email(
            email_to=email,
            email=email,
            token=password_reset_token,
        )
        send_email(
            email_to=email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    except Exception:
        logger.exception("Password recovery delivery failed request_id=%s", request_id)


@router.post("/login/access-token")
def login_access_token(
    request: Request,
    response: Response,
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    request_id = resolve_request_id(request)
    response.headers["X-Request-ID"] = request_id
    limit_keys = auth_attempt_limiter.keys(
        flow="login",
        client_host=_client_host(request),
        account=form_data.username,
    )
    retry_after = auth_attempt_limiter.retry_after(limit_keys)
    if retry_after is not None:
        raise _rate_limit_error(request_id=request_id, retry_after=retry_after)
    try:
        user = crud.authenticate(
            session=session, email=form_data.username, password=form_data.password
        )
    except Exception:
        logger.exception("Login lookup failed request_id=%s", request_id)
        raise _auth_error(
            request_id=request_id,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="AUTH_SERVICE_UNAVAILABLE",
            message="登录服务暂时不可用，请稍后重试。",
        )
    if not user or not user.is_active:
        auth_attempt_limiter.record(limit_keys)
        raise _auth_error(
            request_id=request_id,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="AUTH_CREDENTIALS_INVALID",
            message="邮箱或密码不正确。",
        )

    # A legitimate login clears only the account bucket. Failed attempts from
    # the same client IP remain bounded to slow password spraying.
    auth_attempt_limiter.clear((limit_keys[1],))

    try:
        login_log = Log(
            user_id=user.id, action="login", details=f"User {user.email} logged in"
        )
        session.add(login_log)
        session.commit()
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return Token(
            access_token=security.create_access_token(
                user.id, expires_delta=access_token_expires
            )
        )
    except Exception:
        session.rollback()
        logger.exception("Login finalization failed request_id=%s", request_id)
        raise _auth_error(
            request_id=request_id,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="AUTH_SERVICE_UNAVAILABLE",
            message="登录服务暂时不可用，请稍后重试。",
        )


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """Validate an access token and return the authenticated user."""
    return current_user


@router.post("/password-recovery/{email}", status_code=status.HTTP_202_ACCEPTED)
def recover_password(
    email: EmailStr,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> MessageResponse:
    """
    用户找回密码
    """
    request_id = resolve_request_id(request)
    response.headers["X-Request-ID"] = request_id
    normalized_email = str(email).strip().casefold()
    limit_keys = auth_attempt_limiter.keys(
        flow="password_recovery",
        client_host=_client_host(request),
        account=normalized_email,
    )
    retry_after = auth_attempt_limiter.retry_after(limit_keys)
    if retry_after is not None:
        raise _rate_limit_error(request_id=request_id, retry_after=retry_after)
    auth_attempt_limiter.record(limit_keys)
    try:
        user = crud.get_user_by_email(session=session, email=normalized_email)
    except Exception:
        logger.exception("Password recovery lookup failed request_id=%s", request_id)
        raise _auth_error(
            request_id=request_id,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="AUTH_SERVICE_UNAVAILABLE",
            message="密码重置服务暂时不可用，请稍后重试。",
        )
    background_tasks.add_task(
        _deliver_password_recovery,
        str(user.email) if user and user.is_active else None,
        request_id=request_id,
    )
    return MessageResponse(message=_RECOVERY_MESSAGE)


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: PasswordResetRequest) -> MessageResponse:
    """
    用户修改密码
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    hashed_password = get_password_hash(password=body.new_password)
    user.hashed_password = hashed_password
    session.add(user)
    session.commit()
    return MessageResponse(message="Password updated successfully")


# @router.post(
#     "/password-recovery-html-content/{email}",
#     dependencies=[Depends(get_current_active_superuser)],
#     response_class=HTMLResponse,
# )
# def recover_password_html_content(email: str, session: SessionDep) -> Any:
#     """
#     HTML Content for Password Recovery
#     """
#     user = crud.get_user_by_email(session=session, email=email)

#     if not user:
#         raise HTTPException(
#             status_code=404,
#             detail="The user with this username does not exist in the system.",
#         )
#     password_reset_token = generate_password_reset_token(email=email)
#     email_data = generate_reset_password_email(
#         email_to=user.email, email=email, token=password_reset_token
#     )

#     return HTMLResponse(
#         content=email_data.html_content, headers={"subject:": email_data.subject}
#     )
