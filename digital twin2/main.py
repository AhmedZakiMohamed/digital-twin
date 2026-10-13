import catboost as cb
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# تهيئة تطبيق FastAPI
app = FastAPI(
    title="Digital Twin Vancomycin Dosing API",
    description="API for predicting Vancomycin blood serum levels and dosing",
    version="2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# تحميل موديل الفانكومايسين المدرب مسبقاً
model = cb.CatBoostRegressor()
try:
  model.load_model("digital_twin_vanco_model.cbm")
  print("تم تحميل موديل الفانكومايسين بنجاح!")
except Exception as e:
  print(f"خطأ في تحميل الموديل: {e}")


# تعريف هيكل البيانات الجديد بناءً على مدخلات داتاسيت الفانكومايسين
class VancomycinInputData(BaseModel):
  level_type: str = Field(..., example="Vancomycin - trough")
  dose_offset: float = Field(..., example=-2525.0)
  dose_raw: str = Field(..., example="1,500 mg")
  dose_route: str = Field(..., example="IVPB")
  dose_frequency: str = Field(..., example="QHS")
  dose_drugname: str = Field(
      ..., example="VANCOmycin 1.5 GM in NS 500ML IVPB"
  )
  creatinine: float = Field(..., example=0.88)
  bun: float = Field(..., example=17.0)
  age: float = Field(..., example=67.0)
  gender: str = Field(..., example="Female")
  admissionweight: float = Field(..., example=106.8)
  unittype: str = Field(..., example="Med-Surg ICU")
  dose_amount_mg: float = Field(..., example=1500.0)
  dose_parse_status: str = Field(..., example="ok")


app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")


@app.get("/")
def home():
  return {
      "status": "Online",
      "message": (
          "Digital Twin Vancomycin Clinical Decision API is running"
          " successfully!"
      ),
  }


@app.post("/predict-vancomycin")
def predict_vanco_level(data: VancomycinInputData):
  try:
    # تحويل البيانات القادمة إلى DataFrame
    input_dict = data.dict()
    df_input = pd.DataFrame([input_dict])

    # استخراج أسماء الأعمدة المتوقعة من الموديل
    if hasattr(model, "feature_names_") and model.feature_names_:
      expected_features = model.feature_names_

      # معرفة الأعمدة النصية (Categorical) بدقة من الموديل
      try:
        cat_indices = model.get_cat_feature_indices()
        cat_features_names = [expected_features[i] for i in cat_indices]
      except Exception:
        cat_features_names = [
            "level_type",
            "dose_raw",
            "dose_route",
            "dose_frequency",
            "dose_drugname",
            "gender",
            "unittype",
            "dose_parse_status",
        ]

      # التأكد من وجود كل الأعمدة وترتيبها بالشكل الصحيح
      for col in expected_features:
        if col not in df_input.columns:
          # إذا كان العمود نصياً نضع "Unknown"، وإذا كان رقمياً نضع 0.0 لتجنب الأخطاء
          if col in cat_features_names:
            df_input[col] = "Unknown"
          else:
            df_input[col] = 0.0

      # إعادة ترتيب الأعمدة لتطابق الموديل حرفياً
      df_input = df_input[expected_features]

      # معالجة الأعمدة النصية وتجنب الـ NaN وتحويلها لنصوص
      for col in cat_features_names:
        if col in df_input.columns:
          df_input[col] = df_input[col].fillna("Unknown").astype(str)

    # التنبؤ بمستوى الدواء في الدم باستخدام موديل الفانكومايسين
    prediction = model.predict(df_input)

    return {
        "success": True,
        "predicted_vancomycin_level": round(float(prediction[0]), 2),
    }

  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))