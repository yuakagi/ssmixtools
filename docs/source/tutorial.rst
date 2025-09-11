Tutorial
=========================

1. Install ssmixtools
------------------------------

1-1. Example installation with Python virtual environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

   .. code-block:: bash

      cd /path/to/your/working_dir
      git clone https://github.com/yuakagi/ssmixtools.git  
      cd ssmixtools
      python -m venv .venv  
      source .venv/bin/activate  
      pip install -r requirements.txt  
      pip install . 

1-2. Example installation with Docker (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1-2-1. Download ssmixtools
""""""""""""""""""""""""""""""""


   .. code-block:: bash

      cd /path/to/your/working_dir
      git clone https://github.com/yuakagi/ssmixtools.git

1-2-2. Set up .env
""""""""""""""""""""""""""""""

| There is a file named `.env.example` in the root directory.
| Please **rename this file to .env** and configure the parameters in it.
| Open the file and specify parameters.

1-2-3. Build and run the Docker container:
""""""""""""""""""""""""""""""""""""""""""""""""

   .. code-block:: bash
   
      cd /path/to/your/working_dir/ssmixtools
      docker compose up -d

1-3. Create scripts 
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

| Create scripts that use ssmixtools to process your data.
| You can use `ssmixtools` in your scripts:

   .. code-block:: python

      import ssmixtools

1-4. Run a script with ssmixtools inside the container:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

   .. code-block:: bash

      docker exec -it ssmixtools-python python3 /code/mnt/path/to/script.py

| Replace ssmixtools-python with the name of your Docker container if different.
| (PYTHONPATH = '/code')

2. Extract data from storage
-----------------------------

| Extract data using :meth:`ssmixtools.extraction.extract`.

3. Decrypt the extracted data
------------------------------

| Decrypt the data using :meth:`ssmixtools.decryption.decrypt`.

4. Perform minimal data cleaning and map rendering
---------------------------------------------------

4-1. Build mapping tables using :meth:`ssmixtools.cleaning.mandatory.render_maps`.
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
| This step automatically collects source files and renders tables needed to map medical codes. However, you need to prepare ATC-related source tables by yourself because these tables are not freely available. Please make sure you prepare these tables before taking this step.

4-2. Clean the data using :meth:`ssmixtools.cleaning.mandatory.clean`.
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
| This method applies minimum data cleaning to the extracted data.

5. Perform optional data cleaning steps
---------------------------------------------------

   .. warning::
      - All optional cleaning steps modify data in place. 
      - The optional cleaning steps must be performed in the order shown below.

1st step using :meth:`ssmixtools.cleaning.optional.step1`.
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
| You are given opportunity to map medications and laboratory tests that were not mappable using the default resource.
| The previous step (:meth:`ssmixtools.cleaning.mandatory.clean`) leaves template tables in the directory `reference_dir/created_reference/` for users to investigate and map the unmapped items.
| After you have completed the modification of these tables, run :meth:`ssmixtools.cleaning.optional.step1`.

2nd step using :meth:`ssmixtools.cleaning.optional.step2`.
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
| You are given opportunity to standardize laboratory test units and nonnumeric laboratory test result values.
| The previous step (:meth:`ssmixtools.cleaning.optional.step1`) leaves template tables in the directory `reference_dir/created_reference/` for users to investigate and clean laboratory test units and results.
| After you have completed the modification of these tables, run :meth:`ssmixtools.cleaning.optional.step2`.

3rd step using :meth:`ssmixtools.cleaning.optional.step3`.
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
| After the 2nd step, the data should have been standardized by user. This step investigates irregularities and missingness in the data, and drops records that contain irregular codes (ATC, ICD10, JLAC10) or records with missing data in critical columns (such as laboratory test result records without result values).

4th step using :meth:`ssmixtools.cleaning.optional.step4`.
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
| You are given opportunity to translate standardized codes (ATC, ICD10, JLAC10) into English terms. 
| You need to prepare CSV tables that map ICD10 and ATC codes to English terms (ICD10_to_text.csv and ATC_to_text.csv) in the directory `reference_dir/`. 
| A CSV table that translates JLAC10 codes should have already been created by :meth:`ssmixtools.cleaning.mandatory.render_maps`
| After you have prepared the essential tables, run :meth:`ssmixtools.cleaning.optional.step4`.
| This step leaves a CSV table that maps JLAC10 (method-agnostic) codes to English terms.
