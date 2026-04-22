import unittest

from controllers.session_controller import AppSession
from services.permission_service import PermissionService
from utils.enums import RoleCode


class PermissionTestCase(unittest.TestCase):
    def test_permission_helpers(self) -> None:
        self.assertTrue(PermissionService.is_agent(RoleCode.AGENT_A.value))
        self.assertTrue(PermissionService.is_reviewer(RoleCode.NATIONAL_REVIEWER.value))
        self.assertTrue(PermissionService.is_school_officer(RoleCode.ANU_OFFICER.value))
        self.assertFalse(PermissionService.is_agent(RoleCode.ANU_OFFICER.value))

    def test_single_session_guard(self) -> None:
        session = AppSession()
        session.login({"name": "u1"})
        with self.assertRaises(RuntimeError):
            session.login({"name": "u2"})
        session.logout()
        self.assertFalse(session.is_authenticated)


if __name__ == "__main__":
    unittest.main()

