"""
Train the Placify placement-percentage model.

This intentionally uses beginner-friendly pandas operations (no Pipeline/ColumnTransformer).

Run from this backend folder:
    python train_model.py
"""

import os
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = os.path.join(
    BASE_DIR,
    "..",
    "dataset",
    "student_placement_prediction_dataset.csv"
)


df = pd.read_csv(DATA_PATH)

df = df.drop_duplicates()

df = df.dropna(
    subset=["placement_percentage"]
)


# Fill missing numeric and text values in a simple way

numeric_columns = df.select_dtypes(
    include=["int64", "float64"]
).columns

for column in numeric_columns:
    df[column] = df[column].fillna(
        df[column].median()
    )


text_columns = df.select_dtypes(
    include=["object"]
).columns

for column in text_columns:
    if df[column].isnull().sum() > 0:
        df[column] = df[column].fillna(
            df[column].mode()[0]
        )


# Do not use ID or information that reveals the placement outcome

X = df.drop(
    columns=[
        "student_id",
        "placement_status",
        "salary_package_lpa",
        "placement_percentage"
    ],
    errors="ignore"
)

y = df["placement_percentage"]


# Convert text columns to 0/1 columns

X = pd.get_dummies(
    X,
    drop_first=True,
    dtype=int
)


# Split data so we can check how the model performs

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)


model = RandomForestRegressor(
    n_estimators=30,
    max_depth=14,
    random_state=42,
    n_jobs=-1
)

model.fit(
    X_train,
    y_train
)


predictions = model.predict(X_test)

mae = mean_absolute_error(
    y_test,
    predictions
)

rmse = mean_squared_error(
    y_test,
    predictions
) ** 0.5

r2 = r2_score(
    y_test,
    predictions
)


# Save the model trained on the training split.
# The test split remains separate for evaluation.

joblib.dump(
    model,
    os.path.join(
        BASE_DIR,
        "placement_percentage_model.joblib"
    )
)

joblib.dump(
    list(X.columns),
    os.path.join(
        BASE_DIR,
        "placement_model_columns.joblib"
    )
)

joblib.dump(
    df.drop(
        columns=["placement_percentage"]
    ).median(
        numeric_only=True
    ).to_dict(),
    os.path.join(
        BASE_DIR,
        "numeric_defaults.joblib"
    )
)


# Save common values for categorical columns
# to fill information not collected by the current form

categorical_defaults = {}

for column in df.drop(
    columns=["placement_percentage"]
).select_dtypes(
    include=["object"]
).columns:

    if column not in [
        "student_id",
        "placement_status",
        "salary_package_lpa"
    ]:
        categorical_defaults[column] = str(
            df[column].mode()[0]
        )


joblib.dump(
    categorical_defaults,
    os.path.join(
        BASE_DIR,
        "categorical_defaults.joblib"
    )
)


print("Model trained and saved.")

print(
    f"MAE:  {mae:.2f}"
)

print(
    f"RMSE: {rmse:.2f}"
)

print(
    f"R2:   {r2:.4f}"
)