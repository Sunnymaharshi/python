import uuid
from fastapi import APIRouter, HTTPException, status
from app.schemas import IssueCreate, IssueStatus, IssueUpdate, IssueResponse
from app.storage import load_issues, save_issues



router = APIRouter(prefix="/api/v1/issues", tags=["issues"])

@router.get("/", response_model=list[IssueResponse])
def get_issues():
    issues = load_issues()
    return issues

@router.post("/", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
def create_issue(issue: IssueCreate):
    issues = load_issues()
    new_issue = {
        "id": str(uuid.uuid4()),
        "title": issue.title,
        "description": issue.description,
        "priority": issue.priority,
        "status": IssueStatus.open
    }
    issues.append(new_issue)
    save_issues(issues)
    return new_issue

@router.get("/{issue_id}", response_model=IssueResponse)
def get_issue(issue_id: str):
    issues = load_issues()
    for issue in issues:
        if issue["id"] == issue_id:
            return issue
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

@router.put("/{issue_id}", response_model=IssueResponse)
def update_issue(issue_id: str, issue_update: IssueUpdate):
    issues = load_issues()
    for issue in issues:
        if issue["id"] == issue_id:
            issue.update(issue_update.dict(exclude_unset=True))
            save_issues(issues)
            return issue
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

@router.delete("/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_issue(issue_id: str):
    issues = load_issues()
    for i, issue in enumerate(issues):
        if issue["id"] == issue_id:
            del issues[i]
            save_issues(issues)
            return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")