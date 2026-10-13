import catboost as cb
import pandas as pd
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

# 1. قراءة داتاسيت الفانكومايسين الجديدة
df = pd.read_csv('vancomycin_dosing_dataset.csv')

# 2. إزالة المعرفات غير الضرورية إن وجدت
if 'patientunitstayid' in df.columns:
  df = df.drop(columns=['patientunitstayid'])

# 3. تحديد الأعمدة النصية (Categorical) وتعبئة القيم الفارغة
categorical_features = [
    'level_type',
    'dose_raw',
    'dose_route',
    'dose_frequency',
    'dose_drugname',
    'gender',
    'unittype',
    'dose_parse_status',
]

for col in categorical_features:
  if col in df.columns:
    df[col] = df[col].fillna('Unknown').astype(str)

# تعبئة القيم الرقمية الناقصة (مثل creatinine أو admissionweight) بمتوسط الأعمدة لتجنب الأخطاء
numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())

# 4. تحديد المتغيرات المستقلة (X) والهدف (y)
# هنا الهدف هو التنبؤ بمستوى الدواء في الدم (vancomycin_level)
X = df.drop(columns=['vancomycin_level'])
y = df['vancomycin_level']

# تحديث قائمة الـ categorical features لتتوافق مع الأعمدة الموجودة في X فعلياً
categorical_features = [col for col in categorical_features if col in X.columns]

# 5. تقسيم البيانات (Train / Test)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 6. تدريب الموديل باستخدام CatBoost
model = cb.CatBoostRegressor(
    iterations=300,
    learning_rate=0.03,
    depth=5,
    cat_features=categorical_features,
    verbose=50,
)

print('--- جاري تدريب الموديل على بيانات eICU الفانكومايسين ---')
model.fit(X_train, y_train)

# 7. تقييم الموديل
y_pred = model.predict(X_test)
print('\n--- نتائج تقييم الموديل ---')
print(f'MSE: {mean_squared_error(y_test, y_pred):.2f}')
print(f'R2 Score: {r2_score(y_test, y_pred):.2f}')

# 8. حفظ الموديل المحدث
model.save_model('digital_twin_vanco_model.cbm')
print(
    '\nتم حفظ موديل الفانكومايسين بنجاح باسم: digital_twin_vanco_model.cbm'
)