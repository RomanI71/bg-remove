from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import io
from PIL import Image
from datetime import datetime

# Try to load rembg
try:
    from rembg import remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False
    print("⚠️ rembg module not found. Install with: pip install rembg pillow fastapi uvicorn")

# ------------------------------
# App setup
# ------------------------------
app = FastAPI(title="AI Background Remover API")

# Enable CORS for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Make output folder
os.makedirs("outputs", exist_ok=True)

# ------------------------------
# Helper: remove background
# ------------------------------
def remove_background(image: Image.Image, bg_color: str = "transparent") -> Image.Image:
    """Remove background using rembg (AI) or fallback."""
    if REMBG_AVAILABLE:
        output = remove(image)
        result = Image.open(io.BytesIO(output)).convert("RGBA")
    else:
        # simple fallback (not perfect)
        image = image.convert("RGBA")
        datas = image.getdata()
        newData = []
        for item in datas:
            # Remove white-ish background manually
            if item[0] > 200 and item[1] > 200 and item[2] > 200:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)
        result = Image.new("RGBA", image.size)
        result.putdata(newData)

    # Optional background color fill
    if bg_color != "transparent":
        bg = Image.new("RGBA", result.size, bg_color)
        bg.paste(result, mask=result.split()[3])
        result = bg

    return result


# ------------------------------
# Routes
# ------------------------------

@app.post("/remove-bg")
async def remove_bg_api(
    image: UploadFile = File(...),
    background_color: str = Form("transparent"),
):
    """POST an image → return processed file info"""
    try:
        img = Image.open(io.BytesIO(await image.read()))

        # Process
        processed = remove_background(img, background_color)

        # Save result
        filename = f"removed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_path = os.path.join("outputs", filename)
        processed.save(output_path)

        return {
            "success": True,
            "filename": filename,
            "download_url": f"/download/{filename}",
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download processed image"""
    file_path = os.path.join("outputs", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return JSONResponse(status_code=404, content={"error": "File not found"})


@app.get("/")
async def root():
    return {"message": "🪄 Welcome to AI Background Remover API", "endpoint": "/remove-bg"}


# ------------------------------
# Run server
# ------------------------------
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting AI Background Remover on port {port} ...")
    uvicorn.run("app:app", host="0.0.0.0", port=port)

