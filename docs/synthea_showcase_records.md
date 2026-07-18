# Synthea 시연 레코드 4건 (chosen_loop 필드 추가)

## Figure 1 - 12세 (Otitis media, RAG 근거 대조, NR5)

```json
{
  "record_id": "0808cc99-8743-4c82-8877-28062aed5e4f",
  "source": "synthea",
  "patient_id": "33a3de2f-d27a-13fb-c5a7-62d2993d2321",
  "age": 12,
  "gender": "M",
  "chief_complaint": "Otitis media (disorder)",
  "symptoms": [
    "runny nose",
    "sneezing",
    "nasal congestion",
    "fever",
    "ear pain"
  ],
  "diagnoses": [
    {
      "icd10_code": "Z86.41",
      "description": "Medication review due (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2016-05-28"
    },
    {
      "icd10_code": "J30.2",
      "description": "Other seasonal allergic rhinitis",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2016-11-16"
    },
    {
      "icd10_code": "K01.9",
      "description": "Infection of tooth (disorder)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2019-12-14"
    },
    {
      "icd10_code": "F90.3",
      "description": "Child attention deficit disorder (disorder)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2021-03-19"
    },
    {
      "icd10_code": "J00",
      "description": "Acute nasopharyngitis [common cold]",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2023-12-16"
    },
    {
      "icd10_code": "H67.1",
      "description": "Otitis media in diseases classified elsewhere, right ear",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2024-07-26"
    }
  ],
  "medications": [
    {
      "name": "NDA020800 0.3 ML Epinephrine 1 MG/ML Auto-Injector",
      "dose": 0.3,
      "unit": "mL",
      "route": null,
      "frequency": null,
      "is_active": true
    },
    {
      "name": "Fexofenadine hydrochloride 30 MG Oral Tablet",
      "dose": 30.0,
      "unit": "mg",
      "route": null,
      "frequency": null,
      "is_active": true
    },
    {
      "name": "Acetaminophen 160 MG Chewable Tablet",
      "dose": 160.0,
      "unit": "mg",
      "route": null,
      "frequency": null,
      "is_active": false
    }
  ],
  "observations": [
    {
      "name": "Common Ragweed IgE Ab [Units/volume] in Serum",
      "value": "0.0",
      "unit": "kU/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-12-03T01:58:00Z"
    },
    {
      "name": "Latex IgE Ab [Units/volume] in Serum",
      "value": "0.3",
      "unit": "kU/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-12-03T01:58:00Z"
    },
    {
      "name": "Honey bee IgE Ab [Units/volume] in Serum",
      "value": "0.1",
      "unit": "kU/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-12-03T01:58:00Z"
    },
    {
      "name": "Cladosporium herbarum IgE Ab [Units/volume] in Serum",
      "value": "0.1",
      "unit": "kU/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-12-03T01:58:00Z"
    },
    {
      "name": "American house dust mite IgE Ab [Units/volume] in Serum",
      "value": "0.3",
      "unit": "kU/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-12-03T01:58:00Z"
    },
    {
      "name": "Cat dander IgE Ab [Units/volume] in Serum",
      "value": "0.0",
      "unit": "kU/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-12-03T01:58:00Z"
    },
    {
      "name": "White oak IgE Ab [Units/volume] in Serum",
      "value": "0.2",
      "unit": "kU/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-12-03T01:58:00Z"
    },
    {
      "name": "Shrimp IgE Ab [Units/volume] in Serum",
      "value": "0.2",
      "unit": "kU/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-12-03T01:58:00Z"
    },
    {
      "name": "Soybean IgE Ab [Units/volume] in Serum",
      "value": "0.3",
      "unit": "kU/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-12-03T01:58:00Z"
    },
    {
      "name": "Egg white IgE Ab [Units/volume] in Serum",
      "value": "0.1",
      "unit": "kU/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-12-03T01:58:00Z"
    },
    {
      "name": "Wheat IgE Ab [Units/volume] in Serum",
      "value": "0.2",
      "unit": "kU/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-12-03T01:58:00Z"
    },
    {
      "name": "Codfish IgE Ab [Units/volume] in Serum",
      "value": "0.2",
      "unit": "kU/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-12-03T01:58:00Z"
    },
    {
      "name": "Walnut IgE Ab [Units/volume] in Serum",
      "value": "0.0",
      "unit": "kU/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-12-03T01:58:00Z"
    },
    {
      "name": "Peanut IgE Ab [Units/volume] in Serum",
      "value": "0.1",
      "unit": "kU/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-12-03T01:58:00Z"
    },
    {
      "name": "Cow milk IgE Ab [Units/volume] in Serum",
      "value": "0.3",
      "unit": "kU/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-12-03T01:58:00Z"
    },
    {
      "name": "Head Occipital-frontal circumference Percentile",
      "value": "22.8",
      "unit": "%",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2017-11-25T01:32:21Z"
    },
    {
      "name": "Weight-for-length Per age and sex",
      "value": "12.0",
      "unit": "%",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2017-11-25T01:32:21Z"
    },
    {
      "name": "Head Occipital-frontal circumference",
      "value": "48.5",
      "unit": "cm",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2017-11-25T01:32:21Z"
    },
    {
      "name": "Body temperature",
      "value": "37.7",
      "unit": "Cel",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-12-16T00:32:21Z"
    },
    {
      "name": "Platelet [Entitic mean volume] in Blood by Automated count",
      "value": "11.9",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2025-01-04T01:32:21Z"
    },
    {
      "name": "Platelet distribution width [Entitic volume] in Blood by Automated count",
      "value": "201.5",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2025-01-04T01:32:21Z"
    },
    {
      "name": "Platelets [#/volume] in Blood by Automated count",
      "value": "295.8",
      "unit": "10*3/uL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2025-01-04T01:32:21Z"
    },
    {
      "name": "Erythrocyte [DistWidth] in Blood by Automated count",
      "value": "43.2",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2025-01-04T01:32:21Z"
    },
    {
      "name": "MCHC [Entitic Mass/volume] in Red Blood Cells by Automated count",
      "value": "33.0",
      "unit": "g/dL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2025-01-04T01:32:21Z"
    },
    {
      "name": "MCH [Entitic mass] by Automated count",
      "value": "28.9",
      "unit": "pg",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2025-01-04T01:32:21Z"
    },
    {
      "name": "MCV [Entitic mean volume] in Red Blood Cells by Automated count",
      "value": "92.1",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2025-01-04T01:32:21Z"
    },
    {
      "name": "Hemoglobin [Mass/volume] in Blood",
      "value": "14.2",
      "unit": "g/dL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2025-01-04T01:32:21Z"
    },
    {
      "name": "Erythrocytes [#/volume] in Blood by Automated count",
      "value": "4.3",
      "unit": "10*6/uL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2025-01-04T01:32:21Z"
    },
    {
      "name": "Hematocrit [Volume Fraction] of Blood by Automated count",
      "value": "42.7",
      "unit": "%",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2025-01-04T01:32:21Z"
    },
    {
      "name": "Leukocytes [#/volume] in Blood by Automated count",
      "value": "9.0",
      "unit": "10*3/uL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2025-01-04T01:32:21Z"
    },
    {
      "name": "Heart rate",
      "value": "94.0",
      "unit": "/min",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-01-10T01:32:21Z"
    },
    {
      "name": "Systolic Blood Pressure",
      "value": "153.0",
      "unit": "mm[Hg]",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-01-10T01:32:21Z"
    },
    {
      "name": "Diastolic Blood Pressure",
      "value": "93.0",
      "unit": "mm[Hg]",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-01-10T01:32:21Z"
    },
    {
      "name": "Body mass index (BMI) [Percentile] Per age and sex",
      "value": "43.4",
      "unit": "%",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-01-10T01:32:21Z"
    },
    {
      "name": "Respiratory rate",
      "value": "15.0",
      "unit": "/min",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-01-10T01:32:21Z"
    },
    {
      "name": "Body Weight",
      "value": "35.7",
      "unit": "kg",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-01-10T01:32:21Z"
    },
    {
      "name": "Pain severity - 0-10 verbal numeric rating [Score] - Reported",
      "value": "1.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-01-10T01:32:21Z"
    },
    {
      "name": "Body Height",
      "value": "143.1",
      "unit": "cm",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-01-10T01:32:21Z"
    },
    {
      "name": "Body mass index (BMI) [Ratio]",
      "value": "17.4",
      "unit": "kg/m2",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-01-10T01:32:21Z"
    },
    {
      "name": "Patient Health Questionnaire-9: Modified for Teens total score [Reported.PHQ.Teen]",
      "value": "1.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-01-10T02:13:34Z"
    }
  ],
  "clinical_text": null,
  "context": {
    "situation": "outpatient",
    "roles": [
      "physician",
      "patient",
      "guardian"
    ],
    "accessibility_score": 0.92
  },
  "quality": {
    "reflexion_loops": 3,
    "chosen_loop": [
      3,
      0.5
    ],
    "hallucination_flags": [
      "[NR5] Diagnosis 'Medication review due (situation)' is not mentioned in the reference context",
      "[NR5] Diagnosis 'Child attention deficit disorder (disorder)' is not mentioned in the reference context",
      "[NR5] Diagnosis 'Acute nasopharyngitis [common cold]' is not mentioned in the reference context",
      "[NR5] Diagnosis 'Otitis media in diseases classified elsewhere, right ear' is not mentioned in the reference context"
    ],
    "reason_codes": [
      "NR5"
    ],
    "q_index": 0.5,
    "status": "NEEDS_REVIEW"
  },
  "encounter_date": null,
  "flagged": false,
  "created_at": "2026-07-17T07:40:11.110446"
}
```

## Figure 2 - 8세 (Acute bronchitis, 구조적 중복 검증, NR5)

```json
{
  "record_id": "80ec9dce-6c1f-4477-8287-9fe01e5d5650",
  "source": "synthea",
  "patient_id": "d2bf16e1-62a2-a46e-284c-c923e3fa4327",
  "age": 8,
  "gender": "F",
  "chief_complaint": "Acute bronchitis (disorder)",
  "symptoms": [
    "pain",
    "swelling",
    "limited range of motion",
    "redness",
    "fever"
  ],
  "diagnoses": [
    {
      "icd10_code": "Z86.41",
      "description": "Medication review due (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2018-03-14"
    },
    {
      "icd10_code": "Z86.41",
      "description": "Medication review due (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2018-08-22"
    },
    {
      "icd10_code": "Z86.41",
      "description": "Medication review due (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2019-02-20"
    },
    {
      "icd10_code": "Z86.41",
      "description": "Medication review due (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2019-05-22"
    },
    {
      "icd10_code": "Z86.41",
      "description": "Medication review due (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2020-08-19"
    },
    {
      "icd10_code": "Z86.41",
      "description": "Medication review due (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2021-02-17"
    },
    {
      "icd10_code": "S83",
      "description": "Dislocation and sprain of joints and ligaments of knee",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2021-04-22"
    },
    {
      "icd10_code": "M23.41",
      "description": "Loose body in knee, right knee",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2021-04-22"
    },
    {
      "icd10_code": "H67.1",
      "description": "Otitis media in diseases classified elsewhere, right ear",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2021-07-26"
    },
    {
      "icd10_code": "J00",
      "description": "Acute nasopharyngitis [common cold]",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2023-07-22"
    },
    {
      "icd10_code": "Z86.41",
      "description": "Medication review due (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2024-02-28"
    },
    {
      "icd10_code": "J20.9",
      "description": "Acute bronchitis, unspecified",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2024-07-24"
    },
    {
      "icd10_code": "Z86.41",
      "description": "Medication review due (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2025-03-05"
    }
  ],
  "medications": [
    {
      "name": "Acetaminophen 21.7 MG/ML / Dextromethorphan Hydrobromide 1 MG/ML / doxylamine succinate 0.417 MG/ML Oral Solution",
      "dose": 21.7,
      "unit": "mg",
      "route": null,
      "frequency": null,
      "is_active": false
    },
    {
      "name": "Amoxicillin 500 MG Oral Tablet",
      "dose": 500.0,
      "unit": "mg",
      "route": null,
      "frequency": null,
      "is_active": false
    },
    {
      "name": "Ibuprofen 100 MG Oral Tablet",
      "dose": 100.0,
      "unit": "mg",
      "route": null,
      "frequency": null,
      "is_active": false
    }
  ],
  "observations": [
    {
      "name": "Head Occipital-frontal circumference",
      "value": "48.7",
      "unit": "cm",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2022-02-16T23:46:36Z"
    },
    {
      "name": "Head Occipital-frontal circumference Percentile",
      "value": "50.4",
      "unit": "%",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2022-02-16T23:46:36Z"
    },
    {
      "name": "Weight-for-length Per age and sex",
      "value": "55.5",
      "unit": "%",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2022-02-16T23:46:36Z"
    },
    {
      "name": "Platelet [Entitic mean volume] in Blood by Automated count",
      "value": "11.6",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2024-02-28T23:46:36Z"
    },
    {
      "name": "Platelet distribution width [Entitic volume] in Blood by Automated count",
      "value": "200.2",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2024-02-28T23:46:36Z"
    },
    {
      "name": "Platelets [#/volume] in Blood by Automated count",
      "value": "247.4",
      "unit": "10*3/uL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2024-02-28T23:46:36Z"
    },
    {
      "name": "Erythrocyte [DistWidth] in Blood by Automated count",
      "value": "45.6",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2024-02-28T23:46:36Z"
    },
    {
      "name": "MCHC [Entitic Mass/volume] in Red Blood Cells by Automated count",
      "value": "33.4",
      "unit": "g/dL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2024-02-28T23:46:36Z"
    },
    {
      "name": "MCH [Entitic mass] by Automated count",
      "value": "30.8",
      "unit": "pg",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2024-02-28T23:46:36Z"
    },
    {
      "name": "MCV [Entitic mean volume] in Red Blood Cells by Automated count",
      "value": "90.4",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2024-02-28T23:46:36Z"
    },
    {
      "name": "Hematocrit [Volume Fraction] of Blood by Automated count",
      "value": "46.6",
      "unit": "%",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2024-02-28T23:46:36Z"
    },
    {
      "name": "Hemoglobin [Mass/volume] in Blood",
      "value": "16.4",
      "unit": "g/dL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2024-02-28T23:46:36Z"
    },
    {
      "name": "Erythrocytes [#/volume] in Blood by Automated count",
      "value": "4.5",
      "unit": "10*6/uL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2024-02-28T23:46:36Z"
    },
    {
      "name": "Leukocytes [#/volume] in Blood by Automated count",
      "value": "7.1",
      "unit": "10*3/uL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2024-02-28T23:46:36Z"
    },
    {
      "name": "Heart rate",
      "value": "88.0",
      "unit": "/min",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-03-11T23:46:36Z"
    },
    {
      "name": "Body Height",
      "value": "127.1",
      "unit": "cm",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-03-11T23:46:36Z"
    },
    {
      "name": "Pain severity - 0-10 verbal numeric rating [Score] - Reported",
      "value": "0.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-03-11T23:46:36Z"
    },
    {
      "name": "Body Weight",
      "value": "25.2",
      "unit": "kg",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-03-11T23:46:36Z"
    },
    {
      "name": "Body mass index (BMI) [Ratio]",
      "value": "15.6",
      "unit": "kg/m2",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-03-11T23:46:36Z"
    },
    {
      "name": "Body mass index (BMI) [Percentile] Per age and sex",
      "value": "45.5",
      "unit": "%",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-03-11T23:46:36Z"
    },
    {
      "name": "Diastolic Blood Pressure",
      "value": "68.0",
      "unit": "mm[Hg]",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-03-11T23:46:36Z"
    },
    {
      "name": "Systolic Blood Pressure",
      "value": "109.0",
      "unit": "mm[Hg]",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-03-11T23:46:36Z"
    },
    {
      "name": "Respiratory rate",
      "value": "15.0",
      "unit": "/min",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2026-03-11T23:46:36Z"
    }
  ],
  "clinical_text": null,
  "context": {
    "situation": "outpatient",
    "roles": [
      "physician",
      "patient",
      "guardian"
    ],
    "accessibility_score": 0.72
  },
  "quality": {
    "reflexion_loops": 3,
    "chosen_loop": [
      2,
      0.75
    ],
    "hallucination_flags": [
      "[NR5] Multiple duplicate diagnoses with the same ICD-10 code and is_active status",
      "[NR5] Diagnosis with ICD-10 code Z86.41 has is_active: true when other entries with the same code have is_active: false"
    ],
    "reason_codes": [
      "NR5"
    ],
    "q_index": 0.75,
    "status": "NEEDS_REVIEW"
  },
  "encounter_date": null,
  "flagged": false,
  "created_at": "2026-07-17T07:35:32.464792"
}
```

## 예시 A - 28세 (1회차 즉시 AI_READY 통과)

```json
{
  "record_id": "8673d047-a0c9-45e3-b213-ad6a70dc5875",
  "source": "synthea",
  "patient_id": "5094c0f7-119a-924c-13ef-53d054461d21",
  "age": 28,
  "gender": "M",
  "chief_complaint": "Patient referral for dental care (procedure)",
  "symptoms": [
    "Within the last year  have you been afraid of your partner or ex-partner",
    "Has lack of transportation kept you from medical appointments  meetings  work  or from getting things needed for daily living",
    "Influenza virus A Ag [Presence] in Upper respiratory specimen by Rapid immunoassay",
    "Influenza virus B Ag [Presence] in Upper respiratory specimen by Rapid immunoassay",
    "SARS-CoV-2 (COVID-19) RNA panel - Respiratory system specimen by NAA with probe detection"
  ],
  "diagnoses": [
    {
      "icd10_code": "J30.1",
      "description": "Allergic rhinitis due to pollen",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2001-02-17"
    },
    {
      "icd10_code": "M41.12",
      "description": "Adolescent idiopathic scoliosis",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2008-09-18"
    },
    {
      "icd10_code": "G89.2",
      "description": "Chronic pain, not elsewhere classified",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2016-01-11"
    },
    {
      "icd10_code": "M54.5",
      "description": "Low back pain",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2016-01-11"
    },
    {
      "icd10_code": "Z86.41",
      "description": "Medication review due (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2016-08-20"
    },
    {
      "icd10_code": "Z01.30",
      "description": "Encounter for examination of blood pressure without abnormal findings",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2016-08-20"
    },
    {
      "icd10_code": "Z85.4",
      "description": "Full-time employment (finding)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2016-08-20"
    },
    {
      "icd10_code": "Z60.4",
      "description": "Social exclusion and rejection",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2016-08-20"
    },
    {
      "icd10_code": "J00",
      "description": "Acute nasopharyngitis [common cold]",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2020-05-19"
    },
    {
      "icd10_code": "Z86.41",
      "description": "Medication review due (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2020-08-29"
    },
    {
      "icd10_code": "J11.9",
      "description": "Suspected disease caused by Severe acute respiratory coronavirus 2 (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2021-01-10"
    },
    {
      "icd10_code": "R05",
      "description": "Cough",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2021-01-10"
    },
    {
      "icd10_code": "R50.9",
      "description": "Fever, unspecified",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2021-01-10"
    },
    {
      "icd10_code": "U07.1",
      "description": "Emergency use of U07.1 | COVID-19",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2021-01-10"
    },
    {
      "icd10_code": "Z73.3",
      "description": "Stress, not elsewhere classified",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2023-09-02"
    }
  ],
  "medications": [
    {
      "name": "Fexofenadine hydrochloride 30 MG Oral Tablet",
      "dose": 30.0,
      "unit": "mg",
      "route": null,
      "frequency": null,
      "is_active": true
    },
    {
      "name": "NDA020800 0.3 ML Epinephrine 1 MG/ML Auto-Injector",
      "dose": 0.3,
      "unit": "mL",
      "route": null,
      "frequency": null,
      "is_active": true
    },
    {
      "name": "sodium fluoride 0.0272 MG/MG Oral Gel",
      "dose": 0.0272,
      "unit": "mg",
      "route": null,
      "frequency": null,
      "is_active": false
    }
  ],
  "observations": [
    {
      "name": "Total score [HARK]",
      "value": "0.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-08-20T10:07:32Z"
    },
    {
      "name": "Body mass index (BMI) [Percentile] Per age and sex",
      "value": "8.1",
      "unit": "%",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2017-08-26T08:49:12Z"
    },
    {
      "name": "Total score [AUDIT-C]",
      "value": "3.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2017-08-26T10:55:52Z"
    },
    {
      "name": "MCV [Entitic mean volume] in Red Blood Cells by Automated count",
      "value": "88.5",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2020-08-29T08:49:12Z"
    },
    {
      "name": "MCH [Entitic mass] by Automated count",
      "value": "31.6",
      "unit": "pg",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2020-08-29T08:49:12Z"
    },
    {
      "name": "MCHC [Entitic Mass/volume] in Red Blood Cells by Automated count",
      "value": "34.8",
      "unit": "g/dL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2020-08-29T08:49:12Z"
    },
    {
      "name": "Platelet [Entitic mean volume] in Blood by Automated count",
      "value": "11.6",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2020-08-29T08:49:12Z"
    },
    {
      "name": "Platelets [#/volume] in Blood by Automated count",
      "value": "398.7",
      "unit": "10*3/uL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2020-08-29T08:49:12Z"
    },
    {
      "name": "Platelet distribution width [Entitic volume] in Blood by Automated count",
      "value": "376.0",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2020-08-29T08:49:12Z"
    },
    {
      "name": "Hematocrit [Volume Fraction] of Blood by Automated count",
      "value": "49.1",
      "unit": "%",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2020-08-29T08:49:12Z"
    },
    {
      "name": "Erythrocyte [DistWidth] in Blood by Automated count",
      "value": "44.0",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2020-08-29T08:49:12Z"
    },
    {
      "name": "Hemoglobin [Mass/volume] in Blood",
      "value": "16.4",
      "unit": "g/dL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2020-08-29T08:49:12Z"
    },
    {
      "name": "Leukocytes [#/volume] in Blood by Automated count",
      "value": "5.6",
      "unit": "10*3/uL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2020-08-29T08:49:12Z"
    },
    {
      "name": "Erythrocytes [#/volume] in Blood by Automated count",
      "value": "3.9",
      "unit": "10*6/uL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2020-08-29T08:49:12Z"
    },
    {
      "name": "Generalized anxiety disorder 7 item (GAD-7) total score [Reported.PHQ]",
      "value": "2.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2020-08-29T09:42:56Z"
    },
    {
      "name": "Total score [DAST-10]",
      "value": "0.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2020-08-29T10:52:03Z"
    },
    {
      "name": "Body temperature",
      "value": "37.9",
      "unit": "Cel",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2021-01-10T08:49:12Z"
    },
    {
      "name": "Oxygen saturation in Arterial blood",
      "value": "88.6",
      "unit": "%",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2021-01-10T08:49:12Z"
    },
    {
      "name": "Body Height",
      "value": "171.3",
      "unit": "cm",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-09-02T08:49:12Z"
    },
    {
      "name": "Pain severity - 0-10 verbal numeric rating [Score] - Reported",
      "value": "2.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-09-02T08:49:12Z"
    },
    {
      "name": "Body Weight",
      "value": "66.3",
      "unit": "kg",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-09-02T08:49:12Z"
    },
    {
      "name": "Body mass index (BMI) [Ratio]",
      "value": "22.6",
      "unit": "kg/m2",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-09-02T08:49:12Z"
    },
    {
      "name": "Diastolic Blood Pressure",
      "value": "89.0",
      "unit": "mm[Hg]",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-09-02T08:49:12Z"
    },
    {
      "name": "Systolic Blood Pressure",
      "value": "125.0",
      "unit": "mm[Hg]",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-09-02T08:49:12Z"
    },
    {
      "name": "Heart rate",
      "value": "66.0",
      "unit": "/min",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-09-02T08:49:12Z"
    },
    {
      "name": "Respiratory rate",
      "value": "15.0",
      "unit": "/min",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-09-02T08:49:12Z"
    },
    {
      "name": "How many people are living or staying at this address [#]",
      "value": "8.0",
      "unit": "{#}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-09-02T09:46:35Z"
    },
    {
      "name": "Patient Health Questionnaire 2 item (PHQ-2) total score [Reported]",
      "value": "0.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-09-02T10:22:29Z"
    }
  ],
  "clinical_text": null,
  "context": {
    "situation": "outpatient",
    "roles": [
      "physician",
      "patient"
    ],
    "accessibility_score": 1.0
  },
  "quality": {
    "reflexion_loops": 1,
    "chosen_loop": [
      1,
      1.0
    ],
    "hallucination_flags": [],
    "reason_codes": [],
    "q_index": 1.0,
    "status": "AI_READY"
  },
  "encounter_date": "2023-09-16T08:49:12Z",
  "flagged": false,
  "created_at": "2026-07-17T07:37:06.589717"
}
```

## 예시 B - 29세 (NR11, 관찰값 타당성 검증)

```json
{
  "record_id": "dfdd7e7e-09f2-4ef2-94c0-50814b42e514",
  "source": "synthea",
  "patient_id": "01ba763c-ce8b-7610-7ff0-c5ed527ec673",
  "age": 29,
  "gender": "M",
  "chief_complaint": "Sepsis (disorder)",
  "symptoms": [
    "Drugs of abuse 5 panel - Urine by Screen method",
    "Within the last year  have you been afraid of your partner or ex-partner",
    "Has lack of transportation kept you from medical appointments  meetings  work  or from getting things needed for daily living",
    "Gram positive blood culture panel by Probe in Positive blood culture",
    "Capillary refill [Time] of Nail bed"
  ],
  "diagnoses": [
    {
      "icd10_code": "Z86.41",
      "description": "Medication review due (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2012-04-15"
    },
    {
      "icd10_code": "J00",
      "description": "Acute nasopharyngitis [common cold]",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2014-05-11"
    },
    {
      "icd10_code": "G89.2",
      "description": "Chronic pain, not elsewhere classified",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2015-04-14"
    },
    {
      "icd10_code": "M54.5",
      "description": "Low back pain",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2015-04-14"
    },
    {
      "icd10_code": "M75.229",
      "description": "Chronic neck pain (finding)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2015-04-14"
    },
    {
      "icd10_code": "Z85.4",
      "description": "Received higher education (finding)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2015-05-03"
    },
    {
      "icd10_code": "Z85.4",
      "description": "Part-time employment (finding)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2015-05-03"
    },
    {
      "icd10_code": "Z73.3",
      "description": "Stress, not elsewhere classified",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2015-05-03"
    },
    {
      "icd10_code": "F23.9",
      "description": "Reports of violence in the environment (finding)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2015-05-03"
    },
    {
      "icd10_code": "K02.0",
      "description": "Gingivitis (disorder)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2015-05-03"
    },
    {
      "icd10_code": "Z85.4",
      "description": "Full-time employment (finding)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2017-05-14"
    },
    {
      "icd10_code": "Z86.41",
      "description": "Medication review due (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2018-05-20"
    },
    {
      "icd10_code": "F14.21",
      "description": "Cocaine dependence, in remission",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2018-05-20"
    },
    {
      "icd10_code": "Z73.3",
      "description": "Stress, not elsewhere classified",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2019-05-26"
    },
    {
      "icd10_code": "Z85.81",
      "description": "Part-time employment (finding)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2020-05-31"
    },
    {
      "icd10_code": "Z86.41",
      "description": "Medication review due (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2021-06-06"
    },
    {
      "icd10_code": "Z85.4",
      "description": "Full-time employment (finding)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2021-06-06"
    },
    {
      "icd10_code": "Z73.3",
      "description": "Stress, not elsewhere classified",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2021-06-06"
    },
    {
      "icd10_code": "Z86.41",
      "description": "Medication review due (situation)",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": false,
      "onset_date": "2022-06-12"
    },
    {
      "icd10_code": "A41.9",
      "description": "Sepsis, unspecified organism",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2023-04-06"
    },
    {
      "icd10_code": "J80",
      "description": "Acute respiratory distress syndrome",
      "confidence": "confirmed",
      "is_negated": false,
      "is_active": true,
      "onset_date": "2023-04-11"
    }
  ],
  "medications": [
    {
      "name": "Acetaminophen 300 MG / Codeine Phosphate 15 MG Oral Tablet",
      "dose": 300.0,
      "unit": "mg",
      "route": null,
      "frequency": null,
      "is_active": true
    },
    {
      "name": "Acetaminophen 300 MG / Hydrocodone Bitartrate 5 MG Oral Tablet",
      "dose": 300.0,
      "unit": "mg",
      "route": null,
      "frequency": null,
      "is_active": true
    },
    {
      "name": "4 ML norepinephrine 1 MG/ML Injection",
      "dose": 4.0,
      "unit": "mL",
      "route": null,
      "frequency": null,
      "is_active": false
    },
    {
      "name": "piperacillin 2000 MG / tazobactam 250 MG Injection",
      "dose": 2000.0,
      "unit": "mg",
      "route": null,
      "frequency": null,
      "is_active": false
    },
    {
      "name": "150 ML vancomycin 5 MG/ML Injection",
      "dose": 150.0,
      "unit": "mL",
      "route": null,
      "frequency": null,
      "is_active": false
    },
    {
      "name": "sodium fluoride 0.0272 MG/MG Oral Gel",
      "dose": 0.0272,
      "unit": "mg",
      "route": null,
      "frequency": null,
      "is_active": false
    }
  ],
  "observations": [
    {
      "name": "Patient Health Questionnaire-9: Modified for Teens total score [Reported.PHQ.Teen]",
      "value": "4.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2014-04-20T02:07:28Z"
    },
    {
      "name": "Body temperature",
      "value": "37.3",
      "unit": "Cel",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2014-05-11T01:26:36Z"
    },
    {
      "name": "What number best describes how pain has interfered with your general activity during the past week",
      "value": "7.9",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2015-06-05T18:26:36Z"
    },
    {
      "name": "What number best describes how pain has interfered with your enjoyment of life during the past week",
      "value": "7.4",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2015-06-05T18:26:36Z"
    },
    {
      "name": "Pain severity in the past week - 0-10 numeric rating [Reported]",
      "value": "6.4",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2015-06-05T18:26:36Z"
    },
    {
      "name": "Body mass index (BMI) [Percentile] Per age and sex",
      "value": "20.1",
      "unit": "%",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2016-05-08T01:26:36Z"
    },
    {
      "name": "MCV [Entitic mean volume] in Red Blood Cells by Automated count",
      "value": "94.3",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2018-05-20T01:26:36Z"
    },
    {
      "name": "MCH [Entitic mass] by Automated count",
      "value": "28.4",
      "unit": "pg",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2018-05-20T01:26:36Z"
    },
    {
      "name": "MCHC [Entitic Mass/volume] in Red Blood Cells by Automated count",
      "value": "35.0",
      "unit": "g/dL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2018-05-20T01:26:36Z"
    },
    {
      "name": "Platelet [Entitic mean volume] in Blood by Automated count",
      "value": "11.8",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2018-05-20T01:26:36Z"
    },
    {
      "name": "Platelets [#/volume] in Blood by Automated count",
      "value": "272.2",
      "unit": "10*3/uL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2018-05-20T01:26:36Z"
    },
    {
      "name": "Platelet distribution width [Entitic volume] in Blood by Automated count",
      "value": "180.7",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2018-05-20T01:26:36Z"
    },
    {
      "name": "Hematocrit [Volume Fraction] of Blood by Automated count",
      "value": "45.6",
      "unit": "%",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2018-05-20T01:26:36Z"
    },
    {
      "name": "Erythrocyte [DistWidth] in Blood by Automated count",
      "value": "45.6",
      "unit": "fL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2018-05-20T01:26:36Z"
    },
    {
      "name": "Erythrocytes [#/volume] in Blood by Automated count",
      "value": "5.5",
      "unit": "10*6/uL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2018-05-20T01:26:36Z"
    },
    {
      "name": "Hemoglobin [Mass/volume] in Blood",
      "value": "14.6",
      "unit": "g/dL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2018-05-20T01:26:36Z"
    },
    {
      "name": "Leukocytes [#/volume] in Blood by Automated count",
      "value": "6.7",
      "unit": "10*3/uL",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2018-05-20T01:26:36Z"
    },
    {
      "name": "Total score [AUDIT-C]",
      "value": "3.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2020-05-31T03:13:02Z"
    },
    {
      "name": "Total score [HARK]",
      "value": "0.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2021-06-06T03:06:18Z"
    },
    {
      "name": "Patient Health Questionnaire 2 item (PHQ-2) total score [Reported]",
      "value": "5.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2021-06-06T03:48:25Z"
    },
    {
      "name": "Patient Health Questionnaire 9 item (PHQ-9) total score [Reported]",
      "value": "4.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2021-06-06T04:18:16Z"
    },
    {
      "name": "Body Height",
      "value": "184.9",
      "unit": "cm",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2022-06-12T01:26:36Z"
    },
    {
      "name": "Pain severity - 0-10 verbal numeric rating [Score] - Reported",
      "value": "2.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2022-06-12T01:26:36Z"
    },
    {
      "name": "Body Weight",
      "value": "79.5",
      "unit": "kg",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2022-06-12T01:26:36Z"
    },
    {
      "name": "Body mass index (BMI) [Ratio]",
      "value": "23.2",
      "unit": "kg/m2",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2022-06-12T01:26:36Z"
    },
    {
      "name": "Heart rate",
      "value": "85.0",
      "unit": "/min",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2022-06-12T01:26:36Z"
    },
    {
      "name": "Respiratory rate",
      "value": "14.0",
      "unit": "/min",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2022-06-12T01:26:36Z"
    },
    {
      "name": "How many people are living or staying at this address [#]",
      "value": "4.0",
      "unit": "{#}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2022-06-12T02:14:58Z"
    },
    {
      "name": "Generalized anxiety disorder 7 item (GAD-7) total score [Reported.PHQ]",
      "value": "3.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2022-06-12T02:35:50Z"
    },
    {
      "name": "Total score [DAST-10]",
      "value": "2.0",
      "unit": "{score}",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2022-06-12T03:10:21Z"
    },
    {
      "name": "Oxygen saturation in Arterial blood",
      "value": "90.0",
      "unit": "%",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-04-06T01:26:36Z"
    },
    {
      "name": "Mean blood pressure",
      "value": "92.9",
      "unit": "mm[Hg]",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-04-06T01:56:36Z"
    },
    {
      "name": "Diastolic Blood Pressure",
      "value": "61.2",
      "unit": "mm[Hg]",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-04-11T16:26:36Z"
    },
    {
      "name": "Lactate [Moles/volume] in Blood",
      "value": "1.6",
      "unit": "mmol/L",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-04-11T16:26:36Z"
    },
    {
      "name": "Systolic Blood Pressure",
      "value": "46.0",
      "unit": "mm[Hg]",
      "reference_range": null,
      "is_abnormal": null,
      "observed_date": "2023-04-11T16:26:36Z"
    }
  ],
  "clinical_text": null,
  "context": {
    "situation": "outpatient",
    "roles": [
      "physician",
      "patient"
    ],
    "accessibility_score": 1.0
  },
  "quality": {
    "reflexion_loops": 1,
    "chosen_loop": [
      1,
      0.9
    ],
    "hallucination_flags": [
      "[NR11] Systolic Blood Pressure value of 46.0 mm[Hg] is implausibly low for an adult"
    ],
    "reason_codes": [
      "NR11"
    ],
    "q_index": 0.9,
    "status": "NEEDS_REVIEW"
  },
  "encounter_date": "2023-04-06T01:26:36Z",
  "flagged": false,
  "created_at": "2026-07-17T07:37:24.186279"
}
```
