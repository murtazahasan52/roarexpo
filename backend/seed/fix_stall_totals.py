"""
One-time fix — correct the payment amount for multi-stall admin bookings.

Admin multi-stall bookings used to store the *total* booking amount in the
`stallRate` field while `numberOfStalls` held the stall count. The payment
email and the invoice both multiply `stallRate × numberOfStalls`, so a firm
that booked 3 stalls at ₹72,000 (total ₹2,16,000) was shown ₹6,48,000.

This migration splits that value correctly:
    totalAmount = old stallRate   (the true, exact total the admin entered)
    stallRate   = round(total / stall count)   (per-stall rate)

It only touches admin bookings (they carry a `stallNumbers` array) that don't
yet have `totalAmount`, so it is safe to re-run and never affects public
per-stall registrations. Firms whose displayed amount actually changed
(more than one stall) get a corrected payment email resent automatically.

Guarded by a marker in `migrations`, so it self-applies once per database.
"""
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.common import utcnow

MIGRATION_ID = "fix-stall-totals-v1"


async def fix_stall_totals(db: AsyncIOMotorDatabase) -> dict | None:
    """Idempotent. Returns a summary the first time it runs, else None."""
    if await db.migrations.find_one({"_id": MIGRATION_ID}):
        return None

    from utils.mailer import send_mail
    from utils.email_templates import (
        exhibitor_payment_reminder_email_html,
        payment_cheque_attachments,
    )

    fixed, resent, resend_failed = [], [], []
    cursor = db.exhibitors.find({
        "stallNumbers": {"$type": "array"},
        "totalAmount": {"$in": [None, ""]},
    })
    async for ex in cursor:
        old_rate = ex.get("stallRate")
        if old_rate in (None, ""):
            continue
        nums = ex.get("stallNumbers") or []
        count = len(nums) or (ex.get("numberOfStalls") or 1)
        try:
            total = int(round(float(old_rate)))
        except (TypeError, ValueError):
            continue
        per_stall = int(round(total / count)) if count else total

        await db.exhibitors.update_one(
            {"_id": ex["_id"]},
            {"$set": {"totalAmount": total, "stallRate": per_stall,
                      "numberOfStalls": count, "updatedAt": utcnow()}},
        )
        fixed.append({"company": ex.get("companyName"), "stalls": nums,
                      "oldTotalShown": total * count, "total": total, "perStall": per_stall})

        # Only firms with >1 stall saw the wrong (doubled) figure — resend to them.
        if count > 1 and ex.get("email"):
            ex.update({"totalAmount": total, "stallRate": per_stall, "numberOfStalls": count})
            try:
                await send_mail(
                    to=ex["email"],
                    subject=f"Corrected payment amount for your ROAR Expo stall booking",
                    html=exhibitor_payment_reminder_email_html(ex),
                    attachments=payment_cheque_attachments(),
                )
                resent.append(ex.get("email"))
            except Exception as err:  # noqa: BLE001 — never block start-up on mail
                resend_failed.append({"email": ex.get("email"), "error": str(err)})

    record = {
        "_id": MIGRATION_ID,
        "appliedAt": utcnow(),
        "fixed": fixed,
        "resent": resent,
        "resendFailed": resend_failed,
    }
    await db.migrations.insert_one(record)
    print(f"[migrate] Stall-total fix {MIGRATION_ID}: {len(fixed)} bookings corrected, "
          f"{len(resent)} corrected emails resent, {len(resend_failed)} email failures.")
    return record
