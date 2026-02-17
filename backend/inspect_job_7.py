import asyncio
from app.repositories.db import AsyncSessionLocal
from app.models.models import ScanJob, GuidelineVersion, GuidelineRule
from sqlalchemy import select

async def inspect():
    async with AsyncSessionLocal() as db:
        # Check specific job
        job_id = 7
        result = await db.execute(select(ScanJob).where(ScanJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            print(f"Job {job_id} not found.")
            return
            
        print(f"Job {job_id} - Guideline Version ID: {job.guideline_version_id}")
        
        if job.guideline_version_id:
            gv_res = await db.execute(select(GuidelineVersion).where(GuidelineVersion.id == job.guideline_version_id))
            gv = gv_res.scalar_one_or_none()
            if gv:
                print(f"Guideline Version {gv.id} - Set ID: {gv.guideline_set_id}, Version: {gv.version_number}")
                
                rules_res = await db.execute(select(GuidelineRule).where(GuidelineRule.guideline_version_id == gv.id))
                rules = rules_res.scalars().all()
                print(f"Found {len(rules)} rules for this version.")
                for r in rules[:5]:
                    print(f"  - [{r.rule_id}] {r.rule_text[:50]}...")
            else:
                print("Guideline version not found in DB.")
        else:
            print("Job has NO guideline version ID associated.")

if __name__ == "__main__":
    asyncio.run(inspect())
