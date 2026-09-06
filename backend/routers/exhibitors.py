"""
Port of routes/exhibitors.js + controllers/exhibitorController.js. Accepts
multipart/form-data (Form fields + an optional logo + up to 5 product image
files) exactly like the old `uploadExhibitorFiles` Multer middleware did,
validates the same required fields express-validator used to check, then
replicates the atomic stall-hold flow: verify the picked stall is still
`available`, create the exhibitor, then atomically flip the stall to `held`
— rolling the exhibitor registration back out if someone else grabbed the
same stall in the tiny race window between the check and the claim.
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from config.db import get_db
from config.event_config import EVENT
from middleware.rate_limit import rate_limit
from middleware.upload import EXHIBITOR_FILE_MAX_BYTES, save_upload
from models.exhibitor import new_exhibitor_document
from utils.email_templates import exhibitor_email_html
from utils.generate_code import generate_registration_code
from utils.validators import is_valid_email, is_valid_url
from utils.whatsapp import send_whatsapp
from utils.mailer import send_mail

router = APIRouter(prefix="/api/exhibitors", tags=["exhibitors"])

_register_limiter = rate_limit(
    "register-exhibitor",
    max_requests=10,
    window_seconds=15 * 60,
    message="Too many registration attempts. Please try again later.",
)


@router.post("/register", dependencies=[Depends(_register_limiter)])
async def register_exhibitor(
    itsNumber: str = Form(...),
    contactPerson: str = Form(...),
    designation: str = Form(""),
    email: str = Form(...),
    phone: str = Form(...),
    landline: str = Form(""),
    whatsapp: str = Form(""),
    companyName: str = Form(...),
    businessAddress: str = Form(...),
    businessEmail: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    pincode: str = Form(""),
    website: str = Form(""),
    gstNumber: str = Form(""),
    linkedin: str = Form(""),
    instagram: str = Form(""),
    facebook: str = Form(""),
    category: str = Form(...),
    productsServices: str = Form(""),
    message: str = Form(""),
    stallPackage: str = Form(...),
    numberOfStalls: int = Form(1),
    stallNumber: str = Form(""),
    fasciaName: str = Form(...),
    agreedToTerms: str = Form(...),
    logo: UploadFile | None = File(None),
    productImages: list[UploadFile] = File(default=[]),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    errors = []
    if not itsNumber.strip() or len(itsNumber.strip()) < 4:
        errors.append({"msg": "Enter a valid ITS number", "param": "itsNumber"})
    if not contactPerson.strip():
        errors.append({"msg": "Name is required", "param": "contactPerson"})
    if not is_valid_email(email.strip()):
        errors.append({"msg": "A valid personal email is required", "param": "email"})
    if len(phone.strip()) < 7:
        errors.append({"msg": "A valid mobile number is required", "param": "phone"})
    if not companyName.strip():
        errors.append({"msg": "Business/company name is required", "param": "companyName"})
    if not businessAddress.strip():
        errors.append({"msg": "Business address is required", "param": "businessAddress"})
    if businessEmail.strip() and not is_valid_email(businessEmail.strip()):
        errors.append({"msg": "Enter a valid business email", "param": "businessEmail"})
    if website.strip() and not is_valid_url(website.strip()):
        errors.append({"msg": "Enter a valid website address", "param": "website"})
    if not category.strip():
        errors.append({"msg": "Category is required", "param": "category"})
    if not stallPackage.strip():
        errors.append({"msg": "Stall package is required", "param": "stallPackage"})
    if not fasciaName.strip():
        errors.append({"msg": "Fascia name for your stall is required", "param": "fasciaName"})
    if agreedToTerms not in ("true", "True"):
        errors.append({"msg": "You must agree to the terms", "param": "agreedToTerms"})
    if len(productImages) > 5:
        errors.append({"msg": "Only up to 5 product images are allowed", "param": "productImages"})

    if errors:
        return JSONResponse(status_code=400, content={"success": False, "message": "Validation failed", "errors": errors})

    try:
        # If the exhibitor picked a specific stall, verify it's still
        # available and hold it for them before we create the registration.
        stall = None
        if stallNumber:
            stall = await db.stalls.find_one({"stallNumber": stallNumber.strip().upper()})
            if not stall:
                raise HTTPException(status_code=404, detail="That stall could not be found. Please pick another.")
            if stall["status"] != "available":
                raise HTTPException(
                    status_code=409, detail="That stall was just taken. Please pick another available stall."
                )

        logo_url = ""
        if logo is not None:
            logo_url = await save_upload(logo, "logos", EXHIBITOR_FILE_MAX_BYTES)

        product_image_urls = []
        for img in productImages:
            product_image_urls.append(await save_upload(img, "product-images", EXHIBITOR_FILE_MAX_BYTES))

        registration_code = generate_registration_code("STL")

        doc = new_exhibitor_document({
            "registrationCode": registration_code,
            "itsNumber": itsNumber,
            "contactPerson": contactPerson,
            "designation": designation,
            "email": email,
            "phone": phone,
            "landline": landline,
            "whatsapp": whatsapp,
            "companyName": companyName,
            "businessAddress": businessAddress,
            "businessEmail": businessEmail,
            "city": city,
            "state": state,
            "pincode": pincode,
            "website": website,
            "gstNumber": gstNumber,
            "linkedin": linkedin,
            "instagram": instagram,
            "facebook": facebook,
            "logoUrl": logo_url,
            "productImages": product_image_urls,
            "category": category,
            "productsServices": productsServices,
            "message": message,
            "stallPackage": stallPackage,
            "numberOfStalls": numberOfStalls or 1,
            "stallNumber": stall["stallNumber"] if stall else "",
            "stallId": stall["_id"] if stall else None,
            "stallRate": stall["rate"] if stall else None,
            "fasciaName": fasciaName,
        })

        result = await db.exhibitors.insert_one(doc)
        doc["_id"] = result.inserted_id

        # Atomically claim the stall now that we have the exhibitor's id. If
        # someone else grabbed it in the tiny race window, roll the
        # exhibitor back and ask them to pick again rather than leaving a
        # dangling registration with no stall.
        if stall:
            claimed = await db.stalls.find_one_and_update(
                {"_id": stall["_id"], "status": "available"},
                {"$set": {"status": "held", "heldBy": doc["_id"]}},
                return_document=True,
            )
            if not claimed:
                await db.exhibitors.delete_one({"_id": doc["_id"]})
                raise HTTPException(
                    status_code=409, detail="That stall was just taken. Please pick another available stall."
                )

        # Send confirmation email (does not block the success response if it fails)
        try:
            await send_mail(
                to=doc["email"],
                bcc=None,
                subject=f"Stall Registration Received — {EVENT['eventName']}",
                html=exhibitor_email_html(doc),
            )
            await db.exhibitors.update_one({"_id": doc["_id"]}, {"$set": {"emailSent": True}})
        except Exception as mail_err:  # noqa: BLE001
            print("[exhibitor] Failed to send confirmation email:", mail_err)
            await db.exhibitors.update_one({"_id": doc["_id"]}, {"$set": {"emailError": str(mail_err)}})

        # WhatsApp delivery — non-blocking and safe to skip entirely until a
        # provider is configured (see utils/whatsapp.py).
        try:
            result_wa = await send_whatsapp(
                to=doc.get("whatsapp") or doc["phone"],
                caption=(
                    f"Thanks for registering for {EVENT['eventName']}! Your registration ID is "
                    f"{registration_code}. Your stall is reserved pending organizer approval — we'll "
                    "message you again once it's confirmed."
                ),
            )
            await db.exhibitors.update_one(
                {"_id": doc["_id"]},
                {"$set": {"whatsappSent": bool(result_wa.get("sent")), "whatsappError": "" if result_wa.get("sent") else (result_wa.get("reason") or "")}},
            )
        except Exception as wa_err:  # noqa: BLE001
            print("[exhibitor] Failed to send WhatsApp message:", wa_err)
            await db.exhibitors.update_one({"_id": doc["_id"]}, {"$set": {"whatsappError": str(wa_err)}})

        return {
            "success": True,
            "message": "Registration received. A confirmation email has been sent — your stall is reserved pending organizer approval.",
            "data": {"registrationCode": registration_code},
        }
    except HTTPException:
        raise
    except Exception as err:  # noqa: BLE001
        print("[exhibitor] registration error:", err)
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")
