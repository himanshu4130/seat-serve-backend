"""
Role/Permission model, ported 1:1 from the frontend's src/types/staff.ts so both
sides agree on "what can this role do." The frontend uses this only to gate
navigation; here it is the actual authorization boundary.
"""

from enum import StrEnum


class Role(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    KITCHEN = "KITCHEN"
    STAFF = "STAFF"
    WAITER = "WAITER"
    DELIVERY = "DELIVERY"


class Permission(StrEnum):
    ORDERS_VIEW = "orders.view"
    ORDERS_MANAGE = "orders.manage"
    MENU_VIEW = "menu.view"
    MENU_MANAGE = "menu.manage"
    PAYMENTS_VIEW = "payments.view"
    PAYMENTS_REFUND = "payments.refund"
    STAFF_MANAGE = "staff.manage"
    BUSINESS_MANAGE = "business.manage"
    REPORTS_VIEW = "reports.view"
    BILLING_MANAGE = "billing.manage"
    QR_MANAGE = "qr.manage"
    PLATFORM_VIEW = "platform.view"
    PLATFORM_MANAGE = "platform.manage"
    TENANTS_VIEW = "tenants.view"
    TENANTS_MANAGE = "tenants.manage"
    PLATFORM_REPORTS_VIEW = "platform_reports.view"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.SUPER_ADMIN: {
        Permission.PLATFORM_VIEW,
        Permission.PLATFORM_MANAGE,
        Permission.TENANTS_VIEW,
        Permission.TENANTS_MANAGE,
        Permission.PLATFORM_REPORTS_VIEW,
        Permission.BILLING_MANAGE,
    },
    Role.OWNER: {
        Permission.ORDERS_VIEW,
        Permission.ORDERS_MANAGE,
        Permission.MENU_VIEW,
        Permission.MENU_MANAGE,
        Permission.PAYMENTS_VIEW,
        Permission.PAYMENTS_REFUND,
        Permission.STAFF_MANAGE,
        Permission.BUSINESS_MANAGE,
        Permission.REPORTS_VIEW,
        Permission.BILLING_MANAGE,
        Permission.QR_MANAGE,
    },
    Role.MANAGER: {
        Permission.ORDERS_VIEW,
        Permission.ORDERS_MANAGE,
        Permission.MENU_VIEW,
        Permission.MENU_MANAGE,
        Permission.PAYMENTS_VIEW,
        Permission.STAFF_MANAGE,
        Permission.REPORTS_VIEW,
        Permission.QR_MANAGE,
    },
    Role.KITCHEN: {Permission.ORDERS_VIEW, Permission.ORDERS_MANAGE},
    Role.WAITER: {Permission.ORDERS_VIEW, Permission.MENU_VIEW},
    Role.STAFF: {Permission.ORDERS_VIEW, Permission.ORDERS_MANAGE, Permission.MENU_VIEW},
    Role.DELIVERY: {Permission.ORDERS_VIEW, Permission.ORDERS_MANAGE},
}


def role_has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
