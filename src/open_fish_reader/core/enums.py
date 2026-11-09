from enum import Enum, IntEnum
class MigrationDirection(IntEnum):
    DOWNSTREAM = -1
    UNKNOWN = 0
    UPSTREAM = 1
class ReviewStatus(str, Enum):
    UNVIEWED = "unviewed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"
    ERROR = "error"
