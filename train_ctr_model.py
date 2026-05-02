import pandas as pd
import numpy as np
import pickle
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder

# Load dataset
df = pd.read_csv("data/train_F3fUq2S.csv")

print(f"Dataset shape: {df.shape}")

# ── Feature Engineering ───────────────────────────────────────────────────────
# Encode times_of_day
le = LabelEncoder()
df["times_of_day_enc"] = le.fit_transform(df["times_of_day"])

# Features to use
FEATURE_COLS = [
    "subject_len", "body_len", "mean_paragraph_len",
    "day_of_week", "is_weekend", "times_of_day_enc",
    "no_of_CTA", "mean_CTA_len", "is_image",
    "is_personalised", "is_quote", "is_timer",
    "is_emoticons", "is_discount", "is_price", "is_urgency"
]

X = df[FEATURE_COLS]
y = df["click_rate"]

# ── Train / Test Split ────────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ── Train Model ───────────────────────────────────────────────────────────────
model = GradientBoostingRegressor(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=4,
    random_state=42
)
model.fit(X_train, y_train)

# ── Evaluate ──────────────────────────────────────────────────────────────────
y_pred = model.predict(X_test)
mse    = mean_squared_error(y_test, y_pred)
r2     = r2_score(y_test, y_pred)

print(f"✅ CTR Model trained!")
print(f"   R2 Score:  {r2:.4f}")
print(f"   MSE:       {mse:.6f}")

# ── Save Model ────────────────────────────────────────────────────────────────
with open("models/ctr_model.pkl", "wb") as f:
    pickle.dump({
        "model":    model,
        "features": FEATURE_COLS,
        "label_encoder": le
    }, f)

print("✅ CTR model saved to models/ctr_model.pkl")