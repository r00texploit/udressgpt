from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
from software_company import generate_repo

app = FastAPI(title="MetaGPT API", description="API for MetaGPT software company simulation")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProjectRequest(BaseModel):
    idea: str
    investment: float = 3.0
    n_round: int = 5
    code_review: bool = True
    run_tests: bool = False
    implement: bool = True
    project_name: str = ""
    inc: bool = False
    project_path: str = ""
    reqa_file: str = ""
    max_auto_summarize_code: int = 0
    recover_path: Optional[str] = None
    ui_framework: str = "react"
    enable_ui_review: bool = True

class ProjectResponse(BaseModel):
    project_path: str
    status: str
    message: str

@app.post("/api/project", response_model=ProjectResponse)
async def create_project(request: ProjectRequest):
    try:
        repo = generate_repo(
            idea=request.idea,
            investment=request.investment,
            n_round=request.n_round,
            code_review=request.code_review,
            run_tests=request.run_tests,
            implement=request.implement,
            project_name=request.project_name,
            inc=request.inc,
            project_path=request.project_path,
            reqa_file=request.reqa_file,
            max_auto_summarize_code=request.max_auto_summarize_code,
            recover_path=request.recover_path,
            ui_framework=request.ui_framework,
            enable_ui_review=request.enable_ui_review
        )
        return ProjectResponse(
            project_path=str(repo.workdir),
            status="success",
            message="Project generated successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True) 