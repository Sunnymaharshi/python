from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional

class IssueStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    closed = "closed"

class IssuePriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class IssueCreate(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    description: Optional[str] = Field(min_length=5, max_length=500)
    priority: IssuePriority = IssuePriority.medium

class IssueUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=100)
    description: Optional[str] = Field(default=None, min_length=5, max_length=500)
    status: Optional[IssueStatus] = None
    priority: Optional[IssuePriority] = None

class IssueResponse(IssueCreate):
    id: str