from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
import redis

from app.config import settings
from app.database import get_auth_db, get_user_db, get_lobby_db


app = FastAPI(title=settings.service_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_redis() -> redis.Redis:
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,
    )


def verify_admin_token(authorization: str = Header(default="")) -> str:
    token = authorization.replace("Bearer ", "") if authorization else ""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No token")
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not admin")
        return payload.get("sub", "admin")
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@app.post("/admin/login", response_model=AdminLoginResponse)
def admin_login(body: AdminLoginRequest):
    if body.username != settings.admin_username or body.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    expire = datetime.now(timezone.utc) + timedelta(hours=8)
    token = jwt.encode(
        {"sub": body.username, "role": "admin", "exp": expire},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return AdminLoginResponse(access_token=token)


@app.get("/admin/stats")
def get_stats(
    _admin: str = Depends(verify_admin_token),
    auth_db: Session = Depends(get_auth_db),
    user_db: Session = Depends(get_user_db),
    lobby_db: Session = Depends(get_lobby_db),
):
    auth_users_count = auth_db.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
    user_profiles_count = user_db.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
    collected_cards_count = user_db.execute(text("SELECT COUNT(*) FROM collected_cards")).scalar() or 0
    total_rooms = lobby_db.execute(text("SELECT COUNT(*) FROM rooms")).scalar() or 0
    active_rooms = lobby_db.execute(text("SELECT COUNT(*) FROM rooms WHERE status = 'active'")).scalar() or 0
    waiting_rooms = lobby_db.execute(text("SELECT COUNT(*) FROM rooms WHERE status = 'waiting'")).scalar() or 0
    finished_rooms = lobby_db.execute(text("SELECT COUNT(*) FROM rooms WHERE status = 'finished'")).scalar() or 0
    total_players = lobby_db.execute(text("SELECT COUNT(*) FROM room_players")).scalar() or 0

    r = _get_redis()
    active_games = 0
    try:
        keys = r.keys(f"{settings.redis_key_prefix}:game:*:active")
        for key in keys:
            if r.get(key) == "1":
                active_games += 1
    except Exception:
        pass
    finally:
        r.close()

    return {
        "auth_users": auth_users_count,
        "user_profiles": user_profiles_count,
        "collected_cards": collected_cards_count,
        "total_rooms": total_rooms,
        "active_rooms": active_rooms,
        "waiting_rooms": waiting_rooms,
        "finished_rooms": finished_rooms,
        "total_players": total_players,
        "active_games": active_games,
    }


@app.get("/admin/users")
def list_users(
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    _admin: str = Depends(verify_admin_token),
    auth_db: Session = Depends(get_auth_db),
    user_db: Session = Depends(get_user_db),
):
    if search:
        q = f"%{search}%"
        auth_rows = auth_db.execute(
            text("SELECT id, username, email, balance, created_at FROM users WHERE username ILIKE :q OR email ILIKE :q ORDER BY id DESC LIMIT :limit OFFSET :offset"),
            {"q": q, "limit": limit, "offset": offset},
        ).fetchall()
        total = auth_db.execute(
            text("SELECT COUNT(*) FROM users WHERE username ILIKE :q OR email ILIKE :q"),
            {"q": q},
        ).scalar() or 0
    else:
        auth_rows = auth_db.execute(
            text("SELECT id, username, email, balance, created_at FROM users ORDER BY id DESC LIMIT :limit OFFSET :offset"),
            {"limit": limit, "offset": offset},
        ).fetchall()
        total = auth_db.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0

    users = []
    for row in auth_rows:
        user_profile = user_db.execute(
            text("SELECT id, balance, created_at FROM users WHERE auth_user_id = :aid"),
            {"aid": row[0]},
        ).fetchone()
        cards_count = user_db.execute(
            text("SELECT COUNT(*) FROM collected_cards WHERE auth_user_id = :aid"),
            {"aid": row[0]},
        ).scalar() or 0
        users.append({
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "auth_balance": float(row[3]),
            "user_balance": float(user_profile[1]) if user_profile else None,
            "cards_count": cards_count,
            "created_at": row[4].isoformat() if row[4] else None,
        })

    return {"users": users, "total": total}


@app.get("/admin/rooms")
def list_rooms(
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    _admin: str = Depends(verify_admin_token),
    lobby_db: Session = Depends(get_lobby_db),
):
    if status_filter:
        rows = lobby_db.execute(
            text("SELECT r.id, r.name, r.host_user_id, r.status, r.winning_pattern, r.created_at, r.updated_at, COUNT(rp.id) as player_count FROM rooms r LEFT JOIN room_players rp ON rp.room_id = r.id WHERE r.status = :sf GROUP BY r.id ORDER BY r.id DESC LIMIT :limit OFFSET :offset"),
            {"sf": status_filter, "limit": limit, "offset": offset},
        ).fetchall()
        total = lobby_db.execute(
            text("SELECT COUNT(*) FROM rooms WHERE status = :sf"),
            {"sf": status_filter},
        ).scalar() or 0
    else:
        rows = lobby_db.execute(
            text("SELECT r.id, r.name, r.host_user_id, r.status, r.winning_pattern, r.created_at, r.updated_at, COUNT(rp.id) as player_count FROM rooms r LEFT JOIN room_players rp ON rp.room_id = r.id GROUP BY r.id ORDER BY r.id DESC LIMIT :limit OFFSET :offset"),
            {"limit": limit, "offset": offset},
        ).fetchall()
        total = lobby_db.execute(text("SELECT COUNT(*) FROM rooms")).scalar() or 0

    rooms = []
    for row in rows:
        rooms.append({
            "id": row[0],
            "name": row[1],
            "host_user_id": row[2],
            "status": row[3],
            "winning_pattern": row[4],
            "created_at": row[5].isoformat() if row[5] else None,
            "updated_at": row[6].isoformat() if row[6] else None,
            "player_count": row[7],
        })

    return {"rooms": rooms, "total": total}


@app.get("/admin/rooms/{room_id}")
def get_room_detail(
    room_id: int,
    _admin: str = Depends(verify_admin_token),
    lobby_db: Session = Depends(get_lobby_db),
):
    room = lobby_db.execute(
        text("SELECT id, name, host_user_id, status, winning_pattern, created_at, updated_at FROM rooms WHERE id = :rid"),
        {"rid": room_id},
    ).fetchone()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    players = lobby_db.execute(
        text("SELECT id, user_id, display_name, joined_at FROM room_players WHERE room_id = :rid ORDER BY joined_at"),
        {"rid": room_id},
    ).fetchall()

    game_state = None
    r = _get_redis()
    try:
        prefix = f"{settings.redis_key_prefix}:game:{room_id}"
        active = r.get(f"{prefix}:active")
        if active:
            drawn = r.lrange(f"{prefix}:drawn", 0, -1)
            pool_size = r.llen(f"{prefix}:pool")
            last_ball = r.get(f"{prefix}:last_ball")
            started_at = r.get(f"{prefix}:started_at")
            game_state = {
                "active": active == "1",
                "drawn_count": len(drawn),
                "pool_remaining": pool_size,
                "last_ball": last_ball,
                "started_at": started_at,
                "drawn_balls": [int(b) for b in drawn],
            }
    except Exception:
        pass
    finally:
        r.close()

    return {
        "room": {
            "id": room[0],
            "name": room[1],
            "host_user_id": room[2],
            "status": room[3],
            "winning_pattern": room[4],
            "created_at": room[5].isoformat() if room[5] else None,
            "updated_at": room[6].isoformat() if room[6] else None,
        },
        "players": [
            {
                "id": p[0],
                "user_id": p[1],
                "display_name": p[2],
                "joined_at": p[3].isoformat() if p[3] else None,
            }
            for p in players
        ],
        "game_state": game_state,
    }


@app.delete("/admin/rooms/{room_id}")
def delete_room(
    room_id: int,
    _admin: str = Depends(verify_admin_token),
    lobby_db: Session = Depends(get_lobby_db),
):
    room = lobby_db.execute(
        text("SELECT id, status FROM rooms WHERE id = :rid"),
        {"rid": room_id},
    ).fetchone()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    lobby_db.execute(text("DELETE FROM room_players WHERE room_id = :rid"), {"rid": room_id})
    lobby_db.execute(text("DELETE FROM rooms WHERE id = :rid"), {"rid": room_id})
    lobby_db.commit()

    return {"detail": "Room deleted", "room_id": room_id}


class BalanceRequest(BaseModel):
    amount: float


@app.post("/admin/users/{auth_user_id}/balance")
def set_user_balance(
    auth_user_id: int,
    body: BalanceRequest,
    _admin: str = Depends(verify_admin_token),
    auth_db: Session = Depends(get_auth_db),
    user_db: Session = Depends(get_user_db),
):
    auth_user = auth_db.execute(
        text("SELECT id FROM users WHERE id = :uid"),
        {"uid": auth_user_id},
    ).fetchone()
    if not auth_user:
        raise HTTPException(status_code=404, detail="Auth user not found")

    auth_db.execute(
        text("UPDATE users SET balance = :bal WHERE id = :uid"),
        {"bal": body.amount, "uid": auth_user_id},
    )
    auth_db.commit()

    user_db.execute(
        text("UPDATE users SET balance = :bal WHERE auth_user_id = :uid"),
        {"bal": body.amount, "uid": auth_user_id},
    )
    user_db.commit()

    return {"detail": "Balance updated", "auth_user_id": auth_user_id, "new_balance": body.amount}


@app.get("/admin/games")
def list_active_games(
    _admin: str = Depends(verify_admin_token),
):
    r = _get_redis()
    games = []
    try:
        keys = r.keys(f"{settings.redis_key_prefix}:game:*:active")
        for key in keys:
            if r.get(key) == "1":
                parts = key.split(":")
                room_id = parts[2]
                prefix = f"{settings.redis_key_prefix}:game:{room_id}"
                drawn = r.lrange(f"{prefix}:drawn", 0, -1)
                pool_size = r.llen(f"{prefix}:pool")
                last_ball = r.get(f"{prefix}:last_ball")
                started_at = r.get(f"{prefix}:started_at")
                players = r.smembers(f"{prefix}:players") if r.exists(f"{prefix}:players") else set()
                games.append({
                    "room_id": int(room_id),
                    "drawn_count": len(drawn),
                    "pool_remaining": pool_size,
                    "last_ball": last_ball,
                    "started_at": started_at,
                    "player_count": len(players),
                })
    except Exception:
        pass
    finally:
        r.close()

    return {"games": games, "total": len(games)}


@app.get("/health")
def health_check():
    return {"status": "ok", "service": settings.service_name}
