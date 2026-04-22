from enum import Enum


class RoleCode(str, Enum):
    ANU_OFFICER = "ANU_OFFICER"
    USYD_OFFICER = "USYD_OFFICER"
    UNSW_OFFICER = "UNSW_OFFICER"
    AGENT_A = "AGENT_A"
    AGENT_B = "AGENT_B"
    NATIONAL_REVIEWER = "NATIONAL_REVIEWER"


class ApplicationStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    REVIEW_REJECTED = "REVIEW_REJECTED"
    SCHOOL_PENDING = "SCHOOL_PENDING"
    SCHOOL_FEEDBACK = "SCHOOL_FEEDBACK"
    SCHOOL_RESERVED = "SCHOOL_RESERVED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"


ACTIVE_APPLICATION_STATUSES = (
    ApplicationStatus.SUBMITTED.value,
    ApplicationStatus.SCHOOL_PENDING.value,
    ApplicationStatus.SCHOOL_FEEDBACK.value,
)


SCHOOL_OFFICER_CODES = {
    RoleCode.ANU_OFFICER.value,
    RoleCode.USYD_OFFICER.value,
    RoleCode.UNSW_OFFICER.value,
}


AGENT_ROLE_CODES = {
    RoleCode.AGENT_A.value,
    RoleCode.AGENT_B.value,
}
