# main.py
from fastapi import FastAPI
from metagpt.actions.write_code import WriteCode
from metagpt.roles.engineer import Engineer
from metagpt.roles.product_manager import ProductManager
from metagpt.roles.flutter_developer import FlutterDeveloper
app = FastAPI()

@app.post("/generate_flutter_code")
async def generate_code(requirements: str):
    # تهيئة مهندس البرمجيات
    engineer = Engineer()
    product_manager = ProductManager()
    developer = FlutterDeveloper()
    
    # تنفيذ المهمة
    result = await engineer.run(requirements)
    result = await product_manager.run(requirements)
    result = await developer.run(requirements)
    
    return {
        "status": "success",
        "generated_code": result
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)