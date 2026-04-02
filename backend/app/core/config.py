import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = "https://nthaxzqydovrcpeanimj.supabase.co"
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")  # You need to set this in .env
DATABASE_URL = "postgresql+asyncpg://postgres:4eDga1gpML8LYGhd@db.nthaxzqydovrcpeanimj.supabase.co:5432/postgres?ssl=require"
