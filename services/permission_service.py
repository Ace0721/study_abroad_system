from utils.enums import AGENT_ROLE_CODES, RoleCode, SCHOOL_OFFICER_CODES


class PermissionService:
    """Fixed role_code based permission checks for coursework scope."""

    @staticmethod
    def is_agent(role_code: str) -> bool:
        return role_code in AGENT_ROLE_CODES

    @staticmethod
    def is_reviewer(role_code: str) -> bool:
        return role_code == RoleCode.NATIONAL_REVIEWER.value

    @staticmethod
    def is_school_officer(role_code: str) -> bool:
        return role_code in SCHOOL_OFFICER_CODES

