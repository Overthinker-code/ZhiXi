from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from ultralytics import YOLO
from PIL import Image
import io

app = FastAPI()

model = YOLO("url")  # 待填入模型路径

@app.post("/detect/")
async def detect(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        results = model.predict(image)
        boxes = results[0].boxes  

        output = []
        for box in boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].tolist()
            output.append({
                "class_id": cls_id,
                "confidence": conf,
                "bbox": xyxy  # [x1, y1, x2, y2]
            })

        return JSONResponse(content={"results": output})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# 安装依赖后，运行uvicorn yolo_api:app --host 0.0.0.0 --port [端口号]启动服务。