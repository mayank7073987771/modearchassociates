from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends, File, UploadFile, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Dict, List, Literal
import uuid
import bcrypt
import jwt
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

uploads = AsyncIOMotorGridFSBucket(db, bucket_name="uploads")

# Create the main app without a prefix
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bright-lollipop-1c73e8.netlify.app", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class LeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=8, max_length=20)
    city: str = Field(min_length=2, max_length=80)
    property_size: str = Field(min_length=1, max_length=40)
    floor_type: Literal["1 BHK", "2 BHK", "3 BHK", "Commercial / Office"]
    lead_type: Literal["budget", "consultation", "site_visit"] = "budget"

class LeadResponse(LeadCreate):
    model_config = ConfigDict(extra="ignore")
    id: str
    created_at: str

class AdminLogin(BaseModel):
    password: str = Field(min_length=8, max_length=200)

class ContentPayload(BaseModel):
    content: Dict[str, Any]

DEFAULT_CONTENT = {
    "logo": "https://customer-assets-lqy194kg.emergentagent.net/job_modearch-studio/artifacts/3qjpry9k_interior-logo-arch%20%281%29.png",
    "badge1": "IN-HOUSE EXECUTION",
    "badge2": "100% QUALITY CHECKED",
    "badge3": "ON-TIME DELIVERY",
    "badge4": "TRANSPARENT PRICING",
    "nav_cta": "Book a consultation",
    "hero_eyebrow": "ARCHITECTURE · INTERIORS · EXECUTION",
    "hero_title": "Mode Arch Associates – Interior Designer & Architect in",
    "hero_title_accent": "Mumbai",
    "hero_subtitle": "End-to-end residential and commercial interior solutions delivered on time and within budget.",
    "hero_cta1": "Book free consultation",
    "hero_cta2": "Get cost estimate",
    "hero_note": "Trusted by 100+ homeowners in Mumbai & beyond",
    "hero_caption": "Warm minimalism in every detail",
    "metrics_label": "01 — WHY MODEARCH",
    "metrics_title": "Good design is a",
    "metrics_title_accent": "way of living.",
    "founder": "Nilesh Mishra",
    "story": "Modearch Associates began in 2011 with a simple belief: thoughtful architecture and honest execution can make everyday spaces feel extraordinary. Today, we bring that same personal approach to homes and businesses across Mumbai.",
    "metric1_value": "50+", "metric1_text": "Years combined experience",
    "metric2_value": "100+", "metric2_text": "Projects completed",
    "metric3_value": "100%", "metric3_text": "On-time delivery guarantee",
    "services_label": "02 — WHAT WE DO",
    "services_title": "Our Interior Design",
    "services_title_accent": "Services",
    "services_intro": "From first sketch to final styling, our studio brings every detail under one roof.",
    "service1_title": "Full Home Interiors", "service1_desc": "Complete spaces, thoughtfully considered.",
    "service2_title": "Modular Kitchens & Smart Wardrobes", "service2_desc": "Beautifully made. Built to last.",
    "service3_title": "Architectural Design & Planning", "service3_desc": "Form, function, and a future-ready plan.",
    "service4_title": "Commercial & Retail Spaces", "service4_desc": "Spaces that work as hard as you do.",
    "calc_label": "03 — YOUR NEXT SPACE",
    "calc_title": "Estimate your",
    "calc_title_accent": "interior budget.",
    "calc_intro": "Get a quick, transparent estimate tailored to your home. No obligations, just clarity.",
    "calc_quote_label": "Estimated starting range",
    "calc_quote_note": "Based on standard finishes · final quote after consultation",
    "calc_cta": "Get my detailed estimate",
    "calc_caption": "Built around your life.",
    "price_1bhk": "₹12L",
    "price_2bhk": "₹15L",
    "price_3bhk": "₹18L",
    "price_commercial": "₹9L",
    "packages_label": "04 — SIMPLE, HONEST PRICING",
    "packages_title": "Choose your",
    "packages_title_accent": "level of detail.",
    "packages_intro": "Every package is transparent, flexible, and designed to move with your vision. Share your requirements and we'll prepare a clear quote.",
    "packages_featured": "MOST POPULAR",
    "package1_tag": "01 / ESSENTIAL", "package1_name": "Essential", "package1_desc": "Smart essentials for a beautiful, functional home.", "package1_price": "Get a quote", "package1_f1": "Modular kitchen", "package1_f2": "2 wardrobes", "package1_f3": "Basic lighting plan",
    "package2_tag": "02 / BALANCED", "package2_name": "Balanced", "package2_desc": "The sweet spot between detail, quality, and value.", "package2_price": "Get a quote", "package2_f1": "Complete home interiors", "package2_f2": "Custom storage solutions", "package2_f3": "Lighting & soft furnishings",
    "package3_tag": "03 / PREMIUM", "package3_name": "Premium Luxury", "package3_desc": "For homes where every finish tells a story.", "package3_price": "Get a quote", "package3_f1": "Signature custom design", "package3_f2": "Premium materials", "package3_f3": "Full styling & art direction",
    "projects_label": "05 — SELECTED WORK",
    "projects_title": "Residential & Commercial",
    "projects_title_accent": "Projects",
    "projects_cta": "View all projects",
    "faq_label": "06 — COMMON QUESTIONS",
    "faq_title": "Interior design in Mumbai,",
    "faq_title_accent": "answered honestly.",
    "faq1_q": "How much does interior design cost in Mumbai?", "faq1_a": "1 BHK interiors start around ₹12 lakh, 2 BHK around ₹15 lakh, 3 BHK around ₹18 lakh, and commercial offices around ₹9 lakh. Every project gets a transparent, itemised quote before work begins.",
    "faq2_q": "Which areas do you serve in Mumbai?", "faq2_a": "We are based in Dahisar West and serve all of Mumbai — Dahisar, Borivali, Kandivali, Mira Road, Bhayandar, Malad, Goregaon, Jogeshwari, Andheri and beyond.",
    "faq3_q": "How long does a full home interior project take?", "faq3_a": "A typical 1-2 BHK full home interior takes 45-75 days from design approval to handover. We share a clear timeline upfront and deliver on time with 100% quality checks.",
    "faq4_q": "Do you handle both design and execution?", "faq4_a": "Yes. We are a full in-house studio — design, materials, civil work, furniture and styling are all executed by our own team, so there is one point of contact and no coordination hassles.",
    "faq5_q": "Do you design commercial and office spaces?", "faq5_a": "Yes, we design and build offices, retail stores and commercial spaces across Mumbai, with packages starting around ₹9 lakh depending on size and finishes.",
    "project1_name": "01 — The Nair Residence", "project1_tags": "Calm · Layered · Personal",
    "project2_name": "02 — The Mehta Home", "project2_tags": "Contemporary · Warm · Intentional",
    "contact_label": "07 — LET'S TALK",
    "contact_title": "Have a space",
    "contact_title_accent": "in mind?",
    "contact_intro": "Tell us a little about it. We'll bring the coffee, the ideas, and a clear next step.",
    "contact_cta": "Start a conversation",
    "areas_label": "SERVICE AREA",
    "areas_title": "Interior Design Services",
    "areas_title_accent": "Across Mumbai",
    "areas_text": "Based in Dahisar West — designing and building homes & offices across Mumbai, Maharashtra.",
    "area1_name": "Dahisar West", "area1_desc": "Our home turf. Full home interiors, modular kitchens and renovations for 1, 2 & 3 BHK homes across Mandapeshwar, IC Colony, Shanti Nagar & nearby Dahisar West pockets.",
    "area2_name": "Dahisar East", "area2_desc": "Interior design and civil work for homes and shops in Dahisar East — from fresh flat interiors to complete makeovers near the station and Western Express Highway.",
    "area3_name": "Borivali", "area3_desc": "Architecture and interior design for residences, offices and retail spaces across Borivali West & East — thoughtful planning, honest pricing, on-time handover.",
    "area4_name": "Kandivali", "area4_desc": "Modular kitchens, wardrobes and complete home interiors for Kandivali West & East families — smart storage and finishes that fit your budget.",
    "area5_name": "Mira Road", "area5_desc": "End-to-end interiors for new flats and resale homes in Mira Road & Bhayandar — we handle design, material and execution under one roof.",
    "area6_name": "Malad", "area6_desc": "Premium home and commercial interiors across Malad West & East — custom furniture, lighting and styling tailored to your space.",
    "area7_name": "Goregaon", "area7_desc": "Complete residential and office interiors across Goregaon West & East — from compact 1 BHKs to spacious family homes near Film City and beyond.",
    "area8_name": "Jogeshwari", "area8_desc": "Smart, budget-friendly interiors for homes and small businesses in Jogeshwari West & East — practical design that makes every square foot count.",
    "area9_name": "Andheri", "area9_desc": "Full-scale architecture and interior projects across Andheri West & East — premium apartments, offices and showrooms delivered on time.",
    "phone": "+91 99877 54413",
    "whatsapp": "+91 99877 54413",
    "email": "modearchassociates@gmail.com",
    "instagram": "https://instagram.com/_modearch",
    "facebook": "https://share.google/7lsU8W2SLyaHn7x0S",
    "google_business": "https://share.google/FgM0IC50wNdrkXRlw",
    "address": "2A, Bhavna Avenue Building, Laxman Mhatre Rd, Mandapeshwar, Dahisar West, Mumbai, Maharashtra 400068",
    "hours": "Monday to Sunday · 10:00 AM – 9:00 PM",
    "sticky_text": "Ready to make space for better living?",
    "sticky_call": "Call",
    "sticky_whatsapp": "WhatsApp",
    "sticky_visit": "Book site visit",
    "footer_text": "© 2025 Modearch Associates. Crafted for living.",
    "estimate_label": "GET YOUR ESTIMATE",
    "estimate_title": "A clearer number starts here.",
    "estimate_sub": "Share a few details and our studio will be in touch within one business day.",
    "visit_label": "BOOK A SITE VISIT",
    "visit_title": "Let's see your space.",
    "visit_sub": "Share a few details and our studio will be in touch within one business day.",
    "hero_image": "https://images.unsplash.com/photo-1564078516393-cf04bd966897?auto=format&fit=crop&w=1400&q=72",
    "living_image": "https://images.unsplash.com/photo-1724582586495-d050726cf354?auto=format&fit=crop&w=1080&q=70",
    "kitchen_image": "https://images.pexels.com/photos/7148841/pexels-photo-7148841.jpeg?auto=compress&cs=tinysrgb&w=940",
    "office_image": "https://images.unsplash.com/photo-1718220216044-006f43e3a9b1?auto=format&fit=crop&w=1080&q=70",
    "portfolio1_image": "https://images.unsplash.com/photo-1699800900071-ae073285ca02?auto=format&fit=crop&w=1080&q=70",
    "portfolio2_image": "https://images.unsplash.com/photo-1755771984341-546c2a04f236?auto=format&fit=crop&w=1080&q=70",
}

def admin_token(password: str) -> str:
    secret = os.environ["JWT_SECRET"]
    return jwt.encode({"sub": "modearch-admin", "role": "admin", "exp": datetime.now(timezone.utc).timestamp() + 28800}, secret, algorithm="HS256")

async def require_admin(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Admin login required")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        return payload
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Admin session expired") from exc

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Modearch API"}

@api_router.get("/content")
async def get_content():
    saved = await db.site_content.find_one({}, {"_id": 0})
    return {**DEFAULT_CONTENT, **(saved or {})}

AREAS = {
    "near-me": {"name": "Mumbai", "title": "Interior Designer Near Me in Mumbai", "intro": "Searching for an interior designer near me? Mode Arch Associates is based in Dahisar West and serves homes and offices across all of Mumbai — with in-house execution, transparent pricing and a free first consultation. If you are in Dahisar, Borivali, Kandivali, Malad, Goregaon, Jogeshwari, Andheri, Mira Road or Bhayandar, our team is likely just minutes away from you."},
    "dahisar-west": {"name": "Dahisar West", "intro": "Our home turf. From Mandapeshwar and IC Colony to Shanti Nagar, we design and build full home interiors, modular kitchens and complete renovations for 1, 2 and 3 BHK homes across Dahisar West — with our own in-house team and transparent pricing."},
    "dahisar-east": {"name": "Dahisar East", "intro": "From fresh flat interiors to complete makeovers near Dahisar station and the Western Express Highway — we handle design, civil work and finishing for homes and shops across Dahisar East."},
    "borivali": {"name": "Borivali", "intro": "Architecture and interior design for residences, offices and retail spaces across Borivali West & East — thoughtful planning, honest itemised pricing and on-time handover, every single time."},
    "kandivali": {"name": "Kandivali", "intro": "Modular kitchens, smart wardrobes and complete home interiors for Kandivali West & East families — clever storage and durable finishes that respect your budget."},
    "mira-road": {"name": "Mira Road", "intro": "End-to-end interiors for new flats and resale homes across Mira Road — design, materials and execution handled under one roof by our in-house team."},
    "bhayandar": {"name": "Bhayandar", "intro": "Full home and shop interiors across Bhayandar West & East — the same in-house execution, quality checks and transparent pricing we are known for in Dahisar."},
    "malad": {"name": "Malad", "intro": "Premium home and commercial interiors across Malad West & East — custom furniture, lighting design and full styling tailored to your space and lifestyle."},
    "goregaon": {"name": "Goregaon", "intro": "Complete residential and office interiors across Goregaon West & East — from compact 1 BHKs to spacious family homes near Film City and beyond."},
    "jogeshwari": {"name": "Jogeshwari", "intro": "Smart, budget-friendly interiors for homes and small businesses across Jogeshwari West & East — practical design that makes every square foot count."},
    "andheri": {"name": "Andheri", "intro": "Full-scale architecture and interior projects across Andheri West & East — premium apartments, offices and showrooms designed and delivered on time."},
}

@api_router.get("/areas")
async def list_areas():
    return [{"slug": slug, "name": area["name"]} for slug, area in AREAS.items()]

@api_router.get("/areas/{slug}")
async def get_area(slug: str):
    area = AREAS.get(slug)
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    return {"slug": slug, **area}

@api_router.post("/admin/login")
async def admin_login(input: AdminLogin):
    configured = os.environ["ADMIN_PASSWORD"]
    if not bcrypt.checkpw(input.password.encode("utf-8"), bcrypt.hashpw(configured.encode("utf-8"), bcrypt.gensalt())):
        raise HTTPException(status_code=401, detail="Incorrect admin password")
    return {"token": admin_token(input.password), "role": "admin"}

@api_router.put("/admin/content")
async def update_content(payload: ContentPayload, _: dict = Depends(require_admin)):
    clean = {key: value for key, value in payload.content.items() if key != "_id"}
    await db.site_content.replace_one({}, clean, upsert=True)
    return {**DEFAULT_CONTENT, **clean}

@api_router.get("/admin/leads")
async def get_admin_leads(_: dict = Depends(require_admin)):
    return await db.leads.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api_router.post("/leads", response_model=LeadResponse)
async def create_lead(input: LeadCreate):
    doc = input.model_dump()
    doc.update({"id": str(uuid.uuid4()), "created_at": datetime.now(timezone.utc).isoformat()})
    await db.leads.insert_one(doc.copy())
    return doc

@api_router.get("/leads", response_model=List[LeadResponse])
async def get_leads():
    return await db.leads.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api_router.post("/admin/upload")
async def admin_upload(file: UploadFile = File(...), _: dict = Depends(require_admin)):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 8 MB")
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "jpg"
    path = f"modearch/uploads/{uuid.uuid4()}.{ext}"
    gridfs_id = await uploads.upload_from_stream(path, data, metadata={"contentType": file.content_type})
    await db.files.insert_one({"id": str(uuid.uuid4()), "storage_path": path, "gridfs_id": gridfs_id, "original_filename": file.filename, "content_type": file.content_type, "is_deleted": False, "created_at": datetime.now(timezone.utc).isoformat()})
    return {"url": f"/api/uploads/{path}", "path": path}

@api_router.get("/uploads/{path:path}")
async def get_upload(path: str):
    record = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not record or not record.get("gridfs_id"):
        raise HTTPException(status_code=404, detail="File not found")
    stream = await uploads.open_download_stream(record["gridfs_id"])
    data = await stream.read()
    return Response(content=data, media_type=record.get("content_type") or "application/octet-stream", headers={"Cache-Control": "public, max-age=604800"})

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
