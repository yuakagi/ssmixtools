"""
Configuration file for data extraction, cleaning, and processing.
Contains constants, regular expressions, and mappings for various data workflows.
"""

# Extraction targets (for path collection)
TARGET_DATA_TYPES = [
    "ADT-00",
    "ADT-12",
    "ADT-22",
    "ADT-52",
    "PPR-01",
    "OMP-01",
    "OMP-02",
    "OML-11",
    "OML-12",
]

# Multiprocessing related configs
LOGICAL_CPU = False
CPU_MARGIN = 1

# Single file config
# If false, tables are saved as separate csv files in chunks
SINGLE_FILE = {
    "demographics": True,
    "ADT-12": False,
    "ADT-22": True,
    "ADT-52": True,
    "PPR-01": True,
    "OMP-01": False,
    "OMP-02": False,
    "OML-11": False,
}
# Chunk sizes. Define chunksizes of each step here.
CHUNKSIZES = {
    # Extraction steps
    "all_patient_ID_extraction": 20,  # /directories
    "patient_metadata_extraction": 1000,  # /patients
    "patient_selection": 10000,  # /patients
    "file_path_segregation": 5000,  # /patients
}

# Directories
DEBUG_DIR = "debug_files/"

# File paths or path patterns (use '*' as a wildcard)
TIME_SERIES_DATA_PATTERN = "time_series_*.csv"
DATA_TYPE_PATH_PATTERN = "data_type_paths_*.csv"
DOB_MAP_PATTERN = "DOB_*.csv"
METADATA_TABLE_PATTERN = "patient_metadata_*.csv"
DEMOGRAPHIC_TABLE_PATTERN = "demographics_*.csv"
OUTPATIENT_VISIT_TABLE_PATTERN = "outpatient_visits_*.csv"
ADMISSION_TABLE_PATTERN = "admission_records_*.csv"
DISCHARGE_TABLE_PATTERN = "discharge_records_*.csv"
DIAGNOSIS_TABLE_PATTERN = "diagnosis_records_*.csv"
PRESCRIPTION_ORDER_TABLE_PATTERN = "prescription_order_records_*.csv"
INJECTION_ORDER_TABLE_PATTERN = "injection_order_records_*.csv"
LAB_RESULT_TABLE_PATTERN = "laboratory_test_results_*.csv"
ALL_CLEANED_TABLE_PATTERNS = [
    DEMOGRAPHIC_TABLE_PATTERN,
    OUTPATIENT_VISIT_TABLE_PATTERN,
    ADMISSION_TABLE_PATTERN,
    DISCHARGE_TABLE_PATTERN,
    DIAGNOSIS_TABLE_PATTERN,
    PRESCRIPTION_ORDER_TABLE_PATTERN,
    INJECTION_ORDER_TABLE_PATTERN,
    LAB_RESULT_TABLE_PATTERN,
]

# Common column names
# NOTE: Use snake case without upper case letters.
COL_ORIGINAL = "original"
COL_TARGET = "target"
COL_RECORD_ID = "unique_record_id"
COL_PID = "patient_id"
COL_DID = "deidentified_patient_id"
COL_SEX = "sex"
COL_DOB = "date_of_birth"
COL_N_ENCOUNTERS = "number_of_date_folders"
COL_FIRST_VISIT_DATE = "first_visit_date"
COL_LAST_VISIT_DATE = "last_visit_date"
COL_N_ADMISSIONS = "number_of_recorded_admissions"
COL_ITEM_CODE = "item_code"
COL_ITEM_NAME = "item_name"
COL_ITEM_NAME_LC = "local_item_name"
COL_NUMERIC = "numeric"
COL_NONNUMERIC = "nonnumeric"
# NOTE: Standardized code names such as ICD10 are all lowercased for column names
COL_ATC = "atc"
COL_ICD10 = "icd10"
COL_JLAC10 = "jlac10"

# Crawling config
DEFAULT_DELAY = 10
RESTART_LIMITS = 10

# Strings recognized as missing values (passed to pd.read_csv as 'na_values' )
# NOTE : Because a dash '-' sometimes indicates 'negative' in medical records,
#        adding a dash to the list below may result in unintended record deletion.
NA_VALUES = ["", "NA", "N/A", "na", "nan", "NaN", "NaT", "None", "none"]

# Lab cleaning
LAB_REMOVED_MARKS = ["?"]
LAB_NOT_A_RECORD = "nar"
LAB_COMMENT_SUFFIXES = ("TCM", "TIM", "MED")
POS_NEG_EXPRESSIONS = {
    "(+)": ["+", "positive", "pos", "+ve", "ヨウセイ", "陽性"],
    "(-)": ["-", "negative", "neg", "-ve", "インセイ", "陰性"],
    "(+-)": ["+-", "-+", "(-+)"],
}
UNIT_NORMALIZE_DICT = {
    # Liter unit normalization
    r"^l$|^L$": "L",
    r"/l$|/L$": "/L",
    r"^l/|^L/": "L/",
    r"^ml$": "mL",
    r"/ml$": "/mL",
    r"^ml/": "mL/",
    r"^(μ|u)l$": "μL",
    r"/(μ|u)l$": "/μL",
    r"^(μ|u)l/": "μL/",
    r"/(f|d|n)l$": r"/\1L",
    r"^(f|d|n)l/": r"\1L/",
    r"^(f|d|n)l$": r"\1L",
    # Gram unit normalization
    r"^G$": "g",
    r"/G$": "/g",
    r"^G/": "g/",
    r"^mG$": "mg",
    r"/mG$": "/mg",
    r"^mG/": "mg/",
    r"^(μ|u)G$": "μg",
    r"/(μ|u)G$": "/μg",
    r"^(μ|u)G/": "μg/",
    r"^ug$": "μg",
    r"/ug$": "/μg",
    r"^ug/": "μg/",
    r"^nG$": "ng",
    r"/nG$": "/ng",
    r"^nG/": "ng/",
    # Remove '個'
    r"(個)": "",
    # Power of 10 normalization: 10**2 -> 10^2
    r"^10\*\*": "10^",
    r"/10\*\*": "/10^",
}


# Regular expressions or string patterns, allowing hours from 24 to 47 (i.e, string timestamp patterns such as '202306132430' match).
R_TIME_DEFAULT = r"^\s*(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])(([01][0-9]|2[0-9]|3[0-9]|4[0-7])(([0-5][0-9])([0-5][0-9])?)?)?\s*$"  # YYYYMMDD[HH[MM[SS]]], allowing hours from 24 to 47.
R_YYYYMMDD = r"^\s*(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])\s*$"  # YYYYMMDD
R_YYYYMMDDHHMM = r"^\s*(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])([01][0-9]|2[0-9]|3[0-9]|4[0-7])([0-5][0-9])\s*$"  # YYYYMMDDHHMM
R_YYYYMMDD0000 = (
    r"^\s*(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])0{4}\s*$"  # YYYYMMDD0000
)
R_YYYYMMDDHHMMSS = r"^\s*(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])([01][0-9]|2[0-9]|3[0-9]|4[0-7])([0-5][0-9])([0-5][0-9])\s*$"  # YYYYMMDDHHMMSS
R_YYYYMMDD000000 = (
    r"^\s*(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])0{6}\s*$"  # YYYYMMDD000000
)
R_YYYYMMDDHHMMSSFFF = r"^\s*(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])([01][0-9]|2[0-9]|3[0-9]|4[0-7])([0-5][0-9])([0-5][0-9])(\d{1,3})\s*$"  # YYYYMMDDHHMMSSFFF
R_YYYYMMDD000000000 = r"^\s*(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])0{7,9}\s*$"  # YYYYMMDD000000000
R_YYYYMMDDHHMMSSFFF_DOT = r"^\s*(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])([01][0-9]|2[0-9]|3[0-9]|4[0-7])([0-5][0-9])([0-5][0-9])(\.\d{1,3})\s*$"  # YYYYMMDDHHMMSS.FFF
R_YYYYMMDD000000000_DOT = r"^\s*(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])0{6}\.0{1,3}\s*$"  # YYYYMMDD000000.000
R_ALL_TIME_PATTERNS = r"^\s*(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])(([01][0-9]|2[0-9]|3[0-9]|4[0-7])([0-5][0-9])(([0-5][0-9])\.?(\d{3})?)?)?\s*$"  # Match all above patterns
R_ZEROS_BELOW_DATE = r"^\s*(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])(0{4}|0{6}\.?0{0,3})\s*$"  # YYYYMMDD000000000
R_HOURS_24_TO_47 = r"^\s*(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])(2[4-9]|3[0-9]|4[0-7])([0-5][0-9])(([0-5][0-9])\.?(\d{3})?)?\s*$"
R_DASHES = r"－|-|‐|−|‒|—|–|―|ｰ|─|━|ㅡ|ـ|⁻|₋"  # Do NOT include 'ー' in this (The one seen in 'コード'.)

R_LOCAL_SYSTEM = r"^\s*99[A-Za-z0-9]*\s*$"
MDCDX2 = "MDCDX2"
R_MDCDX2 = r"^\s*MDCDX2\s*$"
R_MDCDX2_CODE = r"^\s*\d{8}\s*$"
ICD10 = "ICD10"
R_ICD10 = r"^\s*I10\s*$"
# ICD-10 rarely contain hyphen ('-'). Examples are T08-0, M45-0, etc.
# NOTE: '-' is a placeholder, which is not necessarily a common practice. Such use is observed in the ICD-10 map provided by MEDIS.
R_ICD10_CODE = r"^\s*([A-Za-z][0-9]{2}\.?|[A-Za-z][0-9]{2}\.?[0-9-]|[A-Za-z][0-9]{2}\.?[0-9-][0-9a-z])\s*$"
HOT = "HOT"
R_HOT = r"^\s*HOT(7|07|9|09|11|13)\s*$"
R_HOT_CODE = r"^\s*(\d{7}|\d{9}|\d{11}|\d{13})\s*$"
YJ = "YJ"
MYAK = "MYAK"
R_YJ_OR_MYAK = r"^\s*(YJ)|(MYAK)\s*$"
R_YJ_OR_MYAK_CODE = r"^\s*[A-Za-z0-9]{12}\s*$"
ATC = "ATC"
R_ATC_CODE = (
    r"^\s*([A-Z]\d{2}[A-Z]{1,2}|[A-Z]\d{2}[A-Z]{2}\d{2})\s*$"  # Matches ATC4,5,7
)
JHSI0002_INJECTION_TYPE = "99I02"
R_JHSI0002_INJECTION_TYPE = r"^\s*99I02\s*$"
R_JHSI0002_INJECTION_TYPE_CODE = r"^\s*0[0-9]\s*$"
JHSD0005_PROVISIONAL_FLAG = "JHSD0005"
R_JHSD0005_PROVISIONAL_FLAG = r"^\s*JHSD0005\s*$"
JHSD0004_DIAGNOSIS_TYPE = "JHSD0004"
R_JHSD0004_DIAGNOSIS_TYPE = r"^\s*JHSD0005\s*$"
JLAC10 = "JLAC10"
R_JLAC10 = r"^\s*JC10\s*$"
R_JLAC10_CODE = r"^\s*\d[A-Z][0-9-]{15}\s*$"  # NOTE: with '[0-9-]' this part, method-agnostic JLAC10 codes ('---' for methodology) match.
ISO_PLUS = r"ISO\+"
R_ISO_PLUS = r"\s*ISO\+\s*"
R_USER_DEFINED_TABLE_0112_CODE = (
    r"\s*(0[1-9])|([1-3][0-9])|(4[0-2])\s*"  # Discharge dispositions
)


# Drug product name cleaning
MIN_CROPPED_DRUG_NAME_LENGTH = 3
R_UNNECESSARY_CHARACTERS = r"(※|・|×|\*|＊|,|\"|＂|”|“||\'|＇|’|‘|′|-|−)"
R_BRACKETED = (
    r"\[.*?\]|\(.*?\)|\{.*?\}|<.*?>|（.*?）|【.*?】|〈.*?〉|〔.*?〕|「.*?」|『.*?』"
)
R_COMMON_UNITS = r"((\d+\.\d+|\d+)(\%|((m|μ|n|p)?g|(m|μ|)?(l|L)|(c|m)(m|M))|Eq|mEq|[一二三四五六七八九十百千万]*(((国際|国内)(標準)?)?単位|(I)?U)))|(/((\d+\.\d+|\d+))?((m|μ|n|p)?g|(m|μ|)?(l|L)|(c|m)(m|M)|包))|((\d+\.\d+|\d+))/((\d+\.\d+|\d+))"
R_UNNECESSARY_TAILS = r"(\d+\.\d*|\d+|([一二三四五六七八九十百千万]+))$"


# Categories
SEX_TYPES = {
    "M": "male",
    "F": "female",
    "O": "others",
    "U": "unknown",
}  # Defined in SS-MIX2 guideline
DIAGNOSIS_TYPES = {
    "H": "admission",
    "L": "discharge",
    "O": "outpatient",
    "B": "pre-operative",
    "A": "post-operative",
    "F": "final",
}  # Defined by JHSD0004

# Discharge status (by user defined table 0112)
# (1: survived, 0: died)
DISCHARGE_STATUS_MAP = {
    r"01|[3]{1}[0-9]{1}": 1,  # Alive
    r"0[2-9]{1}|[1]{1}[0-9]{1}": 1,  # Others (mostly transferred patients.)
    r"[24]{1}[0-9]{1}": 0,  # Expired
}

# Code params
CODE_PARAMS = {
    ICD10: {
        "min_length": 3,
        "max_length": 5,
        "code_regex": R_ICD10_CODE,
        "truncate_long_code": True,
    },
    ATC: {
        "min_length": 4,
        "max_length": 7,
        "code_regex": R_ATC_CODE,
        "truncate_long_code": False,
    },
    JLAC10: {
        "min_length": 17,
        "max_length": 17,
        "code_regex": R_JLAC10_CODE,
        "truncate_long_code": False,
    },
}

# Table params
META_TABLE_PARAMS = {
    "metadata": {
        "all": [
            COL_PID,
            COL_SEX,
            COL_DOB,
            COL_N_ENCOUNTERS,
            COL_FIRST_VISIT_DATE,
            COL_LAST_VISIT_DATE,
            COL_N_ADMISSIONS,
        ],
        "timestamps": [
            COL_DOB,
            COL_FIRST_VISIT_DATE,
            COL_LAST_VISIT_DATE,
        ],
    },
    "file paths": {
        "all": [COL_PID, "data_type", "condition_flag", "file_name"],
        "timestamps": [],
    },
}

RECORD_TABLE_PARAMS = {
    "demographics": {
        "file_name_pattern": DEMOGRAPHIC_TABLE_PATTERN,
        "code_type": None,
        "all": [
            COL_PID,
            COL_SEX,
            COL_N_ENCOUNTERS,
            COL_FIRST_VISIT_DATE,
            COL_LAST_VISIT_DATE,
            COL_N_ADMISSIONS,
        ],
        "timestamps": [
            COL_FIRST_VISIT_DATE,
            COL_LAST_VISIT_DATE,
        ],
        # 'dropna_*' values are cleaned at the final cleaning step (optional)
        "dropna_any": [COL_PID, COL_SEX],
        "dropna_all": None,
        "final_columns": [
            COL_PID,
            COL_SEX,
            COL_N_ENCOUNTERS,
            COL_FIRST_VISIT_DATE,
            COL_LAST_VISIT_DATE,
            COL_N_ADMISSIONS,
        ],
    },
    "ADT-12": {
        "file_name_pattern": OUTPATIENT_VISIT_TABLE_PATTERN,
        "code_type": None,
        "all": [COL_PID, "department", "visiting_date"],
        "timestamps": ["visiting_date"],
        "dropna_any": [COL_PID, "visiting_date"],
        "dropna_all": None,
        "final_columns": [
            COL_PID,
            "department",
            "visiting_date",
        ],
    },
    "ADT-22": {
        "file_name_pattern": ADMISSION_TABLE_PATTERN,
        "code_type": None,
        "all": [
            COL_PID,
            "department",
            "admission_date",
            "time_of_transaction",
            "time_of_message",
        ],
        "timestamps": ["admission_date", "time_of_transaction", "time_of_message"],
        "dropna_any": [COL_PID, "admission_date"],
        "dropna_all": None,
        "final_columns": [
            COL_PID,
            "department",
            "admission_date",
            "time_of_transaction",
            "time_of_message",
        ],
    },
    "ADT-52": {
        "file_name_pattern": DISCHARGE_TABLE_PATTERN,
        "code_type": None,
        "all": [
            COL_PID,
            "discharge_date",
            "time_of_transaction",
            "time_of_message",
            "disposition",
        ],
        "timestamps": ["discharge_date", "time_of_transaction", "time_of_message"],
        "dropna_any": [
            COL_PID,
            "discharge_date",
        ],
        "dropna_all": None,
        "final_columns": [
            COL_PID,
            "discharge_date",
            "time_of_transaction",
            "time_of_message",
            "disposition",
        ],
    },
    "PPR-01": {
        "file_name_pattern": DIAGNOSIS_TABLE_PATTERN,
        "code_type": ICD10,
        "all": [
            COL_PID,
            "primary_diagnosis_coding_system",
            "primary_diagnosis_code",
            "primary_diagnosis_text",
            "secondary_diagnosis_coding_system",
            "secondary_diagnosis_code",
            "diagnosis_type",
            "provisional",
            "time_of_update",
            "date_of_onset",
            "date_of_diagnosis",
        ],
        "timestamps": [
            "time_of_update",
            "date_of_onset",
            "date_of_diagnosis",
        ],
        "dropna_any": [
            COL_PID,
            COL_ITEM_CODE,
            "provisional",
            "time_of_update",
        ],
        "dropna_all": None,
        "final_columns": [
            COL_PID,
            COL_ITEM_CODE,
            COL_ITEM_NAME,
            "provisional",
            "diagnosis_type",
            "time_of_update",
            "date_of_onset",
            "date_of_diagnosis",
        ],
    },
    "OMP-01": {
        "file_name_pattern": PRESCRIPTION_ORDER_TABLE_PATTERN,
        "code_type": ATC,
        "all": [
            COL_PID,
            "primary_prescription_coding_system",
            "primary_prescription_code",
            "primary_prescription_text",
            "secondary_prescription_coding_system",
            "secondary_prescription_code",
            "secondary_prescription_text",
            "duration",
            "time_of_order",
            "start_of_order",
            "end_of_order",
        ],
        "timestamps": [
            "time_of_order",
            "start_of_order",
            "end_of_order",
        ],
        "dropna_any": [
            COL_PID,
            COL_ITEM_CODE,
            "time_of_order",
            "start_of_order",
        ],
        "dropna_all": None,
        "final_columns": [
            COL_PID,
            COL_ITEM_CODE,
            COL_ITEM_NAME,
            "duration",
            "time_of_order",
            "start_of_order",
            "end_of_order",
        ],
    },
    "OMP-02": {
        "file_name_pattern": INJECTION_ORDER_TABLE_PATTERN,
        "code_type": ATC,
        "all": [
            COL_PID,
            "injection_type_coding_system",
            "injection_type_code",
            "injection_type_text",
            "primary_component_coding_system",
            "primary_component_code",
            "primary_component_text",
            "secondary_component_coding_system",
            "secondary_component_code",
            "secondary_component_text",
            "time_of_order",
            "start_of_order",
            "end_of_order",
        ],
        "timestamps": [
            "time_of_order",
            "start_of_order",
            "end_of_order",
        ],
        "dropna_any": [
            COL_PID,
            COL_ITEM_CODE,
            "start_of_order",
        ],
        "dropna_all": None,
        "final_columns": [
            COL_PID,
            COL_ITEM_CODE,
            COL_ITEM_NAME,
            "time_of_order",
            "start_of_order",
            "end_of_order",
        ],
    },
    "OML-11": {
        "file_name_pattern": LAB_RESULT_TABLE_PATTERN,
        "code_type": JLAC10,
        "all": [
            COL_PID,
            "lab_coding_system",
            "lab_code",
            "lab_text",
            "value",
            "unit_text",
            "unit_code",
            "unit_coding_system",
            "sampled_time",
            "tested_time",
            "reported_time",
        ],
        "timestamps": [
            "sampled_time",
            "tested_time",
            "reported_time",
        ],
        "dropna_any": [COL_PID, COL_ITEM_CODE, "sampled_time"],
        "dropna_all": [COL_NUMERIC, COL_NONNUMERIC],
        "final_columns": [
            COL_PID,
            COL_ITEM_CODE,
            COL_ITEM_NAME,
            COL_NUMERIC,
            COL_NONNUMERIC,
            "unit",
            "sampled_time",
            "tested_time",
            "reported_time",
        ],
    },
}


# Data types and their descriptions in SS-MIX2
DATA_TYPE_DICT = {
    "ADT-00": "Basic information(ADT-00)",
    "ADT-01": "Physicians(ADT-01)",
    "ADT-12": "Outpatient reception(ADT-12)",
    "ADT-21": "Admission schedule(ADT-21)",
    "ADT-22": "Admission confirmation(ADT-22)",
    "ADT-31": "Temporal leaves(ADT-31)",
    "ADT-32": "Back from leaves(ADT-32)",
    "ADT-41": "Change dpt./ward orders(ADT-41)",
    "ADT-42": "Change dpt./ward confirmation(ADT-42)",
    "ADT-51": "Discharge orders(ADT-51)",
    "ADT-52": "Discharge confirmation(ADT-52)",
    "ADT-61": "Allergy(ADT-61)",
    "PPR-01": "Diagnoses(PPR-01)",
    "OMD": "Meal orders(OMD)",
    "OMP-01": "Prescriptions(OMP-01)",
    "OMP-11": "Prescriptions performed(OMP-11)",
    "OMP-02": "IV orders(OMP-02)",
    "OMP-12": "IV performed(OMP-12)",
    "OML-01": "Lab test orders(OML-01)",
    "OML-11": "Lab results(OML-11)",
    "OML-02": "Microbiology orders(OML-02)",
    "OML-12": "Microbiology results(OML-12)",
    "OMG-01": "X-ray orders(OMG-01)",
    "OMG-11": "X-ray performed(OMG-11)",
    "OMG-02": "Endoscopy orders(OMG-02)",
    "OMG-12": "Endoscopy performed(OMG-12)",
    "OMG-03": "Physiological test orders(OMG-03)",
    "OMG-13": "Physiological tests performed(OMG-13)",
}
