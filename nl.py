import httpx
import logging
import re
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup

logging.basicConfig(
    filename='api_requests.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

app = FastAPI(
    title="Souptik OSINT API",
    description="Filtered Data Lookup API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EXPLOITS_INDIA_URL = "https://exploitsindia.site"
DEFAULT_BACKEND_KEY = "souptik"

def extract_field(pattern, text):
    """HTML টেক্সট থেকে নির্দিষ্ট ফিল্ডের ডেটা খুঁজে বের করার ফাংশন"""
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else "Not Found"

@app.get("/lookup")
async def lookup_number(
    number: str = Query(..., description="The mobile number to search")
):
    payload = {
        "key": DEFAULT_BACKEND_KEY,
        "type": "number",
        "num": number
    }

    log_data = {"timestamp": datetime.now(timezone.utc).isoformat(), "searched_number": number}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(EXPLOITS_INDIA_URL, params=payload, timeout=15.0)
            
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Backend API error")

            raw_text = response.text

            # HTML পেজ থেকে সমস্ত টেক্সট কন্টেন্ট বের করা হচ্ছে
            soup = BeautifulSoup(raw_text, "html.parser")
            cleaned_text = soup.get_text(separator="  ").strip()
            # অতিরিক্ত স্পেস রিমুভ করা হচ্ছে যাতে ফিল্টার করতে সুবিধা হয়
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

            # --- নির্দিষ্ট তথ্যের প্যাটার্ন ম্যাচিং (Regex Parsing) ---
            # ব্যাকএন্ড ডেটার সাধারণ কীওয়ার্ড ম্যাচিং ট্রাই করা হচ্ছে
            name = extract_field(r"(?:name|customer name|full name)[:\s]+([^|;\n,]+)", cleaned_text)
            fname = extract_field(r"(?:father name|f name|care of|c/o)[:\s]+([^|;\n,]+)", cleaned_text)
            address = extract_field(r"(?:address|current address|residence)[:\s]+([^|;\n]+)", cleaned_text)
            alt_address = extract_field(r"(?:alt address|alternate address|permanent address)[:\s]+([^|;\n]+)", cleaned_text)
            aadhar = extract_field(r"(?:aadhar|uidai|aadhaar number)[:\s]+([\d]{4}\s?[\d]{4}\s?[\d]{4})", cleaned_text)

            # যদি কোনো ফিল্ডই খুঁজে না পাওয়া যায়, তার মানে ডেটা ভিন্ন ফরম্যাটে আছে অথবা নম্বরটি ডাটাবেজে নেই
            if name == "Not Found" and address == "Not Found" and aadhar == "Not Found":
                # ব্যাকআপ হিসেবে সম্পূর্ণ টেক্সট রেজাল্টটি ইউজারকে দিয়ে দেওয়া হবে
                return {
                    "status": "success",
                    "number": number,
                    "message": "Could not parse individual fields. Showing raw text summary.",
                    "raw_summary": cleaned_text[:500] # প্রথম ৫০০ ক্যারেক্টার দেখানো হবে
                }

            log_data.update({"status": "parsed_successfully"})
            logging.info(f"Log: {log_data}")

            # আপনার রিকোয়েস্ট অনুযায়ী একদম ক্লিপ আউটপুট ফরম্যাট
            return {
                "status": "success",
                "number": number,
                "name": name,
                "father_name": fname,
                "address": address,
                "alternate_address": alt_address,
                "aadhar_number": aadhar
            }

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Backend API timeout")
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail="Internal server error")
