from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Customer:
    """The legacy customer record, field names as stored (PROJECT_BRIEF section 2).

    New code outside the monolith must never use these names; Phase 1 adds an ACL that maps them.
    """

    cust_id: UUID
    cust_nm: str
    cust_eml: str
