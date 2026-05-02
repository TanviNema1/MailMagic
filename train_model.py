import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import pickle
import os

def train_and_save():
    print("Loading interaction data...")
    df = pd.read_excel("data/interactions.xlsx")

    # ── Feature Engineering ─────────────────────────────────────────────────
    # WHY: LightGBM needs structured numeric/categorical input.
    # We extract hour from Open_Time — that IS the label we want to predict.

    df["Open_Time"] = pd.to_datetime(df["Open_Time"])
    df["open_hour"]    = df["Open_Time"].dt.hour        # TARGET: what hour did they open?
    df["open_minute"]  = df["Open_Time"].dt.minute      # extra signal
    df["day_of_week"]  = df["Open_Time"].dt.dayofweek   # 0=Monday, 6=Sunday
    df["month"]        = df["Open_Time"].dt.month        # seasonal signal

    # Join customer profile to get tier, interest, age, purchases
    customers = pd.read_excel("data/customers.xlsx")
    df = df.merge(customers[["Customer_ID","Membership_Tier","Interest_Tag","Age","Past_Purchases"]],
                  on="Customer_ID", how="left")

    # Encode categoricals as LightGBM category dtype
    # WHY: LightGBM handles categoricals natively — no manual label encoding needed
    df["Membership_Tier"] = df["Membership_Tier"].astype("category")
    df["Interest_Tag"]    = df["Interest_Tag"].astype("category")
    df["Device"]          = df["Device"].astype("category")

    # ── Define Features & Target ─────────────────────────────────────────────
    FEATURES = [
        "day_of_week", "month", "open_minute",
        "Age", "Past_Purchases",
        "Membership_Tier", "Interest_Tag", "Device"
    ]
    TARGET = "open_hour"

    X = df[FEATURES]
    y = df[TARGET]

    # ── Train / Test Split ───────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # ── LightGBM Dataset ─────────────────────────────────────────────────────
    # WHY lgb.Dataset: LightGBM's native format is faster and uses less RAM
    # than a raw DataFrame during training.
    train_data = lgb.Dataset(
        X_train, label=y_train,
        categorical_feature=["Membership_Tier","Interest_Tag","Device"]
    )
    val_data = lgb.Dataset(
        X_test, label=y_test,
        categorical_feature=["Membership_Tier","Interest_Tag","Device"],
        reference=train_data
    )

    # ── Hyperparameters ──────────────────────────────────────────────────────
    params = {
        "objective":        "regression",      # predict a continuous hour (0–23)
        "metric":           "mae",             # mean absolute error in hours
        "boosting_type":    "gbdt",            # gradient boosting decision tree
        "num_leaves":       31,                # controls model complexity
        "learning_rate":    0.05,              # small = slower but more accurate
        "feature_fraction": 0.9,              # use 90% of features per tree
        "bagging_fraction": 0.8,              # row sampling — reduces overfitting
        "bagging_freq":     5,
        "verbose":          -1                 # suppress noisy output
    }

    # ── Train ────────────────────────────────────────────────────────────────
    print("Training LightGBM model...")
    callbacks = [lgb.early_stopping(50), lgb.log_evaluation(25)]

    model = lgb.train(
        params,
        train_data,
        num_boost_round=500,
        valid_sets=[val_data],
        callbacks=callbacks
    )

    # ── Evaluate ─────────────────────────────────────────────────────────────
    preds = model.predict(X_test)
    mae   = mean_absolute_error(y_test, preds)
    print(f"\n✅ Training complete — MAE: {mae:.2f} hours")
    print(f"   e.g. model is off by {mae:.1f} hours on average")

    # ── Save Feature List ────────────────────────────────────────────────────
    # WHY: We must pass features in the EXACT same order at prediction time
    os.makedirs("models", exist_ok=True)
    with open("models/lgbm_model.pkl", "wb") as f:
        pickle.dump({"model": model, "features": FEATURES}, f)

    print("✅ Model saved to models/lgbm_model.pkl")

if __name__ == "__main__":
    train_and_save()