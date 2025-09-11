Table definitions 
==================

.. contents:: Table of Contents
   :local:
   :depth: 2

Patient info
------------

patient_id_map.csv
^^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "patient_id", "str", "Original patient ID"
    "deidentified_patient_id", "str", "deidentified patient ID"

patient_dob_map.csv
^^^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "date_of_birth", "date", "Date of birth of the patient in YYYYMMDD format"



Cleaned tables
--------------

demographics_*.csv
^^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column","Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "sex", "str", "Patient's sex (gender)"
    "number_of_date_folders", "int", "Number of unique encounter dates"
    "first_visit_date", "datetime", "Date of the first recorded medical encounter"
    "last_visit_date", "datetime", "Date of the last recorded medical encounter"
    "number_of_recorded_admissions", "int", "Total number of recorded admissions"

outpatient_visits_*.csv
^^^^^^^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "department", "str", "Code representing the department the patient visited"
    "visiting_date", "datetime", "Date and time when the patient visited the department"
    "unique_record_id", "str", "Unique identifier for the outpatient visit record"


admission_records_*.csv
^^^^^^^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "department", "str", "Code representing the department where the patient was treated"
    "admission_date", "datetime", "Date and time of the patient's admission"
    "time_of_transaction", "datetime", "The timestamp of the most recent record transaction"
    "time_of_message", "datetime", "Precise time when the message was generated"
    "unique_record_id", "str", "Unique identifier for the record"

discharge_records_*.csv
^^^^^^^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "discharge_date", "datetime", "Date and time when the patient was discharged"
    "time_of_transaction", "datetime", "The timestamp of the most recent record transaction"
    "time_of_message", "datetime", "Timestamp when the discharge message was generated"
    "discharge_disposition", "int", "Code representing the patient's discharge disposition"
    "unique_record_id", "str", "Unique identifier for the discharge record"


diagnosis_records_*.csv
^^^^^^^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "item_code", "str", "Code representing the diagnosis"
    "item_name", "str", "Name of the diagnosis"
    "provisional", "int", "Indicates whether the diagnosis is provisional (1 for true, 0 for false)"
    "diagnosis_type", "str", "Type of the diagnosis (if available)"
    "time_of_update", "datetime", "Timestamp when the diagnosis record was last updated"
    "date_of_onset", "datetime", "Date when the condition or diagnosis started"
    "date_of_diagnosis", "datetime", "Date when the diagnosis was officially recorded"
    "unique_record_id", "str", "Unique identifier for the record"

prescription_order_records_*.csv
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "item_code", "str", "Code representing the prescribed medication"
    "item_name", "str", "Name of the prescribed medication"
    "duration", "str", "Duration for which the medication is prescribed"
    "time_of_order", "datetime", "Timestamp when the prescription was ordered"
    "start_of_order", "datetime", "Start date and time of the medication prescription"
    "end_of_order", "datetime", "End date and time of the medication prescription (if available)"
    "unique_record_id", "str", "Unique identifier for the prescription record"


injection_order_records_*.csv
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "item_code", "str", "Code representing the medication"
    "item_name", "str", "Name of the medication"
    "time_of_order", "datetime", "Timestamp when the medication order was placed"
    "start_of_order", "datetime", "Start time of the medication order"
    "end_of_order", "datetime", "End time of the medication order"
    "unique_record_id", "str", "Unique identifier for the medication order record"

laboratory_test_results_*.csv
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient, including a hospital tag"
    "item_code", "str", "Code representing the test"
    "item_name", "str", "Name of the test"
    "numeric", "float", "Numeric result of the test, if available"
    "nonnumeric", "str", "Non-numeric result of the test, if available"
    "unit", "str", "Unit of the numeric test result (e.g., 'mg/dL' or 'no_unit')"
    "sampled_time", "datetime", "Timestamp when the specimen was collected"
    "tested_time", "datetime", "Timestamp when the test was performed"
    "reported_time", "datetime", "Timestamp when the result was reported"
    "unique_record_id", "str", "Unique identifier for the record, including a hospital tag"

.. note::
    If JLAC10 is not available for item_code, the contents of item_code and item_name are determined using the following rules:

    - **item_code** 
        | The following items are concatenated with a "\|" symbol.  
        | Example: `001\|\|ER01\|0181300_011`.  
        - The specimen code (from OBR-4)  
        - The code for the specimen source (from SPM-8)  
        - The code for the laboratory test group (from OBR-4)  
        - The raw local laboratory test codes  

    - **item_name**  
        | The following items are concatenated with a "\|" symbol.  
        | Example: `"その他\|\|培養同定情報(抗酸菌検査)\|\|Mycobacterium kansasii\|同定菌量"`.  
        - The specimen name (from OBR-4)  
        - The name of the specimen source (from SPM-8)  
        - The name of the laboratory test group (from OBR-4)  
        - The result of the parent laboratory test (from OBR-26; e.g., the bacteria name for the following sensitivity test results)  
        - The result of the laboratory test item related to this lab test (e.g., the bacteria name for the following colony size result if the test result is part of a series)  
        - The raw local laboratory test name  


Maps that need to be prepared by users
--------------------------------------

.. note::
    - Please prepare the following tables by yourself, and place them in `reference_dir`. ssmixtools will automatically parse them.


info_atc.csv
^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "商品名", "str", "Name of the medication in Japanese"
    "HOT番号", "str", "The Japanese medication code (HOT code)"
    "YJコード", "str", "The Japanese medication code (YJ code)"
    "ATC5", "str", "The medication described in the 5-character ATC code"
    "ATC7", "str", "The medication described in the 7-character ATC code"

.. note::
    - This table is required for :meth:`ssmixtools.cleaning.mandatory.render_maps`.
    - Codes not listed in this table will not be automatically mapped to ATC.

ICD10_to_text.csv
^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "item_code", "str", "ICD-10 code representing the specific diagnosis"
    "item_name", "str", "The diagnosis described in English"

.. note::
    - This table is needed for :meth:`ssmixtools.cleaning.optional.step4`


ATC_to_text.csv
^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "item_code", "str", "ATC code representing the therapeutic classification and hierarchy"
    "item_name", "str", "Name or description of the therapeutic category or specific substance"

.. note::
    - This table is needed for :meth:`ssmixtools.cleaning.optional.step4`

Optional maps
-------------

optional_text_to_ATC.csv
^^^^^^^^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "text", "str", "Name of the medication or item in Japanese"
    "counts", "int", "Number of occurrences or usage of the medication"
    "atc", "str", "ATC code representing the therapeutic classification of the medication"

.. note::
    - Change items in the `atc` column for mapping. 


optional_JLAC10_to_JLAC10.csv
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "item_code", "str", "Code representing the specific laboratory test"
    "item_name", "str", "Name of the test, including details such as sample type (e.g., 'LDH_定量値__全血')"
    "modified", "str", "Modified or standardized version of the item code, if applicable"
    "listed_by_MEDIS", "str", "Indicates whether the test is listed by MEDIS ('Yes', 'No', or 'Yes (except for method)')"
    "mean", "float", "Mean value of the test results"
    "frequent_unit", "str", "Most frequently used unit for the test results (e.g., 'U/L')"
    "numeric_count", "int", "Number of test results with numeric values"
    "nonnumeric_count", "int", "Number of test results with non-numeric values"
    "translated", "str", "Translated description of the test code"
    "comment", "str", "Additional information or remarks about the test"

.. note::
    - Change items in the `modified` column for mapping. If you want to mark a record as non-test-result (e.g., record just containing supplementary comments), put 'nar' (not-a-record) in `modified`. Or, simply delete the row in this CSV table. Laboratory test records with these marked items will be removed from the dataset and counted. 
    - method-agnostic form of JLAC10 is allowed in `modified`. (e.g., 5E0560000001---11)


lab_nonnumerics.csv
^^^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "item_code", "str", "Code representing the laboratory test or item"
    "text", "str", "Description of the test or analysis, including specimen type and specific test details"
    "nonnumeric", "str", "Qualitative or categorical result of the test (e.g., '(3+)', '(4+)')"
    "modified", "str", "Modified version of the nonnumeric result"
    "new_unit", "str", "Unit of measurement for the test result, or 'no_unit' if not applicable"
    "count", "int", "Frequency or number of occurrences of the result"
    "comment", "str", "Additional information or remarks about the test result"

.. note::
    - Change items in the `modified` column for mapping.
    - If the modified value become numeric value, put its unit in `new_unit`.
    - If you want to mark a record as non-test-result, put 'nar' (not-a-record) in `modified`.  Laboratory test records with this nonnumeric result will be removed.

lab_units.csv
^^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "item_code", "str", "Code representing the specific laboratory test"
    "method_agnostic", "str", "Code for the test in a method-agnostic format"
    "unit", "str", "Unit of measurement for the test result (e.g., 'mg/dL', 'no_unit')"
    "modified", "str", "Modified or standardized unit of measurement, if applicable"
    "recommended_unit", "str", "Recommended unit for reporting the test result"
    "add_before_multiplication", "float", "Constant to add to the result before applying a multiplication factor"
    "multiply_by", "float", "Factor by which the result is multiplied for normalization or conversion"
    "add_after_multiplication", "float", "Constant to add to the result after applying the multiplication factor"
    "count", "int", "Number of occurrences or records for this test result"
    "mean", "float", "Mean value of the test results"
    "text", "str", "Description of the test, including specimen type and methodology"
    "comment", "str", "Additional information or remarks about the test result"

.. note::
    - Change items in the `modified` column for mapping.
    - Change constants in `add_before_multiplication`, `multiply_by`, and `add_after_multiplication` if conversion is needed. 
    - If you want to mark a record as non-test-result, put 'nar' (not-a-record) in `modified`. Laboratory test records with this unit will be removed.

Raw tables
-----------
Tables of the extracted clinical records before data cleaning.

patient_metadata_*.csv
^^^^^^^^^^^^^^^^^^^^^^
.. csv-table::
    :header: "Column","Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "sex", "str", "Patient's sex (gender)"
    "date_of_birth", "datetime", "Date of birth"
    "number_of_date_folders", "int", "Number of unique encounter dates"
    "first_visit_date", "datetime", "Date of the first recorded medical encounter"
    "last_visit_date", "datetime", "Date of the last recorded medical encounter"
    "number_of_recorded_admissions", "int", "Total number of recorded admissions"

ADT-12_*.csv
^^^^^^^^^^^^
.. csv-table::
    :header: "Column","Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "department", "str", "Name of the clinical department"
    "visiting_date", "datetime", "Date of outpatient visit"


ADT-22_*.csv
^^^^^^^^^^^^
.. csv-table::
    :header: "Column","Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "department", "str", "Name of the clinical department"
    "admission_date", "datetime", "Admission date and time"
    "time_of_transaction", "datetime", "Timestamp of HL7 message transaction"
    "time_of_message", "datetime", "Timestamp of HL7 message creation"

ADT-52_*.csv
^^^^^^^^^^^^
.. csv-table::
    :header: "Column","Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "discharge_date", "datetime", "Discharge date and time"
    "time_of_transaction", "datetime", "Timestamp of HL7 message transaction"
    "time_of_message", "datetime", "Timestamp of HL7 message creation"
    "discharge_disposition", "str", "Disposition of the patient upon discharge"

PPR-01_*.csv
^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "primary_diagnosis_coding_system", "str", "Coding system used for the primary diagnosis"
    "primary_diagnosis_code", "str", "Code for the primary diagnosis"
    "primary_diagnosis_text", "str", "Name of the primary diagnosis"
    "secondary_diagnosis_coding_system", "str", "Coding system used for the backup diagnosis"
    "secondary_diagnosis_code", "str", "Code for the backup diagnosis"
    "diagnosis_type", "str", "Type of diagnosis"
    "provisional", "int", "Flag indicating if the diagnosis is provisional (0 or 1)"
    "time_of_update", "datetime", "Timestamp of the most recent update in the EHR"
    "date_of_onset", "datetime", "Date the condition first appeared"
    "date_of_diagnosis", "datetime", "Date the diagnosis was made"

OMP-01_*.csv
^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "primary_prescription_coding_system", "str", "Coding system used for the primary prescription"
    "primary_prescription_code", "str", "Code for the primary prescription"
    "primary_prescription_text", "str", "Name of the primary prescription"
    "secondary_prescription_coding_system", "str", "Coding system used for the backup prescription"
    "secondary_prescription_code", "str", "Code for the backup prescription"
    "duration", "str", "Duration of the prescription (e.g., '7 days')"
    "time_of_order", "datetime", "Timestamp of when the order was created or updated"
    "start_of_order", "datetime", "Start time when the order becomes effective"
    "end_of_order", "datetime", "End time when the order expires"

OMP-02_*.csv
^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "injection_type_coding_system", "str", "Coding system used for the injection type"
    "injection_type_code", "str", "Code representing the type of injection"
    "injection_type_text", "str", "Description of the injection type"
    "primary_component_coding_system", "str", "Coding system used for the primary injection component"
    "primary_component_code", "str", "Code for the primary injection component"
    "primary_component_text", "str", "Name of the primary injection component"
    "secondary_component_coding_system", "str", "Coding system used for the backup injection component"
    "secondary_component_code", "str", "Code for the backup injection component"
    "time_of_order", "datetime", "Timestamp of when the order was created or last updated"
    "start_of_order", "datetime", "Start time when the order becomes effective"
    "end_of_order", "datetime", "End time when the order expires"

OML-11_*.csv
^^^^^^^^^^^^
.. csv-table::
    :header: "Column", "Data type", "Details"

    "patient_id", "str", "Unique identifier for each patient"
    "lab_coding_system", "str", "Coding system used for the laboratory test"
    "lab_code", "str", "Code representing the laboratory test"
    "lab_text", "str", "Name of the laboratory test"
    "value", "str", "Result value of the laboratory test"
    "unit_text", "str", "Unit of the test result in text format"
    "unit_code", "str", "Unit of the test result in coded format"
    "unit_coding_system", "str", "Coding system used for the unit code"
    "sampled_time", "datetime", "Time when the specimen was collected"
    "tested_time", "datetime", "Time when the test was performed"
    "reported_time", "datetime", "Time when the result was reported"

