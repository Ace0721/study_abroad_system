from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.major import Major
from models.role import Role
from models.university import University
from models.user import User
from utils.enums import RoleCode
from utils.seed_defs import UNIVERSITY_SEED_DATA
from utils.security import hash_password


def seed_initial_data(session: Session) -> None:
    _seed_roles(session)
    _seed_universities_and_majors(session)
    _seed_users(session)
    session.commit()


def _seed_roles(session: Session) -> None:
    role_defs = [
        (RoleCode.ANU_OFFICER.value, "澳洲国立大学批复专员"),
        (RoleCode.USYD_OFFICER.value, "悉尼大学批复专员"),
        (RoleCode.UNSW_OFFICER.value, "新南威尔士大学批复专员"),
        (RoleCode.AGENT_A.value, "国内代理专员 A"),
        (RoleCode.AGENT_B.value, "国内代理专员 B"),
        (RoleCode.NATIONAL_REVIEWER.value, "国家留学管理机构审查员"),
    ]
    for role_code, role_name in role_defs:
        exists = session.execute(select(Role).where(Role.role_code == role_code)).scalar_one_or_none()
        if exists:
            continue
        session.add(
            Role(
                role_code=role_code,
                role_name=role_name,
                description=f"预置角色：{role_name}",
            )
        )
    session.flush()


def _seed_universities_and_majors(session: Session) -> None:
    for uni_code, uni_name, total_quota, majors in UNIVERSITY_SEED_DATA:
        uni = session.execute(
            select(University).where(University.university_code == uni_code)
        ).scalar_one_or_none()
        if not uni:
            uni = University(
                university_code=uni_code,
                university_name=uni_name,
                total_quota=total_quota,
                used_quota=0,
                description=f"{uni_name} 预置学校",
            )
            session.add(uni)
            session.flush()
        for major_code, major_name, major_quota in majors:
            major_exists = session.execute(
                select(Major).where(
                    Major.university_id == uni.id,
                    Major.major_code == major_code,
                )
            ).scalar_one_or_none()
            if major_exists:
                continue
            session.add(
                Major(
                    university_id=uni.id,
                    major_code=major_code,
                    major_name=major_name,
                    major_quota=major_quota,
                    used_quota=0,
                    is_active=True,
                )
            )
    session.flush()


def _seed_users(session: Session) -> None:
    now = datetime.utcnow()
    role_map = {
        role.role_code: role.id for role in session.execute(select(Role)).scalars().all()
    }
    uni_map = {
        uni.university_code: uni.id
        for uni in session.execute(select(University)).scalars().all()
    }

    user_defs = [
        ("anu_officer", "澳国立专员", RoleCode.ANU_OFFICER.value, "ANU"),
        ("usyd_officer", "悉尼专员", RoleCode.USYD_OFFICER.value, "USYD"),
        ("unsw_officer", "新南威尔士专员", RoleCode.UNSW_OFFICER.value, "UNSW"),
        ("agent_a", "代理专员A", RoleCode.AGENT_A.value, None),
        ("agent_b", "代理专员B", RoleCode.AGENT_B.value, None),
        ("reviewer", "国家审查员", RoleCode.NATIONAL_REVIEWER.value, None),
    ]
    for username, full_name, role_code, uni_code in user_defs:
        exists = session.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if exists:
            continue
        session.add(
            User(
                username=username,
                password_hash=hash_password("123456"),
                full_name=full_name,
                role_id=role_map[role_code],
                university_id=uni_map.get(uni_code) if uni_code else None,
                is_active=True,
                last_login_at=None,
                created_at=now,
                updated_at=now,
            )
        )
