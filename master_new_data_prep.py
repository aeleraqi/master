# -*- coding: utf-8 -*-
"""Master_New_Data_Prep.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1QcqKS5-3xkG2Wr9QlayKt0qwAQzqFZ3p
"""

# تثبيت المكتبات إذا لم تكن مثبتة (لبيئة كولاب)
!pip install nltk seaborn imblearn tqdm openpyxl

# ✅ تأكد من تثبيت pandarallel لو مش متثبت
!pip install -q pandarallel

# Commented out IPython magic to ensure Python compatibility.
# استيراد المكتبات الأساسية
import os
import re
import numpy as np
import pandas as pd

# ربط جوجل درايف مع كولاب
from google.colab import drive
drive.mount('/content/drive')

# معالجة النصوص
import nltk
nltk.download('punkt')
from nltk.tokenize import word_tokenize

# مكتبات الرسم البياني والتحليل المرئي
import matplotlib.pyplot as plt
import seaborn as sns
# %matplotlib inline
import plotly.express as px
import plotly.graph_objects as go


# تحديد القيم المتطرفة
from scipy import stats

# التوازن في البيانات
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
from sklearn.utils import resample

# شريط التقدم (اختياري)
from tqdm.notebook import tqdm

from pandarallel import pandarallel
pandarallel.initialize(progress_bar=True)

"""**دمج البيانات**"""

# تحديد مسار الملفات
data_path = '/content/drive/MyDrive/Master_New/Raw_Data'

# أسماء الملفات
file_names = ['SANAD.xlsx', 'AFND.xlsx', 'UltimateArabic.xlsx', 'MYDATA.xlsx']

# قراءة ودمج الملفات
dfs = []  # لتخزين DataFrames

for file in file_names:
    file_path = os.path.join(data_path, file)
    if os.path.exists(file_path):
        print(f"Reading file: {file}")
        df_temp = pd.read_excel(file_path, engine='openpyxl')
        df_temp['file_name'] = file  # إضافة عمود باسم الملف
        dfs.append(df_temp)
    else:
        print(f"File not found: {file}")

# دمج البيانات في DataFrame واحدة
df_combined = pd.concat(dfs, ignore_index=True)

# فحص البيانات المدمجة
print("\n✅ Combined Dataset Overview:")
print(f"Total rows: {len(df_combined):,}")
print("Columns:", df_combined.columns.tolist())

# عرض أول خمس صفوف من البيانات
df_combined.head()

"""**حذف الصفوف المكرر والفارغة في عمود النص**"""

# قبل الحذف
print(f"عدد الصفوف قبل التنظيف: {len(df_combined):,}")

# حذف الصفوف الفارغة (التي لا تحتوي على نص في عمود الخبر)
df_cleaned = df_combined.dropna(subset=['text'])

# حذف الصفوف التي قد تحتوي على نصوص فارغة بعد إزالة المسافات
df_cleaned = df_cleaned[df_cleaned['text'].str.strip().astype(bool)]

print(f"عدد الصفوف بعد حذف الصفوف الفارغة: {len(df_cleaned):,}")

# حذف الصفوف المكررة بناءً على عمود الخبر (text)
df_cleaned = df_cleaned.drop_duplicates(subset=['text'], keep='first')

print(f"عدد الصفوف بعد حذف التكرارات: {len(df_cleaned):,}")

# إعادة تعيين فهرس البيانات
df_cleaned.reset_index(drop=True, inplace=True)

# معاينة البيانات بعد التنظيف
df_cleaned.head()

"""**تسمية الخلايا الفارغة في عمود المصدر والتصنيف**"""

# ✅ تنظيف عمود المؤسسة (source): تعويض الفارغ بـ 'not labeled'
df_cleaned['source'] = df_cleaned['source'].fillna('not labeled')
df_cleaned['source'] = df_cleaned['source'].astype(str).str.strip()
df_cleaned['source'] = df_cleaned['source'].replace('', 'not labeled')

# ✅ إحصائيات عامة
total_rows = len(df_cleaned)
total_sources = df_cleaned['source'].nunique()
label_column = next((col for col in df_cleaned.columns if 'label' in col.lower() or 'category' in col.lower()), None)
total_categories = df_cleaned[label_column].nunique(dropna=True)

# ✅ توزيع المصادر وعدد الأخبار ونسبتها
source_counts = df_cleaned['source'].value_counts()
source_percentages = (source_counts / source_counts.sum()) * 100

# ✅ إنشاء جدول التحليل
source_df = pd.DataFrame({
    'Source': source_counts.index,
    'Count': source_counts.values,
    'Percentage': source_percentages.round(2)
})

# ✅ عرض الإحصائيات في شكل نصي
print("📊 إحصائيات عامة:")
print(f"- عدد الصفوف: {total_rows:,}")
print(f"- عدد المؤسسات الصحفية: {total_sources}")
print(f"- عدد التصنيفات بعد التوحيد: {total_categories}")

print("\n📌 الوزن النسبي لكل مصدر:")
print(source_df)

# ✅ رسم بياني تفاعلي بلون أزرق موحد
fig = px.bar(
    source_df,
    x='Source',
    y='Percentage',
    text='Percentage',
    title='🔵 Percentage of Articles by Source',
    labels={'Percentage': 'Percentage (%)', 'Source': 'Source'},
    color_discrete_sequence=['#1f77b4']
)

fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
fig.update_layout(
    xaxis_tickangle=-45,
    yaxis=dict(title='Percentage (%)'),
    xaxis=dict(title='Source'),
    plot_bgcolor='white'
)

fig.show()

"""**توحيد طريقة كتابة أسماء التصنيفات ودمج التصنيفاات المتشابهة**"""

import plotly.express as px

# ✅ 1. تنظيف التصنيفات: استبدال NaN أو الفراغات بـ 'not labeled'
df_cleaned[label_column] = df_cleaned[label_column].fillna('not labeled')
df_cleaned[label_column] = df_cleaned[label_column].astype(str).str.strip()
df_cleaned[label_column] = df_cleaned[label_column].replace('', 'not labeled')

# ✅ 2. تحويل النصوص إلى lowercase
df_cleaned[label_column] = df_cleaned[label_column].str.lower()

# ✅ 3. قاموس التوحيد النهائي
category_mapping = {
    'finance': 'economy',
    'economy': 'economy',

    'politics': 'politics',
    'politic': 'politics',
    'defense': 'politics',

    'sports': 'sports',
    'sport': 'sports',

    'health': 'health',
    'medical': 'health',
    'science': 'health',
    'environment': 'health',
    'envairoment': 'health',

    'tech': 'technology',
    'technology': 'technology',

    'art': 'culture',
    'culture': 'culture',
    'variety': 'culture',
    'diverse': 'culture',
    'society': 'culture',

    'religion': 'religion'
}

# ✅ 4. تطبيق التوحيد
df_cleaned[label_column] = df_cleaned[label_column].replace(category_mapping)

# ✅ 5. حساب التوزيع النهائي
unified_category_counts = df_cleaned[label_column].value_counts().reset_index()
unified_category_counts.columns = ['Category', 'Count']

# ✅ 6. عرض المعلومات النصية
print("📊 ✅ ملخص البيانات:")
print(f"- إجمالي عدد الصفوف: {len(df_cleaned):,}")
print(f"- عدد التصنيفات الفريدة بعد التوحيد: {df_cleaned[label_column].nunique(dropna=True)}")
print("\n✅ التوزيع الجديد للتصنيفات:")
print(unified_category_counts)

# ✅ 7. رسم بياني تفاعلي بلون أزرق موحد
fig = px.bar(
    unified_category_counts,
    x='Category',
    y='Count',
    text='Count',
    title='🔵 Distribution of News Articles by Category',
    labels={'Count': 'Number of Articles', 'Category': 'Category'},
    color_discrete_sequence=['#1f77b4']
)

fig.update_traces(texttemplate='%{text:,}', textposition='outside')
fig.update_layout(
    xaxis_tickangle=-45,
    yaxis=dict(title='Number of Articles'),
    xaxis=dict(title='Category'),
    plot_bgcolor='white',
    uniformtext_minsize=8,
    uniformtext_mode='hide'
)

fig.show()

"""**تحليل التوزيع الطبيعي بحسب عدد الكلمات في الخبر **"""

# ✅ التأكد من أن عمود wordcounts رقمي ونظيف
df_cleaned['wordcounts'] = pd.to_numeric(df_cleaned['wordcounts'], errors='coerce')
df_cleaned = df_cleaned.dropna(subset=['wordcounts'])

# ✅ Box Plot 1: لجميع الأخبار
fig1 = px.box(
    df_cleaned,
    y='wordcounts',
    title='📦 توزيع عدد الكلمات في جميع الأخبار',
    labels={'wordcounts': 'عدد الكلمات'},
    color_discrete_sequence=['#1f77b4']
)
fig1.update_layout(plot_bgcolor='white')
fig1.show()

# ✅ Box Plot 2: حسب التصنيفات
fig2 = px.box(
    df_cleaned,
    x=label_column,
    y='wordcounts',
    title='📦 توزيع عدد الكلمات حسب التصنيفات',
    labels={'wordcounts': 'عدد الكلمات', label_column: 'التصنيف'},
    color_discrete_sequence=['#1f77b4']
)
fig2.update_layout(
    xaxis_tickangle=-45,
    plot_bgcolor='white'
)
fig2.show()

"""**حذف الأخبار القصيرة والكويلة جدًا**"""

# حذف الأخبار الأقل من 50 والأطول من 1000 كلمة
df_filtered = df_cleaned[(df_cleaned['wordcounts'] >= 50) & (df_cleaned['wordcounts'] <= 1000)]

# طباعة الإحصائيات بعد الفلترة
print("📦 عدد الأخبار بعد فلترة الطول:")
print(f"- قبل الفلترة: {len(df_cleaned):,}")
print(f"- بعد الفلترة: {len(df_filtered):,}")

# ✅ التأكد من أن عمود wordcounts رقمي ونظيف
df_cleaned['wordcounts'] = pd.to_numeric(df_cleaned['wordcounts'], errors='coerce')
df_cleaned = df_cleaned.dropna(subset=['wordcounts'])

# ✅ فلترة الأخبار بطول من 50 إلى 1000 كلمة
df_filtered = df_cleaned[(df_cleaned['wordcounts'] >= 50) & (df_cleaned['wordcounts'] <= 1000)]

# ✅ Box Plot 1: لجميع الأخبار بعد الفلترة
fig1 = px.box(
    df_filtered,
    y='wordcounts',
    title='📦 توزيع عدد الكلمات في جميع الأخبار (50 إلى 1000 كلمة)',
    labels={'wordcounts': 'عدد الكلمات'},
    color_discrete_sequence=['#1f77b4']
)
fig1.update_layout(plot_bgcolor='white')
fig1.show()

# ✅ Box Plot 2: حسب التصنيفات بعد الفلترة
fig2 = px.box(
    df_filtered,
    x=label_column,
    y='wordcounts',
    title='📦 توزيع عدد الكلمات حسب التصنيفات (50 إلى 1000 كلمة)',
    labels={'wordcounts': 'عدد الكلمات', label_column: 'التصنيف'},
    color_discrete_sequence=['#1f77b4']
)
fig2.update_layout(
    xaxis_tickangle=-45,
    plot_bgcolor='white'
)
fig2.show()

print("📊 تحليل عدد الكلمات:")
print(f"- المتوسط: {df_filtered['wordcounts'].mean():.2f}")
print(f"- الوسيط (median): {df_filtered['wordcounts'].median():.2f}")
print(f"- 90% من الأخبار أقل من: {df_filtered['wordcounts'].quantile(0.9):.0f} كلمة")

"""**مقارنة بين عدد الأخبار بحسب المصدر والتصنيف قبل الحذف وبعده**"""

# تحديد الأعمدة
label_column = next((col for col in df_cleaned.columns if 'label' in col.lower() or 'category' in col.lower()), None)
source_column = 'source'

# ✅ مقارنة المصادر
source_before = df_cleaned[source_column].value_counts().reset_index()
source_before.columns = ['Source', 'Count']
source_before['Dataset'] = 'قبل الفلترة'

source_after = df_filtered[source_column].value_counts().reset_index()
source_after.columns = ['Source', 'Count']
source_after['Dataset'] = 'بعد الفلترة'

source_combined = pd.concat([source_before, source_after])

fig1 = px.bar(
    source_combined,
    x='Source',
    y='Count',
    color='Dataset',
    barmode='group',
    title='📊 مقارنة توزيع الأخبار حسب المصادر (قبل وبعد الفلترة)',
    labels={'Count': 'عدد الأخبار', 'Source': 'المصدر'},
    color_discrete_sequence=['#1f77b4', '#ff7f0e']
)
fig1.update_layout(xaxis_tickangle=-45, plot_bgcolor='white')
fig1.show()

# ✅ مقارنة التصنيفات
cat_before = df_cleaned[label_column].value_counts().reset_index()
cat_before.columns = ['Category', 'Count']
cat_before['Dataset'] = 'قبل الفلترة'

cat_after = df_filtered[label_column].value_counts().reset_index()
cat_after.columns = ['Category', 'Count']
cat_after['Dataset'] = 'بعد الفلترة'

cat_combined = pd.concat([cat_before, cat_after])

fig2 = px.bar(
    cat_combined,
    x='Category',
    y='Count',
    color='Dataset',
    barmode='group',
    title='📊 مقارنة توزيع الأخبار حسب التصنيفات (قبل وبعد الفلترة)',
    labels={'Count': 'عدد الأخبار', 'Category': 'التصنيف'},
    color_discrete_sequence=['#1f77b4', '#ff7f0e']
)
fig2.update_layout(xaxis_tickangle=-45, plot_bgcolor='white')
fig2.show()

"""**احصائيات عن البيانات الآن**"""

# ✅ التأكد من الأعمدة
label_column = next((col for col in df_filtered.columns if 'label' in col.lower() or 'category' in col.lower()), None)
source_column = 'source' if 'source' in df_filtered.columns else None

# ✅ إحصائيات أساسية
total_rows = len(df_filtered)
total_categories = df_filtered[label_column].nunique(dropna=True)
total_sources = df_filtered[source_column].nunique(dropna=True)

print("📊 إحصائيات عامة على البيانات بعد الفلترة:")
print(f"- عدد الصفوف: {total_rows:,}")
print(f"- عدد التصنيفات الفريدة: {total_categories}")
print(f"- عدد المصادر الفريدة: {total_sources}")

# ✅ توزيع المصادر
print("\n📌 توزيع عدد الأخبار حسب المصادر:")
source_counts = df_filtered[source_column].value_counts()
print(source_counts)

# ✅ توزيع التصنيفات
print("\n📌 توزيع عدد الأخبار حسب التصنيفات:")
category_counts = df_filtered[label_column].value_counts()
print(category_counts)

"""**تنظيف عمود النص**"""

import re
from pandarallel import pandarallel

# تهيئة pandarallel مع تفعيل شريط التقدم
pandarallel.initialize(progress_bar=True)

def tag_special_tokens(text):
    # تحويل الأرقام العربية لإنجليزية
    text = text.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))

    # استبدال التواريخ الرقمية بأنماط مختلفة
    text = re.sub(
        r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',
        ' <DATE> ', text
    )
    text = re.sub(r'\b(20[0-5][0-9]|19[7-9][0-9])\b', ' <DATE> ', text)

    # استبدال أسماء الشهور العربية
    text = re.sub(r'\b(يناير|فبراير|مارس|إبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)/?\b', ' <DATE> ', text)

    # استبدال الأرقام (بما فيها الحالات مثل "5 آلاف")
    text = re.sub(r'(?<!\w)\d+\s*(?:ألف|آلاف|الف)?(?!\w)', ' <NUM> ', text)
    text = re.sub(r'(?<!\w)\d+(\.\d+)?(?!\w)', ' <NUM> ', text)

    # استبدال العملات
    currency_patterns = [
        r'جنيه(?:اً|ًا|ات|ان|ين)?',
        r'دولار(?:اً|ًا|ات|ان|ين)?',
        r'ريال(?:اً|ًا|ات|ان|ين)?',
        r'درهم(?:اً|ًا|ات|ان|ين)?',
        r'€|£|¥|USD|EGP|SAR|AED'
    ]
    for pattern in currency_patterns:
        text = re.sub(fr'\b{pattern}\b', ' <CURRENCY> ', text, flags=re.IGNORECASE)

    # استبدال الوقت
    time_pattern = re.compile(
        r'\b([01]?[0-9]|2[0-3])[:٫،]?[0-5][0-9]?\s*(?:ص|صباحاً|م|مساء|am|pm|AM|PM)?\b',
        re.IGNORECASE
    )
    text = time_pattern.sub(' <TIME> ', text)

    # استبدال الترتيب
    ordinals = [
        'الأول', 'الثاني', 'الثالث', 'الرابع', 'الخامس',
        'السادس', 'السابع', 'الثامن', 'التاسع', 'العاشر',
        'الحادي عشر', 'الثاني عشر', 'الرابعه', 'الرابعة'
    ]
    for o in ordinals:
        text = re.sub(fr'\b{o}\b', ' <ORDINAL> ', text, flags=re.IGNORECASE)

    # استبدال الوحدات
    units = ['كيلو', 'كجم', 'جرام', 'طن', 'لتر', 'متر', 'سم', 'مللي', 'كيلومتر', 'مليجرام']
    for u in units:
        text = re.sub(fr'\b{u}\b', ' <UNIT> ', text)

    return text

def protect_special_tokens_arabic(text):
    """
    حماية الرموز الخاصة عن طريق استبدالها بنصوص عربية لا تحتوي على أحرف لاتينية أو علامات ترقيم.
    """
    mapping = {
        '<NUM>': 'رقمخاص',
        '<DATE>': 'تاريخخاص',
        '<CURRENCY>': 'عملةخاص',
        '<TIME>': 'وقتخاص',
        '<ORDINAL>': 'ترتيبخاص',
        '<UNIT>': 'وحدةخاص'
    }
    for eng, arb in mapping.items():
        text = text.replace(eng, arb)
    return text

def shield_protected_tokens(text):
    """
    إضافة مسافات قبل وبعد الرموز المحمية لضمان عزلها عن باقي النص،
    حتى لو كانت محصورة بين علامات ترقيم لا تُزال.
    """
    protected = ['رقمخاص', 'تاريخخاص', 'عملةخاص', 'وقتخاص', 'ترتيبخاص', 'وحدةخاص']
    for token in protected:
        # إذا كان الرمز ملتصقاً بكلمة أو علامة، نضيف مسافة قبلها
        text = re.sub(r'(?<!\s)(' + re.escape(token) + r')', r' \1', text)
        # ونضيف مسافة بعدها إذا كانت متلاصقة مع حرف آخر
        text = re.sub(r'(' + re.escape(token) + r')(?!\s)', r'\1 ', text)
    return text

def restore_special_tokens_arabic(text):
    """
    استرجاع الرموز الخاصة المحمية من النص (المكتوبة بالعربية) إلى شكلها الأصلي.
    """
    mapping = {
        'رقمخاص': '<NUM>',
        'تاريخخاص': '<DATE>',
        'عملةخاص': '<CURRENCY>',
        'وقتخاص': '<TIME>',
        'ترتيبخاص': '<ORDINAL>',
        'وحدةخاص': '<UNIT>'
    }
    for arb, eng in mapping.items():
        text = text.replace(arb, eng)
    return text

def basic_text_cleaning(text):
    """
    تنظيف النص من الإيموجي والهاشتاجات والمينشنات والروابط،
    إزالة التشكيل والرموز المخفية وعلامات الترقيم (عن طريق استبدالها بمسافة)
    بالإضافة إلى تطبيع الحروف وإزالة الأحرف الإنجليزية.
    قبل ذلك نضمن عزل الرموز المحمية باستخدام دالة shield.
    """
    # حماية عزل الرموز المحمية
    text = shield_protected_tokens(text)

    # إزالة الإيموجي
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    # إزالة الهاشتاجات والمينشنات والروابط
    text = re.sub(r'#\S+', '', text)
    text = re.sub(r'@\S+', '', text)
    text = re.sub(r'http[s]?://\S+', '', text)
    # إزالة التشكيل والرموز المخفية
    text = re.sub(r'[\u064B-\u065F\u0670\u08D3-\u08E1]', '', text)
    text = re.sub(r'[\u200B-\u200F\u202A-\u202E\u2066-\u2069]', '', text)

    # إزالة علامات الترقيم (عن طريق استبدالها بمسافة)
    all_punctuations = (
        '.،,:;…؟!"#$%&\'()*+,-—:;<=>؟?@[\\]^_`{|}~'
        '¡¿„“”«»‹›—–‑‐‒‘’‚′″‵‶⸴⸵'
        '。！？،؛：「」『』《》【】〜￥'
        '۔॥'
        'ـ٫٬٭ٮٰٱۖۗۘۙۚۛۜ۝۞ۣ۟۠ۡۢۤۥۦۧۨ۩۪ۭ۫۬ۮۯ'
        '†‡‰‹›※⁂⁃⁄⁅⁆⁇⁈⁉⁎⁒⁓'
        '⟨⟩⟪⟫⟬⟭⟮⟯⦃⦄⦅⦆⦇⦈⦉⦊'
        '⁽⁾₍₎'
        '〈〉《》《》《》《》《》《》《》《》《》《》《》《》《》'
        '〝〞〟﹙﹚﹛﹜﹝﹞｟｠'
    )
    text = re.sub(f'[{re.escape(all_punctuations)}]', ' ', text)

    # تقليل الحروف المكررة
    text = re.sub(r'(.)\1{2,}', r'\1\1', text)

    # تطبيع الحروف
    text = re.sub(r'ى', 'ي', text)
    text = re.sub(r'ؤ', 'و', text)
    text = re.sub(r'ة', 'ه', text)
    text = re.sub(r'[إأٱآا]', 'ا', text)
    text = re.sub(r'گ', 'ك', text)
    text = re.sub(r'ڤ', 'ف', text)
    text = re.sub(r'چ', 'ج', text)
    text = re.sub(r'پ', 'ب', text)

    # إزالة الأحرف الإنجليزية (التي لم نحميها)
    text = re.sub(r'[A-Za-z]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def full_text_cleaning(text):
    """
    دمج خطوات التنظيف:
      1. استخراج الرموز الخاصة (tag).
      2. حماية الرموز الخاصة بنصوص عربية قابلة للحماية.
      3. تنظيف النص الأساسي.
      4. استرجاع الرموز الخاصة إلى شكلها الأصلي.
    """
    text = tag_special_tokens(text)
    text = protect_special_tokens_arabic(text)
    text = basic_text_cleaning(text)
    text = restore_special_tokens_arabic(text)
    return text

# تهيئة pandarallel مع تفعيل شريط التقدم
pandarallel.initialize(progress_bar=True)

# نفترض أن df_filtered هو DataFrame الموجود لديك والعمود "text" يحتوي على النصوص

# إنشاء نسخة من الـ DataFrame الأصلي لتطبيق التنظيف عليها
df_filtered_clean = df_filtered.copy()

# تطبيق دالة full_text_cleaning على عمود "text" باستخدام parallel_apply
df_filtered_clean['cleaned_text'] = df_filtered_clean['text'].parallel_apply(full_text_cleaning)

"""**مقارنة النص قبل التنظيف وبعده**"""

df_filtered.loc[df_filtered.index[160], 'text']

df_filtered_clean.loc[df_filtered_clean.index[160], 'cleaned_text']

"""**التوازن بطريقة Oversampling**"""

from sklearn.utils import resample

# تحديد عمود التصنيف
label_column = next((col for col in df_filtered_clean.columns if 'label' in col.lower() or 'category' in col.lower()), None)

# عرض التوزيع قبل التوازن
print("📊 توزيع التصنيفات قبل التوازن:")
print(df_filtered_clean[label_column].value_counts())

# الحد الأعلى (نستهدف مساواة الجميع بأكثر فئة تمثيلًا)
target_size = df_filtered_clean[label_column].value_counts().max()

# عمل Oversampling لكل تصنيف
balanced_frames = []
for label, group in df_filtered_clean.groupby(label_column):
    if len(group) < target_size:
        upsampled = resample(group, replace=True, n_samples=target_size, random_state=42)
    else:
        upsampled = group.copy()
    balanced_frames.append(upsampled)

# إنشاء النسخة المتوازنة وتجميعها
df_balanced = pd.concat(balanced_frames).sample(frac=1, random_state=42).reset_index(drop=True)

print("\n✅ توزيع التصنيفات بعد التوازن:")
after_dist = df_balanced[label_column].value_counts()
print(after_dist)

print(f"✅ عدد الصفوف بعد التوازن: {len(df_balanced):,}")

"""**حفط كافة البيانات في Google Drive**"""

from google.colab import drive
import os
import time

# تركيب Google Drive
drive.mount('/content/drive')

# تعريف مسار المجلد الجديد داخل Master_New
save_path = '/content/drive/MyDrive/Master_New/DataPrep'
os.makedirs(save_path, exist_ok=True)

# التأكد من إنشاء المجلد
time.sleep(2)  # انتظار قصير لتزامن Drive
if os.path.exists(save_path):
    print(f"Directory {save_path} exists or was created.")
else:
    raise Exception(f"Directory {save_path} could not be created.")

# حفظ الملفات في المجلد الجديد
df_combined.to_csv(f"{save_path}/00_merged_raw.csv", index=False)
df_cleaned.to_csv(f"{save_path}/01_cleaned_no_duplicates.csv", index=False)
df_filtered.to_csv(f"{save_path}/02_filtered_by_length.csv", index=False)
df_filtered_clean.to_csv(f"{save_path}/03_cleaned_text_final.csv", index=False)
df_balanced.to_csv(f"{save_path}/04_balanced_data.csv", index=False)

print("All files saved successfully.")