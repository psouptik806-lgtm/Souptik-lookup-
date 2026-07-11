import httpx
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional

# --- Setup Logging ---
# প্রতিবার সার্চ করলে 'api_requests.log' ফাইলে হিস্ট্রি সেভ হবে
logging.basicConfig(
    filename='api_requests.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

app = FastAPI(
    title="Souptik OSINT API",
    description="Direct Lookup API for ExploitsIndia"
)

# CORS Middleware (যাতে এই API-টি যেকোনো ওয়েবসাইট বা অ্যাপ থেকে সরাসরি কল করা যায়)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EXPLOITS_INDIA_URL = "https://exploitsindia.site"
DEFAULT_BACKEND_KEY = "souptik"

@app.get("/lookup")
async def lookup_number(
    number: str = Query(..., description="The mobile number to search")
):
    # মূল API-এর জন্য প্যারামিটার তৈরি করা
    payload = {
        "key": DEFAULT_BACKEND_KEY,
        "type": "number",
        "num": number
    }

    # লগের তথ্য রেডি করা
    log_data = {"timestamp": datetime.now(timezone.utc).isoformat(), "searched_number": number}

    async with httpx.AsyncClient() as client:
        try:
            # মূল API থেকে ডেটা আনা হচ্ছে
            response = await client.get(EXPLOITS_INDIA_URL, params=payload, timeout=12.0)

            if response.status_code != 200:
                log_data.update({"status": "failed", "http_code": response.status_code})
                logging.error(f"Log: {log_data}")
                raise HTTPException(status_code=502, detail="Backend API error")

            try:
                # ডেটা সফলভাবে পাওয়া গেলে সেটি সরাসরি রিটার্ন করা হবে
                api_data = response.json()
                log_data.update({"status": "success"})
                logging.info(f"Log: {log_data}")
                return api_data

            except ValueError:
                # যদি JSON না হয়ে অন্য কোনো টেক্সট আসে
                log_data.update({"status": "raw_text"})
                logging.warning(f"Log: {log_data}")
                return {"status": "success", "raw_data": response.text}

        except httpx.TimeoutException:
            log_data.update({"status": "timeout"})
            logging.error(f"Log: {log_data}")
            raise HTTPException(status_code=504, detail="Backend API timeout")
        except httpx.RequestError as exc:
            log_data.update({"status": "error", "detail": str(exc)})
            logging.error(f"Log: {log_data}")
            raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)