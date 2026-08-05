# Data dictionary
Machine-generated from the CSV files in the working directory. Every figure below is computed directly from the data.
Code/description pairs are ranked by **distinct patients** carrying the code, not by row count.

**Patient roster: 3539 patients in `patients.csv`.**

---

## `patients.csv`

- Rows: **3539**
- Distinct patients: **3539** (100.0% of the 3539-patient roster)

### Columns

| column | type | % null | distinct values |
| --- | --- | ---: | ---: |
| `Id` | text | 0.0 | 3539 |
| `BIRTHDATE` | text | 0.0 | 1947 |
| `DEATHDATE` | text | 56.5 | 1474 |
| `SSN` | text | 0.0 | 3532 |
| `DRIVERS` | text | 1.6 | 3424 |
| `PASSPORT` | text | 2.9 | 3435 |
| `PREFIX` | text | 1.7 | 3 |
| `FIRST` | text | 0.0 | 2212 |
| `LAST` | text | 0.0 | 629 |
| `SUFFIX` | text | 98.2 | 3 |
| `MAIDEN` | text | 68.5 | 491 |
| `MARITAL` | text | 8.3 | 2 |
| `RACE` | text | 0.0 | 5 |
| `ETHNICITY` | text | 0.0 | 2 |
| `GENDER` | text | 0.0 | 2 |
| `BIRTHPLACE` | text | 0.0 | 424 |
| `ADDRESS` | text | 0.0 | 3539 |
| `CITY` | text | 0.0 | 322 |
| `STATE` | text | 0.0 | 1 |
| `COUNTY` | text | 0.0 | 14 |
| `ZIP` | numeric (as text) | 46.9 | 270 |
| `LAT` | numeric (as text) | 0.0 | 3539 |
| `LON` | numeric (as text) | 0.0 | 3539 |
| `HEALTHCARE_EXPENSES` | numeric (as text) | 0.0 | 3539 |
| `HEALTHCARE_COVERAGE` | numeric (as text) | 0.0 | 3386 |

### Low-cardinality columns

Every non-identifier column with 25 or fewer distinct values, enumerated with row counts.

**`MARITAL`** — 2 distinct

| value | rows |
| --- | ---: |
| M | 2604 |
| S | 643 |

**`RACE`** — 5 distinct

| value | rows |
| --- | ---: |
| white | 2978 |
| black | 316 |
| asian | 233 |
| native | 9 |
| other | 3 |

**`ETHNICITY`** — 2 distinct

| value | rows |
| --- | ---: |
| nonhispanic | 3202 |
| hispanic | 337 |

**`GENDER`** — 2 distinct

| value | rows |
| --- | ---: |
| M | 1978 |
| F | 1561 |

**`STATE`** — 1 distinct

| value | rows |
| --- | ---: |
| Massachusetts | 3539 |

**`COUNTY`** — 14 distinct

| value | rows |
| --- | ---: |
| Middlesex County | 792 |
| Worcester County | 457 |
| Suffolk County | 402 |
| Norfolk County | 396 |
| Essex County | 338 |
| Bristol County | 328 |
| Plymouth County | 256 |
| Hampden County | 247 |
| Barnstable County | 101 |
| Hampshire County | 97 |
| Berkshire County | 74 |
| Franklin County | 32 |
| Dukes County | 13 |
| Nantucket County | 6 |

---

## `conditions.csv`

- Rows: **35874**
- Distinct patients: **3535** (99.9% of the 3539-patient roster)

### Columns

| column | type | % null | distinct values |
| --- | --- | ---: | ---: |
| `START` | text | 0.0 | 17396 |
| `STOP` | text | 61.3 | 7770 |
| `PATIENT` | text | 0.0 | 3535 |
| `ENCOUNTER` | text | 0.0 | 31091 |
| `CODE` | numeric (as text) | 0.0 | 152 |
| `DESCRIPTION` | text | 0.0 | 152 |

### Most frequent CODE / DESCRIPTION pairs

Top 40 of **152** distinct pairs, ranked by distinct patients.

| CODE | DESCRIPTION | patients | rows |
| --- | --- | ---: | ---: |
| `444814009` | Viral sinusitis (disorder) | 2361 | 3956 |
| `162864005` | Body mass index 30+ - obesity (finding) | 1863 | 1863 |
| `195662009` | Acute viral pharyngitis (disorder) | 1645 | 2205 |
| `15777000` | Prediabetes | 1516 | 1516 |
| `271737000` | Anemia (disorder) | 1493 | 1493 |
| `10509002` | Acute bronchitis (disorder) | 1394 | 1741 |
| `59621000` | Hypertension | 1126 | 1126 |
| `40055000` | Chronic sinusitis (disorder) | 1077 | 1095 |
| `19169002` | Miscarriage in first trimester | 857 | 857 |
| `55822004` | Hyperlipidemia | 831 | 831 |
| `230690007` | Stroke | 761 | 761 |
| `64859006` | Osteoporosis (disorder) | 577 | 577 |
| `53741008` | Coronary Heart Disease | 565 | 565 |
| `68496003` | Polyp of colon | 539 | 606 |
| `26929004` | Alzheimer's disease (disorder) | 462 | 462 |
| `49436004` | Atrial Fibrillation | 454 | 454 |
| `22325002` | Abnormal gait (finding) | 382 | 382 |
| `44054006` | Diabetes | 382 | 382 |
| `723857007` | Silent micro-hemorrhage of brain (disorder) | 382 | 382 |
| `302870006` | Hypertriglyceridemia (disorder) | 380 | 380 |
| `126906006` | Neoplasm of prostate | 378 | 378 |
| `237602007` | Metabolic syndrome X (disorder) | 378 | 378 |
| `72892002` | Normal pregnancy | 374 | 1007 |
| `43878008` | Streptococcal sore throat (disorder) | 371 | 400 |
| `239873007` | Osteoarthritis of knee | 360 | 360 |
| `92691004` | Carcinoma in situ of prostate (disorder) | 350 | 350 |
| `44465007` | Sprain of ankle | 345 | 365 |
| `88805009` | Chronic congestive heart failure (disorder) | 332 | 332 |
| `65966004` | Fracture of forearm | 276 | 300 |
| `443165006` | Pathological fracture due to osteoporosis (disorder) | 239 | 320 |
| `127013003` | Diabetic renal disease (disorder) | 234 | 234 |
| `386806002` | Impaired cognition (finding) | 230 | 230 |
| `428251008` | History of appendectomy | 228 | 228 |
| `74400008` | Appendicitis | 228 | 228 |
| `713197008` | Recurrent rectal polyp | 227 | 232 |
| `36971009` | Sinusitis (disorder) | 222 | 233 |
| `431855005` | Chronic kidney disease stage 1 (disorder) | 221 | 221 |
| `75498004` | Acute bacterial sinusitis (disorder) | 216 | 220 |
| `22298006` | Myocardial Infarction | 216 | 216 |
| `399211009` | History of myocardial infarction (situation) | 216 | 216 |

### Complete code inventory — remaining 112 pairs

Same ranking continued, so the full set of codes present in this file is listed.

| CODE | DESCRIPTION | patients | rows |
| --- | --- | ---: | ---: |
| `80394007` | Hyperglycemia (disorder) | 203 | 203 |
| `55680006` | Drug overdose | 200 | 200 |
| `410429000` | Cardiac Arrest | 197 | 197 |
| `429007001` | History of cardiac arrest (situation) | 197 | 197 |
| `124171000119105` | Chronic intractable migraine without aura | 188 | 188 |
| `82423001` | Chronic pain | 188 | 188 |
| `62106007` | Concussion with no loss of consciousness | 185 | 190 |
| `196416002` | Impacted molars | 182 | 182 |
| `39848009` | Whiplash injury to neck | 177 | 181 |
| `263102004` | Fracture subluxation of wrist | 172 | 181 |
| `233604007` | Pneumonia | 166 | 166 |
| `249944006` | Monoparesis - arm (disorder) | 162 | 162 |
| `58150001` | Fracture of clavicle | 159 | 167 |
| `309557009` | Numbness of face (finding) | 152 | 152 |
| `70704007` | Sprain of wrist | 150 | 151 |
| `201834006` | Localized  primary osteoarthritis of the hand | 148 | 148 |
| `16114001` | Fracture of ankle | 147 | 157 |
| `65363002` | Otitis media | 146 | 184 |
| `162573006` | Suspected lung cancer (situation) | 146 | 146 |
| `254837009` | Malignant neoplasm of breast (disorder) | 143 | 143 |
| `368581000119106` | Neuropathy due to type 2 diabetes mellitus (disorder) | 139 | 139 |
| `128613002` | Seizure disorder | 137 | 137 |
| `703151001` | History of single seizure (situation) | 137 | 137 |
| `449868002` | Smokes tobacco daily | 132 | 132 |
| `254637007` | Non-small cell lung cancer (disorder) | 127 | 127 |
| `424132000` | Non-small cell carcinoma of lung  TNM stage 1 (disorder) | 127 | 127 |
| `79586000` | Tubal pregnancy | 123 | 135 |
| `284551006` | Laceration of foot | 121 | 123 |
| `284549007` | Laceration of hand | 116 | 118 |
| `239872002` | Osteoarthritis of hip | 115 | 115 |
| `422034002` | Diabetic retinopathy associated with type II diabetes mellitus (disorder) | 111 | 111 |
| `87433001` | Pulmonary emphysema (disorder) | 105 | 105 |
| `283371005` | Laceration of forearm | 104 | 104 |
| `7200002` | Alcoholism | 103 | 103 |
| `370247008` | Facial laceration | 100 | 102 |
| `359817006` | Closed fracture of hip | 96 | 102 |
| `283385000` | Laceration of thigh | 86 | 88 |
| `84757009` | Epilepsy | 84 | 84 |
| `5602001` | Opioid abuse (disorder) | 82 | 82 |
| `156073000` | Fetus with unknown complication | 78 | 85 |
| `185086009` | Chronic obstructive bronchitis (disorder) | 77 | 77 |
| `47693006` | Rupture of appendix | 77 | 77 |
| `403190006` | First degree burn | 75 | 77 |
| `33737001` | Fracture of rib | 70 | 71 |
| `8011004` | Dysarthria (finding) | 68 | 68 |
| `1551000119108` | Nonproliferative diabetic retinopathy due to type 2 diabetes mellitus (disorder) | 66 | 66 |
| `403191005` | Second degree burn | 65 | 65 |
| `314994000` | Metastasis from malignant tumor of prostate (disorder) | 62 | 62 |
| `363406005` | Malignant tumor of colon | 59 | 59 |
| `301011002` | Escherichia coli urinary tract infection | 56 | 61 |
| `197927001` | Recurrent urinary tract infection | 55 | 55 |
| `90560007` | Gout | 52 | 52 |
| `109838007` | Overlapping malignant neoplasm of colon | 51 | 51 |
| `307731004` | Injury of tendon of the rotator cuff of shoulder | 50 | 50 |
| `83664006` | Idiopathic atrophic hypothyroidism | 50 | 50 |
| `198992004` | Antepartum eclampsia | 47 | 50 |
| `62564004` | Concussion with loss of consciousness | 47 | 48 |
| `35999006` | Blighted ovum | 46 | 48 |
| `230265002` | Familial Alzheimer's disease of early onset (disorder) | 45 | 45 |
| `232353008` | Perennial allergic rhinitis with seasonal variation | 44 | 44 |
| `398254007` | Preeclampsia | 42 | 46 |
| `262574004` | Bullet wound | 39 | 39 |
| `38822007` | Cystitis | 38 | 43 |
| `446096008` | Perennial allergic rhinitis | 37 | 37 |
| `90781000119102` | Microalbuminuria due to type 2 diabetes mellitus (disorder) | 35 | 35 |
| `408512008` | Body mass index 40+ - severely obese (finding) | 34 | 34 |
| `431856006` | Chronic kidney disease stage 2 (disorder) | 34 | 34 |
| `27942005` | Shock (disorder) | 32 | 32 |
| `97331000119101` | Macular edema and retinopathy due to type 2 diabetes mellitus (disorder) | 32 | 32 |
| `444448004` | Injury of medial collateral ligament of knee | 30 | 30 |
| `110030002` | Concussion injury of brain | 28 | 28 |
| `236077008` | Protracted diarrhea | 28 | 28 |
| `6072007` | Bleeding from anus | 28 | 28 |
| `95417003` | Primary fibromyalgia syndrome | 28 | 28 |
| `367498001` | Seasonal allergic rhinitis | 26 | 26 |
| `1501000119109` | Proliferative diabetic retinopathy due to type II diabetes mellitus (disorder) | 25 | 25 |
| `24079001` | Atopic dermatitis | 24 | 24 |
| `275272006` | Brain damage - traumatic | 24 | 24 |
| `93761005` | Primary malignant neoplasm of colon | 24 | 24 |
| `370143000` | Major depression disorder | 22 | 22 |
| `444470001` | Injury of anterior cruciate ligament | 22 | 22 |
| `30832001` | Rupture of patellar tendon | 20 | 20 |
| `69896004` | Rheumatoid arthritis | 20 | 20 |
| `254632001` | Small cell carcinoma of lung (disorder) | 19 | 19 |
| `67811000119102` | Primary small cell malignant neoplasm of lung  TNM stage 1 (disorder) | 19 | 19 |
| `239720000` | Tear of meniscus of knee | 18 | 18 |
| `233678006` | Childhood asthma | 15 | 15 |
| `192127007` | Child attention deficit disorder | 14 | 14 |
| `241929008` | Acute allergic reaction | 13 | 13 |
| `94260004` | Secondary malignant neoplasm of colon | 12 | 12 |
| `235919008` | Cholelithiasis | 10 | 10 |
| `40275004` | Contact dermatitis | 10 | 10 |
| `65275009` | Acute Cholecystitis | 10 | 10 |
| `1734006` | Fracture of the vertebral column with spinal cord injury | 8 | 8 |
| `698754002` | Chronic paralysis due to lesion of spinal cord | 8 | 8 |
| `403192003` | Third degree burn | 7 | 7 |
| `15724005` | Fracture of vertebral column without spinal cord injury | 5 | 5 |
| `127295002` | Traumatic brain injury (disorder) | 4 | 4 |
| `195967001` | Asthma | 4 | 4 |
| `429280009` | History of amputation of foot (situation) | 4 | 4 |
| `47505003` | Posttraumatic stress disorder | 3 | 3 |
| `161622006` | History of lower limb amputation (situation) | 2 | 2 |
| `200936003` | Lupus erythematosus | 2 | 2 |
| `11218009` | Infection caused by Pseudomonas aeruginosa | 1 | 1 |
| `157141000119108` | Proteinuria due to type 2 diabetes mellitus (disorder) | 1 | 1 |
| `190905008` | Cystic Fibrosis | 1 | 1 |
| `225444004` | At risk for suicide (finding) | 1 | 1 |
| `427089005` | Diabetes from Cystic Fibrosis | 1 | 1 |
| `433144002` | Chronic kidney disease stage 3 (disorder) | 1 | 1 |
| `60951000119105` | Blindness due to type 2 diabetes mellitus (disorder) | 1 | 1 |
| `65710008` | Acute respiratory failure (disorder) | 1 | 1 |
| `707577004` | Female Infertility | 1 | 1 |

---

## `medications.csv`

- Rows: **371210**
- Distinct patients: **3447** (97.4% of the 3539-patient roster)

### Columns

| column | type | % null | distinct values |
| --- | --- | ---: | ---: |
| `START` | text | 0.0 | 162803 |
| `STOP` | text | 3.2 | 156384 |
| `PATIENT` | text | 0.0 | 3447 |
| `PAYER` | text | 0.0 | 10 |
| `ENCOUNTER` | text | 0.0 | 176936 |
| `CODE` | numeric (as text) | 0.0 | 161 |
| `DESCRIPTION` | text | 0.0 | 164 |
| `BASE_COST` | numeric (as text) | 0.0 | 65554 |
| `PAYER_COVERAGE` | numeric (as text) | 0.0 | 48007 |
| `DISPENSES` | numeric (as text) | 0.0 | 987 |
| `TOTALCOST` | numeric (as text) | 0.0 | 92501 |
| `REASONCODE` | numeric (as text) | 22.4 | 40 |
| `REASONDESCRIPTION` | text | 22.4 | 40 |

### Most frequent CODE / DESCRIPTION pairs

Top 40 of **164** distinct pairs, ranked by distinct patients.

| CODE | DESCRIPTION | patients | rows |
| --- | --- | ---: | ---: |
| `313782` | Acetaminophen 325 MG Oral Tablet | 1665 | 2258 |
| `849574` | Naproxen sodium 220 MG Oral Tablet | 1055 | 1140 |
| `314231` | Simvastatin 10 MG Oral Tablet | 829 | 20631 |
| `562251` | Amoxicillin 250 MG / Clavulanate 125 MG Oral Tablet | 751 | 832 |
| `314076` | lisinopril 10 MG Oral Tablet | 731 | 51133 |
| `309362` | Clopidogrel 75 MG Oral Tablet | 714 | 8551 |
| `310965` | Ibuprofen 200 MG Oral Tablet | 695 | 790 |
| `705129` | Nitroglycerin 0.4 MG/ACTUAT Mucosal Spray | 585 | 12790 |
| `310798` | Hydrochlorothiazide 25 MG Oral Tablet | 574 | 41477 |
| `308136` | amLODIPine 2.5 MG Oral Tablet | 539 | 39819 |
| `312961` | Simvastatin 20 MG Oral Tablet | 476 | 9909 |
| `197361` | Amlodipine 5 MG Oral Tablet | 456 | 9093 |
| `197604` | Digoxin 0.125 MG Oral Tablet | 454 | 11181 |
| `855332` | Warfarin Sodium 5 MG Oral Tablet | 454 | 11181 |
| `897718` | Verapamil Hydrochloride 40 MG | 452 | 10821 |
| `1804799` | Alteplase 100 MG Injection | 448 | 539 |
| `1043400` | Acetaminophen 21.7 MG/ML / Dextromethorphan Hydrobromide 1 MG/ML / doxylamine succinate 0.417 MG/ML Oral Solution | 401 | 421 |
| `1362805` | Calcium Carbonate 1250 MG / Cholecalciferol 1000 UNT / Vitamin K 0.4 MG Chewable Tablet | 382 | 382 |
| `904419` | Alendronic acid 10 MG Oral Tablet | 374 | 374 |
| `1860480` | 1 ML DOCEtaxel 20 MG/ML Injection | 350 | 350 |
| `752899` | 0.25 ML Leuprolide Acetate 30 MG/ML Prefilled Syringe | 350 | 350 |
| `1049221` | Acetaminophen 325 MG / oxyCODONE Hydrochloride 5 MG Oral Tablet | 332 | 344 |
| `313988` | Furosemide 40 MG Oral Tablet | 331 | 2150 |
| `1719286` | 10 ML Furosemide 10 MG/ML Injection | 319 | 319 |
| `834102` | Penicillin V Potassium 500 MG Oral Tablet | 287 | 304 |
| `861467` | Meperidine Hydrochloride 50 MG Oral Tablet | 276 | 282 |
| `310436` | Galantamine 4 MG Oral Tablet | 267 | 267 |
| `106892` | insulin human  isophane 70 UNT/ML / Regular Insulin  Human 30 UNT/ML Injectable Suspension [Humulin] | 232 | 42284 |
| `857005` | Acetaminophen 325 MG / HYDROcodone Bitartrate 7.5 MG Oral Tablet | 231 | 239 |
| `2001499` | Vitamin B 12 5 MG/ML Injectable Solution | 226 | 226 |
| `860975` | 24 HR Metformin hydrochloride 500 MG Extended Release Oral Tablet | 215 | 28065 |
| `310325` | ferrous sulfate 325 MG Oral Tablet | 206 | 206 |
| `896209` | 60 ACTUAT Fluticasone propionate 0.25 MG/ACTUAT / salmeterol 0.05 MG/ACTUAT Dry Powder Inhaler | 174 | 4812 |
| `200033` | carvedilol 25 MG Oral Tablet | 165 | 988 |
| `1736776` | 10 ML oxaliplatin 5 MG/ML Injection | 164 | 164 |
| `1803932` | Leucovorin 100 MG Injection | 164 | 164 |
| `833036` | Captopril 25 MG Oral Tablet | 163 | 175 |
| `1736854` | Cisplatin 50 MG Injection | 146 | 6156 |
| `996740` | Memantine hydrochloride 2 MG/ML Oral Solution | 144 | 144 |
| `243670` | Aspirin 81 MG Oral Tablet | 136 | 174 |

### Complete code inventory — remaining 124 pairs

Same ranking continued, so the full set of codes present in this file is listed.

| CODE | DESCRIPTION | patients | rows |
| --- | --- | ---: | ---: |
| `979492` | losartan potassium 50 MG Oral Tablet | 134 | 758 |
| `757594` | Jolivette 28 Day Pack | 134 | 203 |
| `198031` | 24hr nicotine transdermal patch | 133 | 133 |
| `314077` | lisinopril 20 MG Oral Tablet | 132 | 782 |
| `583214` | PACLitaxel 100 MG Injection | 127 | 5011 |
| `1000126` | 1 ML medroxyprogesterone acetate 150 MG/ML Injection | 124 | 160 |
| `259255` | Atorvastatin 80 MG Oral Tablet | 120 | 129 |
| `748962` | Camila 28 Day Pack | 109 | 154 |
| `2123111` | NDA020503 200 ACTUAT Albuterol 0.09 MG/ACTUAT Metered Dose Inhaler | 108 | 7359 |
| `895994` | 120 ACTUAT Fluticasone propionate 0.044 MG/ACTUAT Metered Dose Inhaler | 108 | 7359 |
| `1100184` | Donepezil hydrochloride 23 MG Oral Tablet | 105 | 105 |
| `978950` | Natazia 28 Day Pack | 104 | 137 |
| `748879` | Levora 0.15/30 28 Day Pack | 103 | 128 |
| `389221` | Etonogestrel 68 MG Drug Implant | 102 | 138 |
| `106258` | Hydrocortisone 10 MG/ML Topical Cream | 101 | 102 |
| `308192` | Amoxicillin 500 MG Oral Tablet | 99 | 101 |
| `748856` | Yaz 28 Day Pack | 97 | 130 |
| `751905` | Trinessa 28 Day Pack | 97 | 122 |
| `749762` | Seasonique 91 Day Pack | 96 | 123 |
| `831533` | Errin 28 Day Pack | 86 | 120 |
| `807283` | Mirena 52 MG Intrauterine System | 85 | 109 |
| `1870230` | NDA020800 0.3 ML Epinephrine 1 MG/ML Auto-Injector | 84 | 84 |
| `1094107` | Phenazopyridine hydrochloride 100 MG Oral Tablet | 82 | 104 |
| `311989` | Nitrofurantoin 5 MG/ML Oral Suspension | 82 | 104 |
| `198014` | Naproxen 500 MG Oral Tablet | 74 | 80 |
| `1049630` | diphenhydrAMINE Hydrochloride 25 MG Oral Tablet | 72 | 72 |
| `1367439` | NuvaRing 0.12/0.015 MG per 24HR 21 Day Vaginal Ring | 71 | 77 |
| `997223` | Donepezil hydrochloride 10 MG Oral Tablet | 71 | 71 |
| `1190795` | Atropine Sulfate 1 MG/ML Injectable Solution | 68 | 69 |
| `1660014` | 1 ML Epinephrine 1 MG/ML Injection | 68 | 69 |
| `1599803` | 24 HR Donepezil hydrochloride 10 MG / Memantine hydrochloride 28 MG Extended Release Oral Capsule | 67 | 67 |
| `834357` | 3 ML Amiodarone hydrocholoride 50 MG/ML Prefilled Syringe | 63 | 64 |
| `1049221` | Acetaminophen 325 MG / Oxycodone Hydrochloride 5 MG Oral Tablet | 56 | 316 |
| `1860154` | Abuse-Deterrent 12 HR Oxycodone Hydrochloride 15 MG Extended Release Oral Tablet | 56 | 305 |
| `856987` | Acetaminophen 300 MG / HYDROcodone Bitartrate 5 MG Oral Tablet | 52 | 325 |
| `312938` | Sertraline 100 MG Oral Tablet | 52 | 52 |
| `1000126` | 1 ML medroxyPROGESTERone acetate 150 MG/ML Injection | 51 | 55 |
| `1656354` | sacubitril 97 MG / valsartan 103 MG Oral Tablet | 50 | 295 |
| `966222` | Levothyroxine Sodium 0.075 MG Oral Tablet | 50 | 50 |
| `313185` | Tacrine 10 MG Oral Capsule | 47 | 47 |
| `1534809` | 168 HR Ethinyl Estradiol 0.00146 MG/HR / norelgestromin 0.00625 MG/HR Transdermal System | 43 | 43 |
| `197591` | Diazepam 5 MG Oral Tablet | 41 | 54 |
| `235389` | Mestranol / Norethynodrel [Enovid] | 40 | 78 |
| `308971` | Carbamazepine[Tegretol] | 39 | 62 |
| `477045` | Chlorpheniramine Maleate 2 MG/ML Oral Solution | 38 | 38 |
| `204892` | clonazePAM 0.25 MG Oral Tablet | 37 | 52 |
| `197319` | Allopurinol 100 MG Oral Tablet | 37 | 47 |
| `309097` | Cefuroxime 250 MG Oral Tablet | 36 | 36 |
| `856980` | Acetaminophen/Hydrocodone | 36 | 36 |
| `834061` | Penicillin V Potassium 250 MG Oral Tablet | 34 | 37 |
| `1856546` | Kyleena 19.5 MG Intrauterine System | 30 | 30 |
| `198240` | Tamoxifen 10 MG Oral Tablet | 26 | 26 |
| `665078` | Loratadine 5 MG Chewable Tablet | 26 | 26 |
| `1605257` | Liletta 52 MG Intrauterine System | 24 | 26 |
| `313820` | Acetaminophen 160 MG Chewable Tablet | 23 | 28 |
| `205923` | 1 ML Epoetin Alfa 4000 UNT/ML Injection [Epogen] | 22 | 21331 |
| `997488` | Fexofenadine hydrochloride 30 MG Oral Tablet | 22 | 22 |
| `749882` | Norinyl 1+50 28 Day Pack | 21 | 27 |
| `197378` | Astemizole 10 MG Oral Tablet | 21 | 21 |
| `1734340` | Etoposide 100 MG Injection | 19 | 1145 |
| `583214` | Paclitaxel 100 MG Injection | 19 | 148 |
| `310385` | FLUoxetine 20 MG Oral Capsule | 17 | 27 |
| `749785` | Ortho Tri-Cyclen 28 Day Pack | 17 | 26 |
| `483438` | pregabalin 100 MG Oral Capsule | 16 | 27 |
| `596926` | duloxetine 20 MG Delayed Release Oral Capsule | 16 | 23 |
| `833135` | Milnacipran hydrochloride 100 MG Oral Tablet | 16 | 21 |
| `197541` | Colchicine 0.6 MG Oral Tablet | 14 | 15 |
| `311995` | NITROFURANTOIN  MACROCRYSTALS 50 MG Oral Capsule | 14 | 15 |
| `198405` | Ibuprofen 100 MG Oral Tablet | 13 | 13 |
| `312617` | predniSONE 5 MG Oral Tablet | 13 | 13 |
| `1946840` | Verzenio 100 MG Oral Tablet | 12 | 12 |
| `1740467` | 2 ML Ondansetron 2 MG/ML Injection | 10 | 20 |
| `1234995` | Rocuronium bromide 10 MG/ML Injectable Solution | 10 | 10 |
| `1659149` | Piperacillin 4000 MG / tazobactam 500 MG Injection | 10 | 10 |
| `1659263` | 1 ML heparin sodium  porcine 5000 UNT/ML Injection | 10 | 10 |
| `1732136` | 1 ML Morphine Sulfate 5 MG/ML Injection | 10 | 10 |
| `1808217` | 100 ML Propofol 10 MG/ML Injection | 10 | 10 |
| `313002` | Sodium Chloride 9 MG/ML Injectable Solution | 10 | 10 |
| `1732186` | 100 ML Epirubicin Hydrochloride 2 MG/ML Injection | 9 | 72 |
| `2119714` | 5 ML hyaluronidase-oysk 2000 UNT/ML / trastuzumab 120 MG/ML Injection | 9 | 9 |
| `311700` | Midazolam 1 MG/ML Injectable Solution | 9 | 9 |
| `241834` | cycloSPORINE  modified 100 MG Oral Capsule | 8 | 17 |
| `141918` | Terfenadine 60 MG Oral Tablet | 8 | 8 |
| `542347` | Isoflurane 999 MG/ML Inhalant Solution | 8 | 8 |
| `997501` | Fexofenadine hydrochloride 60 MG Oral Tablet | 7 | 7 |
| `1734919` | Cyclophosphamide 1000 MG Injection | 6 | 48 |
| `105585` | Methotrexate 2.5 MG Oral Tablet | 6 | 6 |
| `1363309` | Chlorpheniramine Maleate 4 MG Oral Tablet | 6 | 6 |
| `1650142` | Doxycycline Monohydrate 100 MG Oral Tablet | 6 | 6 |
| `311372` | Loratadine 10 MG Oral Tablet | 6 | 6 |
| `1790099` | 10 ML Doxorubicin Hydrochloride 2 MG/ML Injection | 5 | 35 |
| `1049635` | Acetaminophen 325 MG / oxyCODONE Hydrochloride 2.5 MG Oral Tablet | 5 | 7 |
| `1359133` | Estrostep Fe 28 Day Pack | 5 | 7 |
| `105078` | Penicillin G 375 MG/ML Injectable Solution | 5 | 6 |
| `1729584` | remifentanil 2 MG Injection | 5 | 5 |
| `309043` | 12 HR Cefaclor 500 MG Extended Release Oral Tablet | 5 | 5 |
| `727762` | 5 ML fulvestrant 50 MG/ML Prefilled Syringe | 5 | 5 |
| `1366343` | Levonorgestrel 0.00354 MG/HR Drug Implant | 4 | 6 |
| `1873983` | ribociclib 200 MG Oral Tablet | 4 | 4 |
| `308182` | Amoxicillin 250 MG Oral Capsule | 4 | 4 |
| `789980` | Ampicillin 100 MG/ML Injectable Solution | 4 | 4 |
| `312615` | predniSONE 20 MG Oral Tablet | 3 | 12 |
| `1014678` | cetirizine hydrochloride 10 MG Oral Tablet | 3 | 3 |
| `1601380` | palbociclib 100 MG Oral Capsule | 3 | 3 |
| `200064` | letrozole 2.5 MG Oral Tablet | 3 | 3 |
| `310261` | exemestane 25 MG Oral Tablet | 3 | 3 |
| `897122` | 3 ML liraglutide 6 MG/ML Pen Injector | 2 | 54 |
| `1091392` | Methylphenidate Hydrochloride 20 MG Oral Tablet | 2 | 2 |
| `1652673` | Doxycycline Monohydrate 50 MG Oral Tablet | 2 | 2 |
| `1723208` | 10 ML Alfentanil 0.5 MG/ML Injection | 2 | 2 |
| `1809104` | 5 ML SUFentanil 0.05 MG/ML Injection | 2 | 2 |
| `309045` | Cefaclor 250 MG Oral Capsule | 2 | 2 |
| `562366` | desflurane 1000 MG/ML Inhalation Solution | 2 | 2 |
| `608139` | atomoxetine 100 MG Oral Capsule | 2 | 2 |
| `865098` | Insulin Lispro 100 UNT/ML Injectable Solution [Humalog] | 1 | 73 |
| `1114085` | 100 ML zoledronic acid 0.04 MG/ML Injection | 1 | 8 |
| `1014676` | cetirizine hydrochloride 5 MG Oral Tablet | 1 | 1 |
| `1373463` | canagliflozin 100 MG Oral Tablet | 1 | 1 |
| `1665227` | 20 ML Ciprofloxacin 10 MG/ML Injection | 1 | 1 |
| `1735006` | 10 ML Fentanyl 0.05 MG/ML Injection | 1 | 1 |
| `1940648` | neratinib 40 MG Oral Tablet | 1 | 1 |
| `198767` | Pancreatin 600 MG Oral Tablet | 1 | 1 |
| `205532` | Pulmozyme (Dornase Alfa) | 1 | 1 |
| `309845` | Diazepam 5 MG/ML Injectable Solution | 1 | 1 |

---

## `observations.csv`

- Rows: **1480409**
- Distinct patients: **3539** (100.0% of the 3539-patient roster)

### Columns

| column | type | % null | distinct values |
| --- | --- | ---: | ---: |
| `DATE` | text | 0.0 | 123879 |
| `PATIENT` | text | 0.0 | 3539 |
| `ENCOUNTER` | text | 4.7 | 100812 |
| `CODE` | text | 0.0 | 155 |
| `DESCRIPTION` | text | 0.0 | 167 |
| `VALUE` | text | 0.0 | 9097 |
| `UNITS` | text | 3.5 | 39 |
| `TYPE` | text | 0.0 | 2 |

### Most frequent CODE / DESCRIPTION pairs

Top 40 of **176** distinct pairs, ranked by distinct patients.

| CODE | DESCRIPTION | patients | rows |
| --- | --- | ---: | ---: |
| `72514-3` | Pain severity - 0-10 verbal numeric rating [Score] - Reported | 3439 | 73397 |
| `8462-4` | Diastolic Blood Pressure | 3420 | 54439 |
| `8480-6` | Systolic Blood Pressure | 3420 | 54439 |
| `29463-7` | Body Weight | 3420 | 48226 |
| `72166-2` | Tobacco smoking status NHIS | 3420 | 46425 |
| `8302-2` | Body Height | 3420 | 46425 |
| `8867-4` | Heart rate | 3420 | 46425 |
| `9279-1` | Respiratory rate | 3420 | 46425 |
| `718-7` | Hemoglobin [Mass/volume] in Blood | 3420 | 11503 |
| `777-3` | Platelets [#/volume] in Blood by Automated count | 3420 | 11485 |
| `785-6` | MCH [Entitic mass] by Automated count | 3420 | 11485 |
| `786-4` | MCHC [Mass/volume] by Automated count | 3420 | 11485 |
| `787-2` | MCV [Entitic volume] by Automated count | 3420 | 11485 |
| `32207-3` | Platelet distribution width [Entitic volume] in Blood by Automated count | 3420 | 9684 |
| `32623-1` | Platelet mean volume [Entitic volume] in Blood by Automated count | 3420 | 9684 |
| `4544-3` | Hematocrit [Volume Fraction] of Blood by Automated count | 3419 | 11233 |
| `6690-2` | Leukocytes [#/volume] in Blood by Automated count | 3419 | 11233 |
| `789-8` | Erythrocytes [#/volume] in Blood by Automated count | 3419 | 11233 |
| `21000-5` | Erythrocyte distribution width [Entitic volume] by Automated count | 3419 | 9432 |
| `39156-5` | Body Mass Index | 3407 | 46076 |
| `18262-6` | Low Density Lipoprotein Cholesterol | 3064 | 34858 |
| `2085-9` | High Density Lipoprotein Cholesterol | 3064 | 34858 |
| `2093-3` | Total Cholesterol | 3064 | 34858 |
| `2571-8` | Triglycerides | 3064 | 34858 |
| `DALY` | DALY | 2369 | 23177 |
| `QALY` | QALY | 2369 | 23177 |
| `QOLS` | QOLS | 2369 | 23177 |
| `20565-8` | Carbon Dioxide | 2159 | 43577 |
| `2069-3` | Chloride | 2159 | 43577 |
| `2339-0` | Glucose | 2159 | 43577 |
| `2947-0` | Sodium | 2159 | 43577 |
| `38483-4` | Creatinine | 2159 | 43577 |
| `49765-1` | Calcium | 2159 | 43577 |
| `6298-4` | Potassium | 2159 | 43577 |
| `6299-2` | Urea Nitrogen | 2159 | 43577 |
| `8310-5` | Body temperature | 1828 | 2582 |
| `4548-4` | Hemoglobin A1c/Hemoglobin.total in Blood | 1786 | 31234 |
| `69453-9` | Cause of Death [US Standard Certificate of Death] | 1539 | 1539 |
| `33914-3` | Glomerular filtration rate/1.73 sq M.predicted | 1299 | 14640 |
| `1742-6` | Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma | 1276 | 14574 |

### Complete code inventory — remaining 136 pairs

Same ranking continued, so the full set of codes present in this file is listed.

| CODE | DESCRIPTION | patients | rows |
| --- | --- | ---: | ---: |
| `1751-7` | Albumin [Mass/volume] in Serum or Plasma | 1276 | 14574 |
| `1920-8` | Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma | 1276 | 14574 |
| `1975-2` | Bilirubin.total [Mass/volume] in Serum or Plasma | 1276 | 14574 |
| `2885-2` | Protein [Mass/volume] in Serum or Plasma | 1276 | 14574 |
| `6768-6` | Alkaline phosphatase [Enzymatic activity/volume] in Serum or Plasma | 1276 | 14574 |
| `10834-0` | Globulin [Mass/volume] in Serum by calculation | 1065 | 12773 |
| `38265-5` | DXA [T-score] Bone density | 672 | 760 |
| `72106-8` | Total score [MMSE] | 474 | 1617 |
| `29303009` | Electrocardiographic procedure | 406 | 2144 |
| `14959-1` | Microalbumin Creatinine Ratio | 372 | 17164 |
| `33914-3` | Estimated Glomerular Filtration Rate | 372 | 17164 |
| `33756-8` | Polyp size greatest dimension by CAP cancer protocols | 369 | 377 |
| `57905-2` | Hemoglobin.gastrointestinal [Presence] in Stool by Immunologic method | 369 | 377 |
| `17861-6` | Calcium [Mass/volume] in Serum or Plasma | 332 | 1801 |
| `19123-9` | Magnesium [Mass/volume] in Serum or Plasma | 332 | 1801 |
| `2028-9` | Carbon dioxide  total [Moles/volume] in Serum or Plasma | 332 | 1801 |
| `2075-0` | Chloride [Moles/volume] in Serum or Plasma | 332 | 1801 |
| `2160-0` | Creatinine [Mass/volume] in Serum or Plasma | 332 | 1801 |
| `2276-4` | Ferritin [Mass/volume] in Serum or Plasma | 332 | 1801 |
| `2345-7` | Glucose [Mass/volume] in Serum or Plasma | 332 | 1801 |
| `2498-4` | Iron [Mass/volume] in Serum or Plasma | 332 | 1801 |
| `2500-7` | Iron binding capacity [Mass/volume] in Serum or Plasma | 332 | 1801 |
| `2502-3` | Iron saturation [Mass Fraction] in Serum or Plasma | 332 | 1801 |
| `2823-3` | Potassium [Moles/volume] in Serum or Plasma | 332 | 1801 |
| `2951-2` | Sodium [Moles/volume] in Serum or Plasma | 332 | 1801 |
| `3094-0` | Urea nitrogen [Mass/volume] in Serum or Plasma | 332 | 1801 |
| `33762-6` | NT-proBNP | 332 | 1801 |
| `788-0` | Erythrocyte distribution width [Ratio] by Automated count | 332 | 1801 |
| `89579-7` | Troponin I.cardiac [Mass/volume] in Serum or Plasma by High sensitivity method | 332 | 1801 |
| `10230-1` | Left ventricular Ejection fraction | 331 | 1652 |
| `75325-1` | Symptom | 323 | 1938 |
| `88020-3` | Functional capacity NYHA | 323 | 323 |
| `88021-1` | Objective assessment of cardiovascular disease NYHA | 323 | 323 |
| `59576-9` | Body mass index (BMI) [Percentile] Per age and gender | 319 | 2068 |
| `2708-6` | Oxygen saturation in Arterial blood | 319 | 1485 |
| `2857-1` | Prostate specific Ag [Mass/volume] in Serum or Plasma | 277 | 1493 |
| `32465-7` | Physical findings of Prostate | 277 | 1493 |
| `20454-5` | Protein [Presence] in Urine by Test strip | 260 | 4733 |
| `20505-4` | Bilirubin.total [Mass/volume] in Urine by Test strip | 260 | 4733 |
| `2514-8` | Ketones [Presence] in Urine by Test strip | 260 | 4733 |
| `25428-4` | Glucose [Presence] in Urine by Test strip | 260 | 4733 |
| `32167-9` | Clarity of Urine | 260 | 4733 |
| `5767-9` | Appearance of Urine | 260 | 4733 |
| `5767-9` | Odor of Urine | 260 | 4733 |
| `5770-3` | Bilirubin.total [Presence] in Urine by Test strip | 260 | 4733 |
| `5778-6` | Color of Urine | 260 | 4733 |
| `5792-7` | Glucose [Mass/volume] in Urine by Test strip | 260 | 4733 |
| `5794-3` | Hemoglobin [Presence] in Urine by Test strip | 260 | 4733 |
| `5797-6` | Ketones [Mass/volume] in Urine by Test strip | 260 | 4733 |
| `5799-2` | Leukocyte esterase [Presence] in Urine by Test strip | 260 | 4733 |
| `5802-4` | Nitrite [Presence] in Urine by Test strip | 260 | 4733 |
| `5803-2` | pH of Urine by Test strip | 260 | 4733 |
| `5804-0` | Protein [Mass/volume] in Urine by Test strip | 260 | 4733 |
| `5811-5` | Specific gravity of Urine by Test strip | 260 | 4733 |
| `20570-8` | Hematocrit [Volume Fraction] of Blood | 252 | 270 |
| `21000-5` | RDW - Erythrocyte distribution width Auto (RBC) [Entitic vol] | 252 | 252 |
| `6690-2` | WBC Auto (Bld) [#/Vol] | 252 | 252 |
| `789-8` | RBC Auto (Bld) [#/Vol] | 252 | 252 |
| `46288-7` | US Guidance for biopsy of Prostate | 235 | 316 |
| `19926-5` | FEV1/FVC | 182 | 2004 |
| `6075-6` | Cladosporium herbarum IgE Ab in Serum | 60 | 92 |
| `6082-2` | Codfish IgE Ab in Serum | 60 | 92 |
| `6085-5` | Common Ragweed IgE Ab in Serum | 60 | 92 |
| `6095-4` | American house dust mite IgE Ab in Serum | 60 | 92 |
| `6106-9` | Egg white IgE Ab in Serum | 60 | 92 |
| `6158-0` | Latex IgE Ab in Serum | 60 | 92 |
| `6189-5` | White oak IgE Ab in Serum | 60 | 92 |
| `6206-7` | Peanut IgE Ab in Serum | 60 | 92 |
| `6246-3` | Shrimp IgE Ab in Serum | 60 | 92 |
| `6248-9` | Soybean IgE Ab in Serum | 60 | 92 |
| `6273-7` | Walnut IgE Ab in Serum | 60 | 92 |
| `6276-0` | Wheat IgE Ab in Serum | 60 | 92 |
| `6833-8` | Cat dander IgE Ab in Serum | 60 | 92 |
| `6844-5` | Honey bee IgE Ab in Serum | 60 | 92 |
| `7258-7` | Cow milk IgE Ab in Serum | 60 | 92 |
| `28245-9` | Abuse Status [OMAHA] | 57 | 204 |
| `46240-8` | History of Hospitalizations+Outpatient visits | 57 | 204 |
| `55277-8` | HIV status | 57 | 204 |
| `63513-6` | Are you covered by health insurance or some other kind of health care plan [PhenX] | 57 | 204 |
| `71802-3` | Housing status | 57 | 204 |
| `76690-7` | Sexual orientation | 57 | 204 |
| `88040-1` | Response to cancer treatment | 54 | 193 |
| `77606-2` | Weight-for-length Per age and sex | 50 | 476 |
| `9843-4` | Head Occipital-frontal circumference | 50 | 476 |
| `21908-9` | Stage group.clinical Cancer | 46 | 86 |
| `21905-5` | Primary tumor.clinical [Class] Cancer | 46 | 46 |
| `21906-3` | Regional lymph nodes.clinical [Class] Cancer | 46 | 46 |
| `21907-1` | Distant metastases.clinical [Class] Cancer | 46 | 46 |
| `33728-7` | Size.maximum dimension in Tumor | 46 | 46 |
| `85318-4` | HER2 [Presence] in Breast cancer specimen by FISH | 46 | 46 |
| `85319-2` | HER2 [Presence] in Breast cancer specimen by Immune stain | 46 | 46 |
| `85337-4` | Estrogen receptor Ag [Presence] in Breast cancer specimen by Immune stain | 46 | 46 |
| `85339-0` | Progesterone receptor Ag [Presence] in Breast cancer specimen by Immune stain | 46 | 46 |
| `59557-9` | Treatment status Cancer | 42 | 42 |
| `44667-4` | Site of distant metastasis in Breast tumor | 40 | 40 |
| `74006-8` | Weight difference [Mass difference] --pre dialysis - post dialysis | 23 | 22504 |
| `10480-2` | Estrogen+Progesterone receptor Ag [Presence] in Tissue by Immune stain | 21 | 21 |
| `85352-3` | Lymph nodes with isolated tumor cells [#] in Cancer specimen by Light microscopy | 20 | 20 |
| `85343-2` | Lymph nodes with macrometastases [#] in Cancer specimen by Light microscopy | 15 | 15 |
| `85344-0` | Lymph nodes with micrometastases [#] in Cancer specimen by Light microscopy | 11 | 11 |
| `10834-0` | Globulin | 10 | 10 |
| `1742-6` | ALT (Elevated) | 10 | 10 |
| `1751-7` | Albumin | 10 | 10 |
| `17861-6` | Calcium | 10 | 10 |
| `1920-8` | AST (Elevated) | 10 | 10 |
| `2028-9` | Carbon Dioxide | 10 | 10 |
| `20570-8` | Hematocrit | 10 | 10 |
| `2075-0` | Chloride | 10 | 10 |
| `2160-0` | Creatinine | 10 | 10 |
| `2345-7` | Glucose | 10 | 10 |
| `26453-1` | Red Blood Cell | 10 | 10 |
| `26464-8` | White Blood Cell (Elevated) | 10 | 10 |
| `26515-7` | Platelet Count | 10 | 10 |
| `2823-3` | Potassium | 10 | 10 |
| `2885-2` | Protein | 10 | 10 |
| `2951-2` | Sodium | 10 | 10 |
| `30385-9` | RBC Distribution Width | 10 | 10 |
| `30428-7` | MCV | 10 | 10 |
| `3094-0` | Urea Nitrogen | 10 | 10 |
| `33037-3` | Anion Gap | 10 | 10 |
| `42719-5` | Total Bilirubin (Elevated) | 10 | 10 |
| `6768-6` | Alkaline Phosphatase | 10 | 10 |
| `718-7` | Hemoglobin | 10 | 10 |
| `80271-0` | Physical findings of Abdomen by Palpation | 10 | 10 |
| `3016-3` | Thyrotropin [Units/volume] in Serum or Plasma | 9 | 9 |
| `3024-7` | Thyroxine (T4) free [Mass/volume] in Serum or Plasma | 9 | 9 |
| `21924-6` | Tumor marker Cancer | 5 | 5 |
| `417181009` | Estrogen+Progesterone receptor Ag [Presence] in Tissue by Immune stain | 5 | 5 |
| `75443-2` | Mental health Outpatient Note | 2 | 133 |
| `84215-3` | Mental health Telehealth Note | 2 | 133 |
| `71970-8` | PROMIS-10 Global Mental Health (GMH) score | 1 | 2 |
| `71972-4` | PROMIS-10 Global Physical Health (GPH) score | 1 | 2 |
| `66519-0` | Percentage area affected by eczema Head and Neck | 1 | 1 |
| `66524-0` | Percentage area affected by eczema Upper extremitiy - bilateral | 1 | 1 |
| `66529-9` | Percentage area affected by eczema Trunk | 1 | 1 |
| `66534-9` | Percentage area affected by eczema Lower extremitiy - bilateral | 1 | 1 |

### Low-cardinality columns

Every non-identifier column with 25 or fewer distinct values, enumerated with row counts.

**`TYPE`** — 2 distinct

| value | rows |
| --- | ---: |
| numeric | 1372101 |
| text | 108308 |

### Numeric `VALUE` spread by `UNITS`

| UNITS | n | min | median | max |
| --- | ---: | ---: | ---: | ---: |
| mg/dL | 356301 | 0.00 | 56.00 | 563.50 |
| mmol/L | 181562 | 2.70 | 29.00 | 144.00 |
| mm[Hg] | 108878 | 31.00 | 96.00 | 185.00 |
| {score} | 98191 | 0.00 | 2.00 | 25.00 |
| /min | 92850 | 12.00 | 38.00 | 100.00 |
| kg | 70730 | 1.00 | 75.70 | 175.80 |
| % | 54048 | 0.00 | 6.20 | 100.00 |
| g/dL | 52176 | 2.40 | 16.60 | 80.00 |
| cm | 46947 | 0.30 | 170.60 | 198.70 |
| a | 46354 | 0.00 | 17.60 | 107.90 |
| kg/m2 | 46076 | 9.00 | 28.00 | 51.70 |
| U/L | 43722 | 0.00 | 36.90 | 140.00 |
| fL | 40547 | 9.40 | 81.00 | 519.90 |
| 10*3/uL | 22970 | 0.50 | 80.40 | 450.00 |
| mL/min/{1.73_m2} | 17164 | 1.00 | 25.30 | 161.00 |
| mg/g | 17164 | 0.00 | 104.05 | 599.80 |
| mL/min | 14640 | 4.00 | 71.00 | 160.50 |
| g/L | 12773 | 2.00 | 2.70 | 3.50 |
| 10*6/uL | 11495 | 3.80 | 4.70 | 5.80 |
| pg | 11485 | 26.60 | 29.90 | 33.00 |
| {nominal} | 4999 | 1.00 | 1.00 | 1.00 |
| pH | 4733 | 5.00 | 6.00 | 7.00 |
| ug/dL | 3602 | 35.00 | 207.45 | 449.90 |
| pg/mL | 3602 | 0.00 | 101.05 | 1999.80 |
| Cel | 2582 | 37.00 | 37.50 | 39.40 |

---

## `encounters.csv`

- Rows: **285339**
- Distinct patients: **3539** (100.0% of the 3539-patient roster)

### Columns

| column | type | % null | distinct values |
| --- | --- | ---: | ---: |
| `Id` | text | 0.0 | 285339 |
| `START` | text | 0.0 | 262865 |
| `STOP` | text | 0.0 | 265725 |
| `PATIENT` | text | 0.0 | 3539 |
| `ORGANIZATION` | text | 0.0 | 2352 |
| `PROVIDER` | text | 0.0 | 2354 |
| `PAYER` | text | 0.0 | 10 |
| `ENCOUNTERCLASS` | text | 0.0 | 6 |
| `CODE` | numeric (as text) | 0.0 | 47 |
| `DESCRIPTION` | text | 0.0 | 55 |
| `BASE_ENCOUNTER_COST` | numeric (as text) | 0.0 | 2 |
| `TOTAL_CLAIM_COST` | numeric (as text) | 0.0 | 2 |
| `PAYER_COVERAGE` | numeric (as text) | 0.0 | 15 |
| `REASONCODE` | numeric (as text) | 74.9 | 98 |
| `REASONDESCRIPTION` | text | 74.9 | 99 |

### Most frequent CODE / DESCRIPTION pairs

Top 40 of **55** distinct pairs, ranked by distinct patients.

| CODE | DESCRIPTION | patients | rows |
| --- | --- | ---: | ---: |
| `162673000` | General examination of patient (procedure) | 3410 | 82538 |
| `185345009` | Encounter for symptom | 3409 | 13317 |
| `185349003` | Encounter for check up (procedure) | 2303 | 41727 |
| `50849002` | Emergency room admission (procedure) | 2263 | 3672 |
| `185349003` | Encounter for 'check-up' | 2198 | 4640 |
| `185347001` | Encounter for problem | 2101 | 13896 |
| `308646001` | Death Certification | 1539 | 1539 |
| `702927004` | Urgent care clinic (procedure) | 1334 | 24461 |
| `424441002` | Prenatal initial visit | 1079 | 2149 |
| `390906007` | Follow-up encounter | 837 | 20645 |
| `230690007` | Stroke | 731 | 909 |
| `410620009` | Well child visit (procedure) | 680 | 3595 |
| `50849002` | Emergency Room Admission | 670 | 1270 |
| `424619006` | Prenatal visit | 610 | 5380 |
| `390906007` | Hypertension follow-up encounter | 579 | 880 |
| `698314001` | Consultation for treatment | 524 | 2085 |
| `183452005` | Encounter Inpatient | 493 | 1651 |
| `316744009` | Office Visit | 432 | 1189 |
| `308335008` | Patient encounter procedure | 395 | 2658 |
| `50849002` | Emergency Encounter | 394 | 5565 |
| `183460006` | Obstetric emergency hospital admission | 371 | 629 |
| `185347001` | Encounter for Problem | 366 | 730 |
| `169762003` | Postnatal visit | 355 | 618 |
| `305351004` | Admission to intensive care unit (procedure) | 319 | 672 |
| `185347001` | Encounter for problem (procedure) | 253 | 31456 |
| `22298006` | Myocardial Infarction | 209 | 226 |
| `410429000` | Cardiac Arrest | 192 | 197 |
| `32485007` | Hospital admission | 190 | 264 |
| `56876005` | Drug rehabilitation and detoxification | 181 | 430 |
| `371883000` | Outpatient procedure | 150 | 2993 |
| `270427003` | Patient-initiated encounter | 141 | 186 |
| `439740005` | Postoperative follow-up visit (procedure) | 135 | 1494 |
| `183495009` | Non-urgent orthopedic admission | 128 | 130 |
| `410410006` | Screening surveillance (regime/therapy) | 126 | 1113 |
| `394701000` | Asthma follow-up | 106 | 668 |
| `448337001` | Telemedicine consultation with patient | 102 | 7801 |
| `185345009` | Encounter for symptom (procedure) | 87 | 87 |
| `86013001` | Periodic reevaluation and management of healthy individual (procedure) | 76 | 76 |
| `170837001` | Allergic disorder initial assessment | 73 | 73 |
| `310061009` | Gynecology service (qualifier value) | 72 | 623 |

### Complete code inventory — remaining 15 pairs

Same ranking continued, so the full set of codes present in this file is listed.

| CODE | DESCRIPTION | patients | rows |
| --- | --- | ---: | ---: |
| `79094001` | Initial Psychiatric Interview with mental status evaluation | 66 | 66 |
| `183478001` | Emergency hospital admission for asthma | 65 | 112 |
| `210098006` | Domiciliary or rest home patient evaluation and management | 64 | 212 |
| `305408004` | Admission to surgical department | 57 | 61 |
| `170838006` | Allergic disorder follow-up assessment | 57 | 57 |
| `223484005` | Discussion about treatment (procedure) | 44 | 44 |
| `185389009` | Follow-up visit (procedure) | 32 | 293 |
| `47505003` | posttraumatic stress disorder | 25 | 42 |
| `305411003` | Admission to thoracic surgery department | 17 | 17 |
| `387713003` | Surgical procedure (procedure) | 12 | 12 |
| `185317003` | Telephone encounter (procedure) | 5 | 142 |
| `183801001` | Inpatient stay 3 days | 2 | 2 |
| `185349003` | Encounter for check up | 1 | 45 |
| `305336008` | Admission to hospice (procedure) | 1 | 1 |
| `67799006` | Diagnosis of cystic fibrosis using sweat test and gene test | 1 | 1 |

### Low-cardinality columns

Every non-identifier column with 25 or fewer distinct values, enumerated with row counts.

**`ENCOUNTERCLASS`** — 6 distinct

| value | rows |
| --- | ---: |
| ambulatory | 94840 |
| wellness | 87672 |
| outpatient | 52362 |
| urgentcare | 24461 |
| emergency | 13348 |
| inpatient | 12656 |

**`BASE_ENCOUNTER_COST`** — 2 distinct

| value | rows |
| --- | ---: |
| 129.16 | 154455 |
| 77.49 | 130884 |

**`TOTAL_CLAIM_COST`** — 2 distinct

| value | rows |
| --- | ---: |
| 129.16 | 154455 |
| 77.49 | 130884 |

**`PAYER_COVERAGE`** — 15 distinct

| value | rows |
| --- | ---: |
| 37.49 | 71516 |
| 0.00 | 52987 |
| 89.16 | 48091 |
| 129.16 | 23002 |
| 69.16 | 21272 |
| 54.16 | 9751 |
| 17.49 | 9363 |
| 59.16 | 8851 |
| 49.16 | 8412 |
| 64.16 | 7790 |
| 74.16 | 6713 |
| 2.49 | 6075 |
| 29.16 | 4818 |
| 7.49 | 3701 |
| 12.49 | 2997 |

---

## `careplans.csv`

- Rows: **14115**
- Distinct patients: **3420** (96.6% of the 3539-patient roster)

### Columns

| column | type | % null | distinct values |
| --- | --- | ---: | ---: |
| `Id` | text | 0.0 | 14115 |
| `START` | text | 0.0 | 10481 |
| `STOP` | text | 52.3 | 5266 |
| `PATIENT` | text | 0.0 | 3420 |
| `ENCOUNTER` | text | 0.0 | 14044 |
| `CODE` | numeric (as text) | 0.0 | 35 |
| `DESCRIPTION` | text | 0.0 | 36 |
| `REASONCODE` | numeric (as text) | 5.1 | 69 |
| `REASONDESCRIPTION` | text | 5.1 | 69 |

### Most frequent CODE / DESCRIPTION pairs

Top 37 of **37** distinct pairs, ranked by distinct patients.

| CODE | DESCRIPTION | patients | rows |
| --- | --- | ---: | ---: |
| `698360004` | Diabetes self management plan | 1667 | 1667 |
| `53950000` | Respiratory therapy | 1531 | 2235 |
| `443402002` | Lifestyle education regarding hypertension | 1126 | 1126 |
| `736285004` | Hyperlipidemia clinical management plan | 829 | 829 |
| `385691007` | Fracture care | 815 | 985 |
| `408869004` | Musculoskeletal care | 785 | 933 |
| `91251008` | Physical therapy procedure | 603 | 661 |
| `386257007` | Demential management | 507 | 507 |
| `225358003` | Wound care | 506 | 544 |
| `384758001` | Self-care interventions (procedure) | 453 | 453 |
| `736252007` | Cancer care plan | 378 | 378 |
| `134435003` | Routine antenatal care | 353 | 840 |
| `735984001` | Heart failure self management plan | 331 | 331 |
| `736353004` | Inpatient care plan (record artifact) | 319 | 672 |
| `734163000` | Care Plan | 264 | 264 |
| `47387005` | Head injury rehabilitation | 240 | 251 |
| `412776001` | Chronic obstructive pulmonary disease clinical management plan | 182 | 182 |
| `734163000` | Care plan (record artifact) | 176 | 176 |
| `182964004` | Terminal care | 146 | 146 |
| `395082007` | Cancer care plan | 146 | 146 |
| `133901003` | Burn care | 145 | 149 |
| `781831000000109` | Major surgery care management | 113 | 113 |
| `699728000` | Asthma self management | 108 | 108 |
| `736254008` | Psychiatry care plan | 87 | 87 |
| `869761000000107` | Urinary tract infection care | 82 | 104 |
| `170836005` | Allergic disorder monitoring | 59 | 59 |
| `737471002` | Minor surgery care management (procedure) | 42 | 42 |
| `711282006` | Skin condition care | 34 | 34 |
| `736690008` | Dialysis care plan (record artifact) | 23 | 23 |
| `718347000` | Mental health care plan | 22 | 22 |
| `386522008` | Overactivity/inattention behavior management | 14 | 14 |
| `133899007` | Postoperative care | 10 | 10 |
| `737434004` | Major depressive disorder clinical management plan | 9 | 9 |
| `75162002` | Spinal cord injury rehabilitation | 7 | 7 |
| `183401008` | Anti-suicide psychotherapy | 4 | 4 |
| `718347000` | Mental health care plan (record artifact) | 3 | 3 |
| `703040004` | Agreeing on diabetes care plan | 1 | 1 |

---

## `supplies.csv`

**This file contains 0 data rows (header only).**

- Rows: **0**
- Distinct patients: **0** (0.0% of the 3539-patient roster)

### Columns

| column | type | % null | distinct values |
| --- | --- | ---: | ---: |
| `DATE` | empty | 0.0 | 0 |
| `PATIENT` | empty | 0.0 | 0 |
| `ENCOUNTER` | empty | 0.0 | 0 |
| `CODE` | empty | 0.0 | 0 |
| `DESCRIPTION` | empty | 0.0 | 0 |
| `QUANTITY` | empty | 0.0 | 0 |
