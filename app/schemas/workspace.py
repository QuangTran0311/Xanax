from pydantic import BaseModel


class WorkspaceUserOut(BaseModel):
    id: str
    username: str
    role: str


class WorkspaceOut(BaseModel):
    status: str = "ready"
    redirect_to: str = "/workspace"
    message: str = "Workspace backend is ready"
    user: WorkspaceUserOut
