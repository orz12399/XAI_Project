from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd
import io
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse('static/index.html')

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents))
    elif file.filename.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(io.BytesIO(contents))
    else:
        return {"error": "Invalid file format"}
    
    # Convert to list of dicts for JSON response if needed, but for agents we pass df
    return {"columns": df.columns.tolist(), "rows": len(df), "preview": df.head().to_dict()}

@app.post("/generate_suggestions")
async def generate_suggestions(file: UploadFile = File(...)):
    import traceback
    try:
        print(f"DEBUG: Receiving file {file.filename}")
        contents = await file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            return {"error": "Invalid file format"}

        from agents import agent_lime_advice, agent_standard_advice, agent_cot_advice, agent_self_check_advice
        import asyncio

        # Run agents in parallel
        results = await asyncio.gather(
            agent_lime_advice(df),
            agent_standard_advice(df),
            agent_cot_advice(df),
            agent_self_check_advice(df)
        )

        return {
            "lime": results[0],
            "standard": results[1],
            "cot": results[2],
            "self_check": results[3]
        }
    except Exception as e:
        print("ERROR in generate_suggestions:")
        traceback.print_exc()
        return {
            "lime": {"error": f"Backend Error: {str(e)}"},
            "standard": {"error": f"Backend Error: {str(e)}"},
            "cot": {"error": f"Backend Error: {str(e)}"},
            "self_check": {"error": f"Backend Error: {str(e)}"}
        }

