from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import pandas as pd
import pickle
import lightgbm as lgb
from datetime import datetime
from dotenv import load_dotenv

from gemini_service import generate_email
from gmail_service import send_email
from scheduler import schedule_email
from safety_filter import safe_generate_email

load_dotenv()

app = FastAPI(title="MailMagic API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Load LightGBM model ───────────────────────────────────────────────────────
with open("models/lgbm_model.pkl", "rb") as f:
    saved        = pickle.load(f)
    lgbm_model   = saved["model"]
    FEATURE_COLS = saved["features"]

print(f"✅ LightGBM model loaded | Features: {FEATURE_COLS}")

# ── Load CTR model ────────────────────────────────────────────────────────────
with open("models/ctr_model.pkl", "rb") as f:
    ctr_saved     = pickle.load(f)
    ctr_model     = ctr_saved["model"]
    CTR_FEATURES  = ctr_saved["features"]
    ctr_label_enc = ctr_saved["label_encoder"]

print(f"✅ CTR model loaded | Features: {CTR_FEATURES}")


# ── Request / Response Models ─────────────────────────────────────────────────
class RunCampaignRequest(BaseModel):
    customer_ids: List[int]
    scheduled: bool = True

class SendEmailRequest(BaseModel):
    email: str
    name: str
    subject: str
    body: str
    cta: str
    preview_text: str
    quality_score: float
    predicted_send_hour: int
    scheduled: bool = False

class AddCustomerRequest(BaseModel):
    Name: str
    Email: str
    Membership_Tier: str
    Interest_Tag: str
    City: str
    Age: int
    Past_Purchases: int = 0
    Preferred_Device: str = "Mobile"
    Preferred_Hour: int = 10


# ── Helpers ───────────────────────────────────────────────────────────────────
def load_customers() -> pd.DataFrame:
    return pd.read_excel("data/customers.xlsx")

def load_audit_log() -> pd.DataFrame:
    try:
        return pd.read_excel("data/audit_log.xlsx")
    except FileNotFoundError:
        return pd.DataFrame(columns=[
            "Log_ID", "Customer_ID", "Sent_At", "Predicted_Open_Hour",
            "Subject", "Quality_Score", "Status", "Message_ID", "Predicted_CTR"
        ])

def append_audit_log(row: dict):
    df = load_audit_log()
    row["Log_ID"] = len(df) + 1
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_excel("data/audit_log.xlsx", index=False)

def predict_send_hour(customer: dict) -> int:
    now = datetime.now()
    row = {
        "day_of_week":     now.weekday(),
        "month":           now.month,
        "open_minute":     0,
        "Age":             customer.get("Age", 30),
        "Past_Purchases":  customer.get("Past_Purchases", 0),
        "Membership_Tier": customer.get("Membership_Tier", "Silver"),
        "Interest_Tag":    customer.get("Interest_Tag", "General"),
        "Device":          "Mobile",
    }
    df = pd.DataFrame([row])
    for col in ["Membership_Tier", "Interest_Tag", "Device"]:
        df[col] = df[col].astype("category")
    pred = lgbm_model.predict(df[FEATURE_COLS])[0]
    return max(6, min(22, int(round(pred))))

def predict_ctr(email_content: dict, predicted_hour: int) -> float:
    times_map = {
        6: "Morning", 7: "Morning", 8: "Morning",
        9: "Morning", 10: "Morning", 11: "Morning",
        12: "Noon", 13: "Noon", 14: "Noon", 15: "Noon", 16: "Noon",
        17: "Evening", 18: "Evening", 19: "Evening",
        20: "Evening", 21: "Evening", 22: "Evening"
    }
    times_of_day = times_map.get(predicted_hour, "Noon")
    times_enc    = ctr_label_enc.transform([times_of_day])[0]
    subject = email_content.get("subject", "")
    body    = email_content.get("body", "")
    cta     = email_content.get("cta", "")
    row = {
        "subject_len":        len(subject),
        "body_len":           len(body),
        "mean_paragraph_len": len(body) // 3 if body else 0,
        "day_of_week":        datetime.now().weekday(),
        "is_weekend":         1 if datetime.now().weekday() >= 5 else 0,
        "times_of_day_enc":   times_enc,
        "no_of_CTA":          1,
        "mean_CTA_len":       len(cta),
        "is_image":           0,
        "is_personalised":    1,
        "is_quote":           0,
        "is_timer":           0,
        "is_emoticons":       0,
        "is_discount":        1 if "deal" in body.lower() else 0,
        "is_price":           0,
        "is_urgency":         1 if "limited" in body.lower() else 0,
    }
    df  = pd.DataFrame([row])
    ctr = ctr_model.predict(df[CTR_FEATURES])[0]
    return round(float(max(0, min(1, ctr))), 4)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "MailMagic API running", "version": "1.0.0"}

@app.get("/customers")
def get_customers():
    return load_customers().to_dict(orient="records")


@app.post("/customers")
def add_customer(req: AddCustomerRequest = Body(...)):
    customers_df = load_customers()
    new_id = int(customers_df["Customer_ID"].max()) + 1

    new_customer = {
        "Customer_ID": new_id, "Name": req.Name, "Email": req.Email,
        "Membership_Tier": req.Membership_Tier, "Interest_Tag": req.Interest_Tag,
        "City": req.City, "Age": req.Age, "Past_Purchases": req.Past_Purchases
    }
    customers_df = pd.concat(
        [customers_df, pd.DataFrame([new_customer])], ignore_index=True
    )
    customers_df.to_excel("data/customers.xlsx", index=False)

    try:
        interactions_df = pd.read_excel("data/interactions.xlsx")
    except FileNotFoundError:
        interactions_df = pd.DataFrame(columns=[
            "Customer_ID", "Email_ID", "Open_Time",
            "Clicked", "Device", "Day_of_Week"
        ])

    now       = datetime.now()
    open_time = now.replace(hour=req.Preferred_Hour, minute=0, second=0)
    new_interaction = {
        "Customer_ID": new_id, "Email_ID": "camp_001",
        "Open_Time":   open_time.strftime("%Y-%m-%d %H:%M:%S"),
        "Clicked":     False, "Device": req.Preferred_Device,
        "Day_of_Week": now.weekday()
    }
    interactions_df = pd.concat(
        [interactions_df, pd.DataFrame([new_interaction])], ignore_index=True
    )
    interactions_df.to_excel("data/interactions.xlsx", index=False)

    return {
        "success":     True,
        "message":     f"Customer {req.Name} added successfully!",
        "customer_id": new_id,
        "interaction": f"Default interaction created at {req.Preferred_Hour}:00 on {req.Preferred_Device}"
    }


@app.post("/run-campaign")
def run_campaign(req: RunCampaignRequest):
    """
    For each selected customer:
      1. LightGBM  → predicts best send hour
      2. Ollama    → generates personalized email
      3. Safety    → checks content, regenerates if unsafe
      4. CTR check → regenerates if CTR < 2%
      5. Schedule or send immediately
    """
    customers_df = load_customers()
    results, errors = [], []

    for cid in req.customer_ids:
        match = customers_df[customers_df["Customer_ID"] == cid]
        if match.empty:
            errors.append({"customer_id": cid, "error": "Not found"})
            continue

        customer = match.iloc[0].to_dict()

        try:
            # Step 1: Predict best send hour
            predicted_hour = predict_send_hour(customer)

            # Step 2: Generate initial email
            initial_email = generate_email(customer)

            # Step 3 & 4: Safety + CTR pipeline
            pipeline_result = safe_generate_email(
                customer=customer,
                initial_email=initial_email,
                predict_ctr_fn=lambda email, hour: predict_ctr(email, predicted_hour)
            )

            if not pipeline_result["is_safe"]:
                errors.append({
                    "customer_id": cid,
                    "error": f"Email failed safety after {pipeline_result['attempts_safety']} attempts: {pipeline_result['final_issues']}"
                })
                continue

            email_content = pipeline_result["email"]
            predicted_ctr = pipeline_result["ctr"]
            ctr_level     = pipeline_result["ctr_level"]

            email_payload = {
                "customer_id":         cid,
                "name":                customer["Name"],
                "email":               customer["Email"],
                "tier":                customer["Membership_Tier"],
                "interest":            customer["Interest_Tag"],
                "predicted_send_hour": predicted_hour,
                "subject":             email_content["subject"],
                "body":                email_content["body"],
                "cta":                 email_content["cta"],
                "preview_text":        email_content.get("preview_text", ""),
                "quality_score":       email_content["quality_score"],
                "predicted_ctr":       predicted_ctr,
                "predicted_ctr_pct":   f"{round(predicted_ctr * 100, 2)}%",
                "ctr_level":           ctr_level,
                "was_regenerated":     pipeline_result["was_regenerated"],
                "attempts_safety":     pipeline_result["attempts_safety"],
                "attempts_ctr":        pipeline_result["attempts_ctr"]
            }

            # Step 5: Just return preview — frontend calls /send-email after approval
            email_payload["status"] = "Pending"
            results.append(email_payload)

        except Exception as e:
            errors.append({"customer_id": cid, "error": str(e)})

    return {
        "total_generated": len(results),
        "total_errors":    len(errors),
        "mode":            "scheduled" if req.scheduled else "immediate",
        "campaigns":       results,
        "errors":          errors
    }


@app.post("/send-email/{customer_id}")
def send_approved_email(customer_id: int, payload: SendEmailRequest):
    if payload.scheduled:
        job_info = schedule_email(
            customer_id=customer_id,
            predicted_hour=payload.predicted_send_hour,
            email_payload=payload.dict(),
            send_fn=lambda p: send_email(
                to=p["email"], subject=p["subject"], body=p["body"],
                cta=p["cta"], preview_text=p["preview_text"], name=p["name"]
            )
        )
        append_audit_log({
            "Customer_ID":         customer_id,
            "Sent_At":             job_info["scheduled_for"],
            "Predicted_Open_Hour": payload.predicted_send_hour,
            "Subject":             payload.subject,
            "Quality_Score":       payload.quality_score,
            "Status":              "Scheduled",
            "Message_ID":          job_info["job_id"],
            "Predicted_CTR":       0
        })
        return {"success": True, "mode": "scheduled", **job_info}
    else:
        result = send_email(
            to=payload.email, subject=payload.subject,
            body=payload.body, cta=payload.cta,
            preview_text=payload.preview_text, name=payload.name
        )
        append_audit_log({
            "Customer_ID":         customer_id,
            "Sent_At":             datetime.now().isoformat(),
            "Predicted_Open_Hour": payload.predicted_send_hour,
            "Subject":             payload.subject,
            "Quality_Score":       payload.quality_score,
            "Status":              "Sent" if result["success"] else "Failed",
            "Message_ID":          result.get("message_id", ""),
            "Predicted_CTR":       0
        })
        return {"success": result["success"], "mode": "immediate", **result}


@app.get("/analytics")
def get_analytics():
    audit     = load_audit_log()
    customers = load_customers()

    if audit.empty:
        return {
            "total_sent": 0, "avg_quality_score": 0,
            "open_rate": 0, "engagement_lift": 0, "avg_ctr": 0,
            "heatmap": [], "sentiment_trend": [], "interest_breakdown": []
        }

    sent_df         = audit[audit["Status"].isin(["Sent", "Scheduled"])]
    total_sent      = len(sent_df)
    avg_quality     = round(float(sent_df["Quality_Score"].mean()), 1)
    open_rate       = round((sent_df["Quality_Score"] / 100 * 0.6).mean() * 100, 1)
    engagement_lift = round(open_rate - 29.5, 1)
    avg_ctr         = round(float(sent_df["Predicted_CTR"].mean()) * 100, 2) if "Predicted_CTR" in sent_df.columns else 0.0

    heatmap = (
        sent_df.groupby("Predicted_Open_Hour").size()
               .reset_index(name="sends")
               .rename(columns={"Predicted_Open_Hour": "hour"})
               .to_dict(orient="records")
    )

    sent_df["Sent_At"] = pd.to_datetime(sent_df["Sent_At"], errors="coerce")
    sent_df["week"]    = sent_df["Sent_At"].dt.isocalendar().week.astype(str)
    sentiment = (
        sent_df.groupby("week")["Quality_Score"].mean().round(1)
               .reset_index().rename(columns={"Quality_Score": "score"})
               .to_dict(orient="records")
    )

    merged = sent_df.merge(
        customers[["Customer_ID", "Interest_Tag"]], on="Customer_ID", how="left"
    )
    interest = (
        merged.groupby("Interest_Tag").size()
              .reset_index(name="value")
              .rename(columns={"Interest_Tag": "name"})
              .to_dict(orient="records")
    )

    return {
        "total_sent":         total_sent,
        "avg_quality_score":  avg_quality,
        "open_rate":          open_rate,
        "engagement_lift":    engagement_lift,
        "avg_ctr":            avg_ctr,
        "heatmap":            heatmap,
        "sentiment_trend":    sentiment,
        "interest_breakdown": interest,
    }


@app.get("/health")
def health_check():
    return {
        "status":    "ok",
        "model":     "LightGBM + CTR + Safety loaded",
        "timestamp": datetime.now().isoformat()
    }